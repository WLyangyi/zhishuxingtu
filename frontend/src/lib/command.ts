import { reactive } from 'vue'

const state = reactive({ open: false })

export function useCommandPalette() {
  return {
    state,
    open() {
      state.open = true
    },
    close() {
      state.open = false
    },
    toggle() {
      state.open = !state.open
    }
  }
}

function isTyping(target: EventTarget | null) {
  const element = target as HTMLElement | null
  if (!element) return false
  return (
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName) ||
    element.isContentEditable === true
  )
}

/**
 * 全局快捷键：
 * - ⌘/Ctrl + K 开关命令面板
 * - g 然后 1..4 直达观测台 / 我的笔记 / 关系图谱 / AI 助手（避免占用浏览器保留的 ⌘1..4）
 */
export function installShellShortcuts(navigate: (path: string) => void) {
  const primary = ['/', '/library', '/graph', '/ai']
  let pendingG = 0

  function onKeydown(event: KeyboardEvent) {
    const modifier = event.metaKey || event.ctrlKey

    if (modifier && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      useCommandPalette().toggle()
      return
    }

    if (modifier || event.altKey || isTyping(event.target)) return

    if (event.key.toLowerCase() === 'g') {
      pendingG = Date.now()
      return
    }

    const index = Number(event.key) - 1
    const withinSequence = pendingG > 0 && Date.now() - pendingG < 900
    if (withinSequence && Number.isInteger(index) && index >= 0 && index < primary.length) {
      event.preventDefault()
      pendingG = 0
      navigate(primary[index])
    }
  }

  window.addEventListener('keydown', onKeydown)
  return () => window.removeEventListener('keydown', onKeydown)
}
