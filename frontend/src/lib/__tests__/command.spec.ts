import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildResourceCommands, installShellShortcuts, useCommandPalette } from '../command'

describe('全局快捷键', () => {
  beforeEach(() => {
    useCommandPalette().close()
  })

  it('Ctrl/⌘ + K 打开命令面板，再按一次关闭', () => {
    const dispose = installShellShortcuts(() => {})
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
    expect(useCommandPalette().state.open).toBe(true)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
    expect(useCommandPalette().state.open).toBe(false)
    dispose()
  })

  it('g 后按 2 直达「我的笔记」', () => {
    const navigate = vi.fn()
    const dispose = installShellShortcuts(navigate)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '2' }))

    expect(navigate).toHaveBeenCalledWith('/library')
    dispose()
  })

  it('在输入框中输入 g 2 不会触发导航', () => {
    const navigate = vi.fn()
    const dispose = installShellShortcuts(navigate)
    const input = document.createElement('input')
    document.body.appendChild(input)

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'g', bubbles: true }))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: '2', bubbles: true }))

    expect(navigate).not.toHaveBeenCalled()
    input.remove()
    dispose()
  })

  it('卸载监听后不再响应快捷键', () => {
    const navigate = vi.fn()
    const dispose = installShellShortcuts(navigate)
    dispose()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '2' }))

    expect(navigate).not.toHaveBeenCalled()
  })
})

describe('P2-5 · 命令面板资源动作', () => {
  const folders = [
    { id: 'f1', name: '工作笔记' },
    { id: 'f2', name: '阅读摘录' }
  ]
  const skills = [{ id: 's1', name: '周报生成' }]
  const prompts = [{ id: 'p1', name: '代码审查' }]

  it('行为1 · 为每个文件夹生成「新建笔记到 X」动作，带 folder query', () => {
    const cmds = buildResourceCommands({ folders, skills: [], prompts: [] })
    expect(cmds).toHaveLength(2)
    expect(cmds[0]).toMatchObject({
      id: 'new-note-f1',
      label: '新建笔记到「工作笔记」',
      to: '/notes/new?folder=f1'
    })
    expect(cmds[1].to).toBe('/notes/new?folder=f2')
  })

  it('行为2 · 为每个 Skill 生成「执行 Skill: X」动作，跳 /skills 带 execute query', () => {
    const cmds = buildResourceCommands({ folders: [], skills, prompts: [] })
    expect(cmds).toHaveLength(1)
    expect(cmds[0]).toMatchObject({
      id: 'exec-skill-s1',
      label: '执行 Skill: 周报生成',
      to: '/skills?execute=s1'
    })
  })

  it('行为3 · 为每个 Prompt 生成「打开提示词 X」动作，跳 /prompts 带 open query', () => {
    const cmds = buildResourceCommands({ folders: [], skills: [], prompts })
    expect(cmds).toHaveLength(1)
    expect(cmds[0]).toMatchObject({
      id: 'open-prompt-p1',
      label: '打开提示词: 代码审查',
      to: '/prompts?open=p1'
    })
  })

  it('行为4 · 三类资源合并，空资源返回空', () => {
    const cmds = buildResourceCommands({ folders, skills, prompts })
    expect(cmds.map((c) => c.id)).toEqual([
      'new-note-f1',
      'new-note-f2',
      'exec-skill-s1',
      'open-prompt-p1'
    ])
    expect(buildResourceCommands({ folders: [], skills: [], prompts: [] })).toEqual([])
  })

  it('行为5 · 特殊字符 id/name 做 URL 编码', () => {
    const cmds = buildResourceCommands({
      folders: [{ id: 'f/1 x', name: 'A&B' }],
      skills: [],
      prompts: []
    })
    expect(cmds[0].to).toBe(`/notes/new?folder=${encodeURIComponent('f/1 x')}`)
    expect(cmds[0].label).toContain('A&B')
  })
})
