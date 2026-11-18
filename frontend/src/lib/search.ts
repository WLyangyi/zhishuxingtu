import { parseWikiLinks } from './editor'
import type { Note } from '@/types/note'

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** 命中词包 <mark>，输入先转义，避免 v-html 注入。 */
export function highlightHtml(text: string, query: string): string {
  const escaped = escapeHtml(text)
  const keyword = query.trim()
  if (!keyword) return escaped

  const pattern = escapeRegExp(escapeHtml(keyword))
  return escaped.replace(new RegExp(`(${pattern})`, 'gi'), '<mark>$1</mark>')
}

/** 截取命中词附近的一段纯文本摘要；没有命中则取开头。 */
export function excerptAround(content: string | null | undefined, query: string, radius = 60): string {
  const text = (content || '')
    .replace(/[#*`>[\]()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!text) return ''

  const keyword = query.trim().toLowerCase()
  const index = keyword ? text.toLowerCase().indexOf(keyword) : -1
  if (index < 0) return text.slice(0, radius * 2)

  const start = Math.max(0, index - radius)
  const end = Math.min(text.length, index + keyword.length + radius)
  return `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`
}

export interface LinkHit {
  title: string
  sourceId: string
  sourceTitle: string
  targetId: string | null
}

/** 从所有笔记的 [[标题]] 中找命中链接，按标题去重。 */
export function collectLinkHits(notes: Note[], query: string): LinkHit[] {
  const keyword = query.trim().toLowerCase()
  if (!keyword) return []

  const byTitle = new Map(notes.map((note) => [note.title.trim(), note.id]))
  const hits = new Map<string, LinkHit>()

  for (const note of notes) {
    for (const title of parseWikiLinks(note.content || '')) {
      if (!title.toLowerCase().includes(keyword)) continue
      if (hits.has(title)) continue
      hits.set(title, {
        title,
        sourceId: note.id,
        sourceTitle: note.title,
        targetId: byTitle.get(title) ?? null
      })
    }
  }

  return [...hits.values()].sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'))
}

export function matchNotes(notes: Note[], query: string): Note[] {
  const keyword = query.trim().toLowerCase()
  if (!keyword) return []
  return notes
    .filter(
      (note) =>
        note.title.toLowerCase().includes(keyword) ||
        (note.content ?? '').toLowerCase().includes(keyword)
    )
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
}
