import { describe, expect, it } from 'vitest'
import { collectLinkHits, excerptAround, highlightHtml, matchNotes } from '../search'
import type { Note } from '@/types/note'

function note(id: string, title: string, content = ''): Note {
  return {
    id,
    title,
    content,
    folder_id: null,
    linked_note_ids: [],
    tags: [],
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z'
  }
}

describe('全局搜索', () => {
  it('高亮命中词并转义 HTML', () => {
    const html = highlightHtml('<script> Agent 三查', 'agent')
    expect(html).not.toContain('<script>')
    expect(html).toContain('<mark>Agent</mark>')
  })

  it('摘要围绕命中词截取并加省略号', () => {
    const content = `${'前置内容'.repeat(20)}关键命中词${'后续内容'.repeat(20)}`
    const excerpt = excerptAround(content, '关键命中词', 5)
    expect(excerpt).toContain('关键命中词')
    expect(excerpt.startsWith('…')).toBe(true)
    expect(excerpt.endsWith('…')).toBe(true)
  })

  it('没有命中时取正文开头', () => {
    expect(excerptAround('一段普通的正文内容', '不存在', 4)).toBe('一段普通的正文内')
  })

  it('链接按标题去重，并解析目标笔记', () => {
    const notes = [
      note('n1', 'A', '参见 [[RAG 混合检索要点]] 与 [[RAG 混合检索要点]]'),
      note('n2', 'B', '再看 [[RAG 混合检索要点]]'),
      note('n3', 'RAG 混合检索要点')
    ]
    const hits = collectLinkHits(notes, 'RAG')
    expect(hits).toHaveLength(1)
    expect(hits[0]).toMatchObject({
      title: 'RAG 混合检索要点',
      sourceId: 'n1',
      targetId: 'n3'
    })
  })

  it('笔记匹配标题或正文，并按更新时间倒序', () => {
    const older = { ...note('n1', 'Agent 复盘'), updated_at: '2026-11-01T00:00:00Z' }
    const newer = { ...note('n2', '普通标题', 'Agent 正文'), updated_at: '2026-11-10T00:00:00Z' }
    const result = matchNotes([older, newer, note('n3', '无关')], 'agent')
    expect(result.map((item) => item.id)).toEqual(['n2', 'n1'])
  })
})
