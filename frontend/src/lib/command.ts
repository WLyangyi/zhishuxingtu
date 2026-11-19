import { reactive } from 'vue'

/** 命令面板中一条可被选择/执行的命令描述（与 UI 层 CommandItem 结构兼容）。 */
export interface ResourceCommand {
  id: string
  label: string
  hint: string
  to: string
}

export interface CommandResources {
  folders: Array<{ id: string; name: string }>
  skills: Array<{ id: string; name: string }>
  prompts: Array<{ id: string; name: string }>
}

/**
 * 由文件夹/Skill/Prompt 三类资源生成动态命令（P2-5）。
 * - 文件夹 → 新建笔记到该文件夹（NoteEditor 读取 ?folder= 预填）
 * - Skill → 跳 /skills 带 ?execute=（SkillsView 读取后打开执行弹窗）
 * - Prompt → 跳 /prompts 带 ?open=（PromptsView 读取后打开编辑弹窗）
 */
export function buildResourceCommands(resources: CommandResources): ResourceCommand[] {
  const folderCommands = resources.folders.map((folder) => ({
    id: `new-note-${folder.id}`,
    label: `新建笔记到「${folder.name}」`,
    hint: '在文件夹中新建',
    to: `/notes/new?folder=${encodeURIComponent(folder.id)}`
  }))
  const skillCommands = resources.skills.map((skill) => ({
    id: `exec-skill-${skill.id}`,
    label: `执行 Skill: ${skill.name}`,
    hint: '运行技能',
    to: `/skills?execute=${encodeURIComponent(skill.id)}`
  }))
  const promptCommands = resources.prompts.map((prompt) => ({
    id: `open-prompt-${prompt.id}`,
    label: `打开提示词: ${prompt.name}`,
    hint: '编辑提示词',
    to: `/prompts?open=${encodeURIComponent(prompt.id)}`
  }))

  return [...folderCommands, ...skillCommands, ...promptCommands]
}

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
