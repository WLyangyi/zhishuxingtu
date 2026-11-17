/**
 * 视觉验收截图（CDP，无第三方依赖）
 *
 * 用法：
 *   node scripts/qa-shot.mjs --url http://localhost:5174/dev/ui \
 *     --out ../docs/design/qa/phase-2/shot.png \
 *     --width 1440 --height 1200 --full --token <JWT> --theme dark
 *
 * 说明：无头 Edge/Chrome 的 --window-size 有最小宽度限制（约 492px），
 * 375px 移动端必须通过 Emulation.setDeviceMetricsOverride 才能真正生效。
 */
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const EDGE_CANDIDATES = [
  process.env.EDGE_PATH,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe'
].filter(Boolean)

function parseArgs(argv) {
  const result = {}
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i]
    if (!key.startsWith('--')) continue
    const next = argv[i + 1]
    if (!next || next.startsWith('--')) result[key.slice(2)] = true
    else {
      result[key.slice(2)] = next
      i += 1
    }
  }
  return result
}

const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms))

async function waitFor(url, attempts = 60) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url)
      if (response.ok) return await response.json()
    } catch {
      /* 浏览器尚未就绪 */
    }
    await sleep(200)
  }
  throw new Error(`等待 CDP 就绪超时：${url}`)
}

class CDP {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl)
    this.seed = 0
    this.pending = new Map()
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (!message.id) return
      const entry = this.pending.get(message.id)
      if (!entry) return
      this.pending.delete(message.id)
      if (message.error) entry.reject(new Error(message.error.message))
      else entry.resolve(message.result)
    }
    this.ws.onclose = () => this.rejectAll(new Error('CDP 连接已关闭'))
    this.ws.onerror = () => this.rejectAll(new Error('CDP 连接错误'))
  }

  open() {
    return new Promise((resolveOpen, rejectOpen) => {
      this.ws.onopen = () => resolveOpen()
      this.ws.onerror = () => rejectOpen(new Error('CDP WebSocket 连接失败'))
    })
  }

  send(method, params = {}, timeoutMs = 20000) {
    const id = ++this.seed
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolveSend, rejectSend) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        rejectSend(new Error(`CDP 调用超时: ${method}`))
      }, timeoutMs)
      this.pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer)
          resolveSend(value)
        },
        reject: (error) => {
          clearTimeout(timer)
          rejectSend(error)
        }
      })
    })
  }

  rejectAll(error) {
    for (const [id, entry] of this.pending) {
      this.pending.delete(id)
      entry.reject(error)
    }
  }

  close() {
    this.ws.close()
  }
}

const args = parseArgs(process.argv.slice(2))
const targetUrl = args.url
const out = args.out
if (!targetUrl || !out) {
  console.error('缺少参数：--url 与 --out 必填')
  process.exit(1)
}

const width = Number(args.width ?? 1440)
const height = Number(args.height ?? 1000)
const mobile = Boolean(args.mobile)
const fullPage = Boolean(args.full)
const theme = args.theme ?? 'dark'
const waitMs = Number(args.wait ?? 2600)
const port = Number(args.port ?? 9300 + Math.floor(Math.random() * 400))

const edgePath = EDGE_CANDIDATES.find((path) => existsSync(path))
if (!edgePath) {
  console.error('找不到 Edge/Chrome，可通过 EDGE_PATH 指定路径')
  process.exit(1)
}

const profile = mkdtempSync(join(tmpdir(), 'zs-qa-'))
const browser = spawn(edgePath, [
  '--headless=new',
  '--disable-gpu',
  '--hide-scrollbars',
  '--no-first-run',
  '--no-default-browser-check',
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`,
  'about:blank'
])

let cdp = null
try {
  await waitFor(`http://127.0.0.1:${port}/json/version`)
  const target = await (
    await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })
  ).json()
  cdp = new CDP(target.webSocketDebuggerUrl)
  await cdp.open()

  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile,
    screenWidth: width,
    screenHeight: height
  })

  // 先落到目标域（可能被守卫重定向到 /login），确保 localStorage 写在正确 origin
  await cdp.send('Page.navigate', { url: targetUrl })
  await sleep(1400)

  const storageScript = args.token
    ? `localStorage.setItem('token', ${JSON.stringify(args.token)}); localStorage.setItem('theme', ${JSON.stringify(theme)});`
    : `localStorage.setItem('theme', ${JSON.stringify(theme)});`
  await cdp.send('Runtime.evaluate', { expression: storageScript })

  // 写入登录态后重新导航到目标（守卫此时才会放行）
  await cdp.send('Page.navigate', { url: targetUrl })
  await sleep(waitMs)

  if (args.eval) {
    await cdp.send('Runtime.evaluate', { expression: String(args.eval) })
    await sleep(Number(args.settle ?? 700))
  }

  let clip
  if (fullPage) {
    const metrics = await cdp.send('Page.getLayoutMetrics')
    const size = metrics.cssContentSize ?? metrics.contentSize
    clip = { x: 0, y: 0, width: Math.ceil(size.width), height: Math.ceil(size.height), scale: 1 }
  }

  const shot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: fullPage,
    ...(clip ? { clip } : {})
  })

  writeFileSync(resolve(process.cwd(), out), Buffer.from(shot.data, 'base64'))
  console.log(`✓ 截图已保存：${out} (${width}x${height}${mobile ? ' mobile' : ''}${fullPage ? ' full' : ''})`)
} finally {
  cdp?.close()
  browser.kill('SIGKILL')
}
