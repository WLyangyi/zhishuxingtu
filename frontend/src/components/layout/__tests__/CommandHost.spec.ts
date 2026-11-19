import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { push } = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

const { paletteHolder } = vi.hoisted(() => ({ paletteHolder: { state: null as { open: boolean } | null } }))
vi.mock('@/lib/command', async () => {
  const { reactive } = await import('vue')
  const actual = await vi.importActual<typeof import('@/lib/command')>('@/lib/command')
  const shared = reactive({ open: false })
  paletteHolder.state = shared
  return {
    ...actual,
    useCommandPalette: () => ({
      state: shared,
      open: () => { shared.open = true },
      close: () => { shared.open = false },
      toggle: () => { shared.open = !shared.open }
    })
  }
})

vi.mock('@/api/notes', () => ({ notesApi: { list: vi.fn().mockResolvedValue({ data: { items: [] } }) } }))
const { foldersList, skillsGet, promptsGet } = vi.hoisted(() => ({
  foldersList: vi.fn(),
  skillsGet: vi.fn(),
  promptsGet: vi.fn()
}))
vi.mock('@/api/folders', () => ({ foldersApi: { list: foldersList } }))
vi.mock('@/api/skills', () => ({ skillsApi: { getSkills: skillsGet } }))
vi.mock('@/api/prompts', () => ({ promptsApi: { getPrompts: promptsGet } }))

vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ logout: vi.fn() }) }))
const { toggle } = vi.hoisted(() => ({ toggle: vi.fn() }))
vi.mock('@/stores/theme', () => ({ useThemeStore: () => ({ isDark: false, toggle }) }))
vi.mock('@/stores/import', () => ({ useImportStore: () => ({ openImportModal: vi.fn() }) }))

import CommandHost from '../CommandHost.vue'
import CommandPalette from '@/components/ui/CommandPalette.vue'

async function mountHost() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(CommandHost, { global: { plugins: [pinia] } })
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  if (paletteHolder.state) paletteHolder.state.open = false
  foldersList.mockResolvedValue({ data: [{ id: 'f1', name: '工作笔记', children: [] }] })
  skillsGet.mockResolvedValue({ items: [{ id: 's1', name: '周报生成' }] })
  promptsGet.mockResolvedValue({ data: { items: [{ id: 'p1', name: '代码审查' }] } })
})

describe('CommandHost 动态命令注册（P2-5）', () => {
  it('面板打开时加载三类资源，把动态命令合并进 actions', async () => {
    const wrapper = await mountHost()
    paletteHolder.state!.open = true
    await flushPromises()

    const palette = wrapper.findComponent(CommandPalette)
    const actions = palette.props('actions') as Array<{ id: string; label: string; to?: string }>
    const ids = actions.map((a) => a.id)

    expect(ids).toContain('new-note-f1')
    expect(ids).toContain('exec-skill-s1')
    expect(ids).toContain('open-prompt-p1')
    expect(actions.find((a) => a.id === 'new-note-f1')?.to).toBe('/notes/new?folder=f1')

    wrapper.unmount()
  })

  it('三类 API 解包约定不同也能正确取值（不抛错、命令齐全）', async () => {
    const wrapper = await mountHost()
    paletteHolder.state!.open = true
    await flushPromises()

    expect(foldersList).toHaveBeenCalled()
    expect(skillsGet).toHaveBeenCalled()
    expect(promptsGet).toHaveBeenCalled()
    const palette = wrapper.findComponent(CommandPalette)
    expect((palette.props('actions') as unknown[]).length).toBeGreaterThanOrEqual(8)

    wrapper.unmount()
  })
})
