/**
 * 图谱 500 节点压测（CDP）
 *
 * 用法：
 *   node scripts/graph-stress.mjs --url http://localhost:5174/graph \
 *     --token <JWT> [--theme dark] [--out ../docs/design/qa/phase-6/graph-stress.json]
 *
 * 指标：
 *   - 节点/边规模（从 /api/graph/global 统计）
 *   - 布局收敛：加载后每秒 rAF 密度曲线（d3 tick 驱动，衰减到静默即收敛）
 *   - 交互帧率：CDP 派发 wheel 缩放 + mousemove 期间的主线程帧间隔 p50/p95/长帧率
 *   - 堆内存
 */
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

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
  throw new Error('等待 CDP 就绪超时')
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
  }

  open() {
    return new Promise((resolveOpen, rejectOpen) => {
      this.ws.onopen = () => resolveOpen()
      this.ws.onerror = () => rejectOpen(new Error('CDP WebSocket 连接失败'))
    })
  }

  send(method, params = {}, timeoutMs = 30000) {
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
    for (const [, entry] of this.pending) entry.reject(error)
    this.pending.clear()
  }

  close() {
    this.ws.close()
  }
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true
  })
  if (result.exceptionDetails) {
    throw new Error(`页面内脚本异常: ${result.exceptionDetails.text}`)
  }
  return result.result?.value
}

const args = parseArgs(process.argv.slice(2))
const targetUrl = args.url
const token = args.token
if (!targetUrl || !token) {
  console.error('缺少参数：--url 与 --token 必填')
  process.exit(1)
}

const port = Number(args.port ?? 9700 + Math.floor(Math.random() * 300))
const edgePath = EDGE_CANDIDATES.find((path) => existsSync(path))
if (!edgePath) {
  console.error('找不到 Edge/Chrome，可通过 EDGE_PATH 指定路径')
  process.exit(1)
}

const profile = mkdtempSync(join(tmpdir(), 'zs-stress-'))
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

const report = { url: targetUrl, theme: args.theme ?? 'dark' }
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
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
    screenWidth: 1440,
    screenHeight: 900
  })

  // ---- 1. 规模统计（直连 API）----
  const graphData = await (
    await fetch(`${targetUrl.replace(/\/graph.*$/, '')}/api/graph/global`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  ).json()
  report.nodes = graphData.data?.nodes?.length ?? 0
  report.edges = graphData.data?.edges?.length ?? 0
  const apiMs = graphData.meta?.server_time
    ? null
    : null

  // ---- 2. 落地并注入登录态 ----
  await cdp.send('Page.navigate', { url: targetUrl })
  await sleep(1200)
  await evaluate(cdp, `localStorage.setItem('token', ${JSON.stringify(token)}); localStorage.setItem('theme', ${JSON.stringify(args.theme ?? 'dark')});`)
  await cdp.send('Page.navigate', { url: targetUrl })
  await sleep(300)

  // ---- 3. 布局收敛检测（canvas 像素静止 = tick 停止）----
  // 每 800ms 抽样 canvas 局部像素做哈希，连续 3 次相同视为布局静止。
  // 不用 rAF 计数：采样器自身每秒产生 60 条记录，密度曲线无法区分 tick 源。
  await evaluate(cdp, `window.__pixelHashes = []; (function snap() {
    const el = document.querySelector('.graph__canvas')
    if (!el) { window.__pixelHashes.push(null) }
    else {
      const ctx = el.getContext('2d')
      const w = el.width, h = el.height
      const boxes = [[0, 0, 300, 200], [w - 300, 0, 300, 200], [Math.floor(w/2)-150, Math.floor(h/2)-100, 300, 200]]
      let hash = 0
      for (const [x, y, bw, bh] of boxes) {
        const data = ctx.getImageData(x, y, bw, bh).data
        for (let i = 0; i < data.length; i += 97) hash = ((hash * 31) + data[i]) | 0
      }
      window.__pixelHashes.push(hash)
    }
    setTimeout(snap, 800)
  })();`)
  await sleep(12000)

  const hashes = await evaluate(cdp, `window.__pixelHashes.slice()`)
  const samples = hashes.filter((h) => h !== null)
  let convergeSamples = -1
  for (let i = 0; i + 2 < samples.length; i += 1) {
    if (samples[i] === samples[i + 1] && samples[i + 1] === samples[i + 2]) {
      convergeSamples = i
      break
    }
  }
  report.pixelSampleCount = samples.length
  report.layoutConvergeSeconds = convergeSamples >= 0 ? Math.round(convergeSamples * 0.8) : null
  report.layoutConverged = convergeSamples >= 0
  await evaluate(cdp, `window.__pixelHashes = []`)

  // ---- 4. 交互帧率（wheel 缩放 + 按住拖拽 4s）----
  await evaluate(cdp, `window.__frames = []; (function loop(t) { window.__frames.push(performance.now()); requestAnimationFrame(loop); })();`)

  const cx = 720
  const cy = 450
  for (let step = 0; step < 16; step += 1) {
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseWheel',
      x: cx,
      y: cy,
      deltaX: 0,
      deltaY: step % 2 === 0 ? -120 : 120
    })
    await sleep(60)
  }
  // 完整拖拽序列：press → move → release（drag end 会把 alphaTarget 归零）
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed', x: cx, y: cy, button: 'left', buttons: 1, clickCount: 1
  })
  for (let step = 0; step < 24; step += 1) {
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: cx + (step % 8) * 30,
      y: cy + Math.floor(step / 8) * 30,
      buttons: 1
    })
    await sleep(40)
  }
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased', x: cx + 120, y: cy + 60, button: 'left', buttons: 0, clickCount: 1
  })
  await sleep(1500)

  const frameStats = await evaluate(cdp, `(() => {
    const frames = window.__frames
    const gaps = []
    for (let i = 1; i < frames.length; i += 1) gaps.push(frames[i] - frames[i - 1])
    gaps.sort((a, b) => a - b)
    const pick = (q) => gaps[Math.min(gaps.length - 1, Math.floor(gaps.length * q))]
    const long = gaps.filter((g) => g > 32).length
    return {
      samples: gaps.length,
      p50: Math.round(pick(0.5) * 10) / 10,
      p95: Math.round(pick(0.95) * 10) / 10,
      maxGap: Math.round(gaps[gaps.length - 1] * 10) / 10,
      longFrameRatio: Math.round((long / Math.max(1, gaps.length)) * 1000) / 10
    }
  })()`)
  report.interaction = frameStats

  // ---- 5. 内存 ----
  report.memoryMB = await evaluate(cdp, `performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null`)

  // ---- 6. 截图留档 ----
  if (args.out) {
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png' })
    writeFileSync(args.out.replace(/\.json$/, '.png'), Buffer.from(shot.data, 'base64'))
    writeFileSync(args.out, JSON.stringify(report, null, 2))
    console.log(`✓ 压测报告与截图已保存：${args.out}`)
  } else {
    console.log(JSON.stringify(report, null, 2))
  }
} catch (error) {
  console.error('✗ 压测失败：', error.message)
  console.log(JSON.stringify(report, null, 2))
  process.exitCode = 1
} finally {
  cdp?.close()
  browser.kill()
}
