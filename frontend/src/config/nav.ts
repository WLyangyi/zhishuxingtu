import {
  Activity,
  FlaskConical,
  Library,
  Network,
  Quote,
  Sparkles,
  Telescope,
  Zap
} from 'lucide-vue-next'
import type { Component } from 'vue'

export interface NavItem {
  id: string
  label: string
  to: string
  icon: Component
  shortcut?: string
  group: 'main' | 'lab'
}

export const PRIMARY_NAV: NavItem[] = [
  { id: 'home', label: '观测台', to: '/', icon: Telescope, shortcut: 'G 1', group: 'main' },
  { id: 'library', label: '我的笔记', to: '/library', icon: Library, shortcut: 'G 2', group: 'main' },
  { id: 'graph', label: '关系图谱', to: '/graph', icon: Network, shortcut: 'G 3', group: 'main' },
  { id: 'ai', label: 'AI 助手', to: '/ai', icon: Sparkles, shortcut: 'G 4', group: 'main' }
]

export const LAB_NAV: NavItem[] = [
  { id: 'lab', label: '提示词实验室', to: '/lab', icon: FlaskConical, group: 'lab' },
  { id: 'skills', label: 'Skills', to: '/skills', icon: Zap, group: 'lab' },
  { id: 'prompts', label: 'Prompts', to: '/prompts', icon: Quote, group: 'lab' },
  { id: 'observability', label: '可观测面板', to: '/ai/observability', icon: Activity, group: 'lab' }
]

export interface PageMeta {
  title: string
  kicker: string
  group: string
}

const PAGE_META: Record<string, PageMeta> = {
  Home: { title: '观测台', kicker: 'OBSERVATORY', group: 'observe' },
  Library: { title: '我的笔记', kicker: 'LIBRARY', group: 'create' },
  LibraryDetail: { title: '我的笔记', kicker: 'LIBRARY', group: 'create' },
  NewNote: { title: '新建笔记', kicker: 'NOTE', group: 'create' },
  NoteEditor: { title: '笔记编辑器', kicker: 'NOTE', group: 'create' },
  NewContent: { title: '新建内容', kicker: 'CONTENT', group: 'create' },
  ContentEditor: { title: '内容编辑器', kicker: 'CONTENT', group: 'create' },
  Graph: { title: '关系图谱', kicker: 'STAR ATLAS', group: 'observe' },
  AIAssistant: { title: 'AI 助手', kicker: 'OBSERVER', group: 'ai' },
  AgentObservability: { title: '可观测面板', kicker: 'OBSERVABILITY', group: 'ai' },
  Skills: { title: 'Skills', kicker: 'SKILLS', group: 'lab' },
  PromptLab: { title: '提示词实验室', kicker: 'LAB', group: 'lab' },
  Prompts: { title: 'Prompts', kicker: 'PROMPTS', group: 'lab' },
  Search: { title: '全局搜索', kicker: 'SEARCH', group: 'create' },
  ImportHistory: { title: '导入历史', kicker: 'IMPORT', group: 'create' },
  DevUI: { title: '组件库', kicker: 'DESIGN SYSTEM', group: 'dev' }
}

export function pageMetaOf(name?: string | symbol | null): PageMeta {
  if (typeof name === 'string' && PAGE_META[name]) return PAGE_META[name]
  return { title: '知枢星图', kicker: 'STAR ATLAS', group: 'default' }
}
