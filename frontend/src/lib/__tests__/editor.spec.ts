import { describe, expect, it } from 'vitest'
import {
  buildWikiHighlightSegments,
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

describe('编辑态 [[ ]] 高亮切分（P6-②）', () => {
  it('行为1 · 闭合链接切分为 wiki 段，前后保持普通段', () => {
    expect(buildWikiHighlightSegments('前言 [[RAG 笔记]] 后记')).toEqual([
      { text: '前言 ', kind: 'plain' },
      { text: '[[RAG 笔记]]', kind: 'wiki' },
      { text: ' 后记', kind: 'plain' }
    ])
    expect(buildWikiHighlightSegments('没有链接的一行')).toEqual([
      { text: '没有链接的一行', kind: 'plain' }
    ])
    expect(buildWikiHighlightSegments('[[A]]与[[B]]相邻')).toEqual([
      { text: '[[A]]', kind: 'wiki' },
      { text: '与', kind: 'plain' },
      { text: '[[B]]', kind: 'wiki' },
      { text: '相邻', kind: 'plain' }
    ])
  })

  it('行为2 · 未闭合 [[ 查询为 pending 段，到行尾为止不跨行', () => {
    expect(buildWikiHighlightSegments('输入 [[RAG')).toEqual([
      { text: '输入 ', kind: 'plain' },
      { text: '[[RAG', kind: 'pending' }
    ])
    // pending 不吞换行，下一行回到普通文本
    expect(buildWikiHighlightSegments('[[abc\ndef')).toEqual([
      { text: '[[abc', kind: 'pending' },
      { text: '\ndef', kind: 'plain' }
    ])
    // [[ 后直接换行 → 不产生任何高亮段，文本无损
    const noHighlight = buildWikiHighlightSegments('a [[\nb')
    expect(noHighlight.some((s) => s.kind !== 'plain')).toBe(false)
    expect(noHighlight.map((s) => s.text).join('')).toBe('a [[\nb')
  })

  it('行为3 · 空标题 [[]] 与孤立 ]] 不算链接，多行正文链接不跨行', () => {
    // [[]] 空标题：plain 且文本无损
    const empty = buildWikiHighlightSegments('x [[]] y')
    expect(empty.some((s) => s.kind !== 'plain')).toBe(false)
    expect(empty.map((s) => s.text).join('')).toBe('x [[]] y')

    // 孤立 ]] 无开头：plain
    const orphan = buildWikiHighlightSegments('a ]] b')
    expect(orphan.some((s) => s.kind !== 'plain')).toBe(false)
    expect(orphan.map((s) => s.text).join('')).toBe('a ]] b')

    // 闭合标记在下一行 → 视为未闭合 pending（不跨行）
    expect(buildWikiHighlightSegments('[[跨行\n标题]]')).toEqual([
      { text: '[[跨行', kind: 'pending' },
      { text: '\n标题]]', kind: 'plain' }
    ])

    // 逐段拼回原文无损（overlay 渲染的前提）
    const sample = 'a [[x]] b [[未完成\nc ]] d [[ok]] e'
    const joined = buildWikiHighlightSegments(sample)
      .map((s) => s.text)
      .join('')
    expect(joined).toBe(sample)
  })
})
