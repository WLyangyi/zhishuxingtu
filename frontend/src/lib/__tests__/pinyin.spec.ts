import { describe, expect, it } from 'vitest'
import { matchesCommand, toPinyinForms } from '../pinyin'

describe('命令拼音匹配（P2-5 补充）', () => {
  it('行为1 · 中文转全拼连写与首字母串，非中文原样保留', () => {
    const forms = toPinyinForms('新建笔记')
    expect(forms.full).toBe('xinjianbiji')
    expect(forms.initials).toBe('xjbj')
  })

  it('行为2 · 中英混合文本：中文转拼音、英文/数字保留', () => {
    const forms = toPinyinForms('Agent 三查反思')
    expect(forms.full).toContain('agent')
    expect(forms.full).toContain('sanchafansi')
    expect(forms.initials).toContain('scfs')
  })

  it('行为3 · 原样子串匹配仍生效（大小写不敏感）', () => {
    expect(matchesCommand('Agentic RAG 设计笔记', undefined, 'rag')).toBe(true)
    expect(matchesCommand('关系图谱', '/graph', 'graph')).toBe(true)
    expect(matchesCommand('关系图谱', '/graph', 'RAG')).toBe(false)
  })

  it('行为4 · 全拼匹配中文标题', () => {
    expect(matchesCommand('新建笔记', undefined, 'xinjian')).toBe(true)
    expect(matchesCommand('新建笔记', undefined, 'xinjianbiji')).toBe(true)
    expect(matchesCommand('关系图谱', undefined, 'guanxi')).toBe(true)
  })

  it('行为5 · 首字母匹配中文标题', () => {
    expect(matchesCommand('新建笔记', undefined, 'xjbj')).toBe(true)
    expect(matchesCommand('执行 Skill: 周报生成', undefined, 'zbs')).toBe(true)
  })

  it('行为6 · hint 也参与匹配（原样子串与拼音）', () => {
    expect(matchesCommand('新建笔记到「工作笔记」', '在文件夹中新建', 'wenjianjia')).toBe(true)
    expect(matchesCommand('关系图谱', '/graph', 'graph')).toBe(true)
    expect(matchesCommand('未链接提及', 'UNLINKED', 'wl')).toBe(true)
  })

  it('行为7 · 空关键词永远匹配；完全不相关返回 false', () => {
    expect(matchesCommand('新建笔记', undefined, '')).toBe(true)
    expect(matchesCommand('新建笔记', undefined, 'zzzz')).toBe(false)
  })
})
