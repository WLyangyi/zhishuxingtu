import { describe, expect, it } from 'vitest'
import {
  detectWikiQuery,
  parseWikiLinks,
  readMinutes,
  renderWikiMarkup,
  suggestNotes,
  wordCount
} from '../editor'
import type { Note } from '@/types/note'

function note(id: string, title: string): Note {
  return {
    id,
    title,
    content: '',
    folder_id: null,
    linked_note_ids: [],
    tags: [],
    created_at: '',
    updated_at: ''
  }
}

const notes = [note('n1', 'Agent 三查反思'), note('n2', 'RAG 混合检索要点'), note('n3', 'Agent 记忆')]

describe('编辑器纯逻辑', () => {
  it('解析双方括号链接并去重', () => {
    expect(parseWikiLinks('参见 [[Agent 三查反思]] 与 [[RAG 混合检索要点]]，再看 [[Agent 三查反思]]')).toEqual([
      'Agent 三查反思',
      'RAG 混合检索要点'
    ])
    expect(parseWikiLinks('没有链接')).toEqual([])
    expect(parseWikiLinks('[[\n换行不算]]')).toEqual([])
  })

  it('识别光标前的 [[ 查询', () => {
    const text = '前文内容 [[Ag'
    expect(detectWikiQuery(text)).toEqual({ start: 5, query: 'Ag' })
    expect(detectWikiQuery('[[Agent]]')).toBeNull()
    expect(detectWikiQuery('[[\n换行')).toBeNull()
    expect(detectWikiQuery('普通文本')).toBeNull()
  })

  it('候选优先前缀匹配，排除当前笔记并限制数量', () => {
    const result = suggestNotes(notes, 'agent', 'n1', 5)
    expect(result.map((item) => item.id)).toEqual(['n3'])
    expect(suggestNotes(notes, '', null, 2).map((item) => item.id)).toEqual(['n1', 'n2'])
  })

  it('预览把双链渲染为站内链接，未知标题为断链且转义 HTML', () => {
    const html = renderWikiMarkup(
      '看 [[Agent 三查反思]] 和 [[不存在的笔记]] 以及 [[<script>alert(1)</script>]]',
      notes
    )
    expect(html).toContain('href="/notes/n1"')
    expect(html).toContain('wiki-link--broken')
    expect(html).not.toContain('<script>')
  })

  it('字数去空白，阅读时长按 250 字/分钟向上取整', () => {
    expect(wordCount('你好 世界\n第二行')).toBe(7)
    expect(readMinutes(1284)).toBe(6)
    expect(readMinutes(0)).toBe(1)
  })
})
