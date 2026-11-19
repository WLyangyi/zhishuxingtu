import type { Note } from '@/types/note'

const WIKI_PATTERN = /\[\[([^[\]\n]{1,200})\]\]/g

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** 提取正文中的 [[标题]]，去重并去掉首尾空白。 */
export function parseWikiLinks(content: string): string[] {
  const titles = new Set<string>()
  for (const match of content.matchAll(WIKI_PATTERN)) {
    const title = match[1].trim()
    if (title) titles.add(title)
  }
  return [...titles]
}

/** 根据光标前的文本判断是否正在输入 [[ 查询。 */
export function detectWikiQuery(textBeforeCaret: string): { start: number; query: string } | null {
  const start = textBeforeCaret.lastIndexOf('[[')
  if (start < 0) return null

  const query = textBeforeCaret.slice(start + 2)
  if (query.includes(']]') || query.includes('\n') || query.length > 60) return null
  return { start, query }
}

/** 候选：前缀匹配优先，其次包含匹配；排除当前笔记。 */
export function suggestNotes(
  notes: Note[],
  query: string,
  excludeId: string | null,
  limit = 6
): Note[] {
  const keyword = query.trim().toLowerCase()
  const pool = notes.filter((note) => note.id !== excludeId)
  if (!keyword) return pool.slice(0, limit)

  const prefix: Note[] = []
  const contains: Note[] = []

  for (const note of pool) {
    const title = note.title.toLowerCase()
    if (title.startsWith(keyword)) prefix.push(note)
    else if (title.includes(keyword)) contains.push(note)
  }

  return [...prefix, ...contains].slice(0, limit)
}

/** 把 [[标题]] 换成站内链接 / 断链占位，交给 Markdown 渲染前使用。 */
export function renderWikiMarkup(content: string, notes: Note[]): string {
  const byTitle = new Map(notes.map((note) => [note.title.trim(), note]))

  return content.replace(WIKI_PATTERN, (_match, rawTitle: string) => {
    const title = rawTitle.trim()
    const note = byTitle.get(title)
    const safeTitle = escapeHtml(title)

    if (!note) {
      return `<span class="wiki-link wiki-link--broken">${safeTitle}</span>`
    }
    return `<a href="/notes/${note.id}" class="wiki-link" data-note-id="${note.id}">${safeTitle}</a>`
  })
}

export function wordCount(content: string): number {
  return content.replace(/\s+/g, '').length
}

export interface WikiSegment {
  text: string
  kind: 'plain' | 'wiki' | 'pending'
}

/**
 * 编辑态 overlay 高亮切分（P6-②）
 * - 闭合 [[标题]] → wiki（金色高亮）
 * - 未闭合 [[查询（不跨行）→ pending（弱提示）
 * - [[]] 空标题、孤立 [[ 与 ]] → plain
 */
export function buildWikiHighlightSegments(content: string): WikiSegment[] {
  const segments: WikiSegment[] = []
  let buffer = ''
  let index = 0

  const flush = () => {
    if (buffer) {
      segments.push({ text: buffer, kind: 'plain' })
      buffer = ''
    }
  }

  while (index < content.length) {
    const open = content.indexOf('[[', index)
    if (open < 0) {
      buffer += content.slice(index)
      break
    }
    buffer += content.slice(index, open)

    const close = content.indexOf(']]', open + 2)
    const newline = content.indexOf('\n', open + 2)
    const hasClose = close >= 0 && (newline < 0 || close < newline)
    const inner = hasClose
      ? content.slice(open + 2, close)
      : content.slice(open + 2, newline >= 0 ? newline : undefined)

    if (hasClose && inner.trim()) {
      flush()
      segments.push({ text: content.slice(open, close + 2), kind: 'wiki' })
      index = close + 2
      continue
    }

    if (!hasClose && inner.trim()) {
      flush()
      const end = newline >= 0 ? newline : content.length
      segments.push({ text: content.slice(open, end), kind: 'pending' })
      index = end
      continue
    }

    // [[]] 空标题或 [[ 后直接结束：按普通文本消费两个字符
    buffer += '[['
    index = open + 2
  }

  flush()
  return segments
}

export function readMinutes(chars: number): number {
  return Math.max(1, Math.ceil(chars / 250))
}

/** 正文中所有 [[...]] 块占据的 [start, end) 区间。 */
function wikiRanges(content: string): Array<[number, number]> {
  const ranges: Array<[number, number]> = []
  for (const match of content.matchAll(WIKI_PATTERN)) {
    const start = match.index ?? 0
    ranges.push([start, start + match[0].length])
  }
  return ranges
}

function inWikiRange(index: number, ranges: Array<[number, number]>): boolean {
  return ranges.some(([start, end]) => index >= start && index < end)
}

/**
 * 未链接提及：正文中以纯文本出现、但未写成 [[标题]] 的笔记（P2-4）。
 * - 忽略 [[...]] 块内的文字（那是已建链的锚文本）
 * - 大小写不敏感、标题首尾空白规范化
 * - 排除 excludeId 指向的当前笔记；按正文首次出现顺序返回
 */
export function findUnlinkedMentions(
  content: string,
  notes: Note[],
  excludeId: string | null
): Note[] {
  const ranges = wikiRanges(content)
  const plain = [...content].map((ch, i) => (inWikiRange(i, ranges) ? '' : ch)).join('')
  const lower = plain.toLowerCase()
  const hits: Array<{ note: Note; at: number }> = []

  for (const note of notes) {
    if (note.id === excludeId) continue
    const title = note.title.trim()
    if (!title) continue
    const at = lower.indexOf(title.toLowerCase())
    if (at >= 0) hits.push({ note, at })
  }

  hits.sort((a, b) => a.at - b.at)
  return hits.map((item) => item.note)
}

/** 把正文中首个位于纯文本区（非 [[...]] 内）的标题替换为 [[标题]]（P2-4）。 */
export function linkMention(content: string, title: string): string {
  const clean = title.trim()
  if (!clean) return content
  const ranges = wikiRanges(content)
  const lower = content.toLowerCase()
  const key = clean.toLowerCase()
  let from = 0

  while (from <= content.length - key.length) {
    const at = lower.indexOf(key, from)
    if (at < 0) return content
    if (!inWikiRange(at, ranges)) {
      return `${content.slice(0, at)}[[${clean}]]${content.slice(at + clean.length)}`
    }
    from = at + key.length
  }
  return content
}
