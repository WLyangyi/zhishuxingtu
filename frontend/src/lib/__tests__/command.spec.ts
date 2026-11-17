import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installShellShortcuts, useCommandPalette } from '../command'

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
