import { readdirSync, readFileSync, statSync } from 'node:fs'
import { extname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = fileURLToPath(new URL('../src/', import.meta.url))
const TARGETS = ['components/ui', 'components/domain', 'components/layout', 'lib', 'views/DevUI.vue']
const EXTENSIONS = new Set(['.vue', '.css', '.ts', '.js'])
const HEX = /#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g

const offenders = []

function checkFile(full) {
  if (!EXTENSIONS.has(extname(full))) return
  const rel = relative(ROOT, full).replace(/\\/g, '/')
  const content = readFileSync(full, 'utf8')
  content.split(/\r?\n/).forEach((line, index) => {
    const matches = line.match(HEX)
    if (matches) offenders.push({ file: rel, line: index + 1, values: matches })
  })
}

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) walk(full)
    else checkFile(full)
  }
}

for (const target of TARGETS) {
  const full = join(ROOT, target)
  const stat = statSync(full)
  if (stat.isDirectory()) walk(full)
  else checkFile(full)
}

if (offenders.length) {
  console.error(`✗ 设计系统组件中发现 ${offenders.length} 处硬编码色值：`)
  for (const item of offenders) {
    console.error(`  ${item.file}:${item.line}  ${item.values.join(', ')}`)
  }
  process.exit(1)
}

console.log('✓ hex 扫描通过：ui/domain/layout/lib 与 /dev/ui 无硬编码色值')
