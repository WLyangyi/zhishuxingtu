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

export function readMinutes(chars: number): number {
  return Math.max(1, Math.ceil(chars / 250))
}
