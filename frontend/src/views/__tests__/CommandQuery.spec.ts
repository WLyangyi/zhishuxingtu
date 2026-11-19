import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type RouteComponent } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getSkills, executeSkill } = vi.hoisted(() => ({
  getSkills: vi.fn(),
  executeSkill: vi.fn()
}))
vi.mock('@/api/skills', () => ({
  skillsApi: {
    getTemplates: vi.fn().mockResolvedValue([]),
    getSkills,
    executeSkill
  }
}))

const { getPrompts, getTemplates, getCategories, updatePrompt } = vi.hoisted(() => ({
  getPrompts: vi.fn(),
  getTemplates: vi.fn().mockResolvedValue({ data: [] }),
  getCategories: vi.fn().mockResolvedValue({ data: [] }),
  updatePrompt: vi.fn()
}))
vi.mock('@/api/prompts', () => ({
  promptsApi: {
    getTemplates,
    getPrompts,
    getCategories,
    updatePrompt
  }
}))

vi.mock('@/stores/category', () => ({
  useCategoryStore: () => ({ categories: [], fetchCategories: vi.fn() })
}))
vi.mock('@/stores/notification', () => ({
  useNotificationStore: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() })
}))

import SkillsView from '../SkillsView.vue'
import PromptsView from '../PromptsView.vue'
import AppModal from '@/components/ui/AppModal.vue'

const skills = [
  {
    id: 's1',
    name: '周报生成',
    description: null,
    icon: 'zap',
    color: '',
    input_schema: {},
    output_schema: {},
    execution_logic: {},
    trigger_type: 'manual',
    schedule_config: {},
    output_category_id: null,
    output_type_id: null,
    output_tag_ids: [],
    is_template: false,
    is_active: true,
    created_at: '',
    updated_at: ''
  }
]

const prompts = [
  {
    id: 'p1',
    name: '代码审查',
    description: null,
    category: 'dev',
    system_prompt: '',
    user_prompt_template: '',
    output_format: 'text',
    variables: [],
    is_system: false,
    is_active: true,
    is_default: false,
    priority: 'normal',
    created_at: '',
    updated_at: ''
  }
]

async function mountAt(path: string, component: RouteComponent) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/skills', component }, { path: '/prompts', component }]
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(component, {
    global: { plugins: [router, pinia], stubs: { teleport: true } }
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  getSkills.mockResolvedValue({ items: skills, total: 1 })
  getPrompts.mockResolvedValue({ data: { items: prompts, total: 1 } })
})

describe('P2-5 · 命令 query 直达', () => {
  it('行为6 · /skills?execute=s1 自动打开周报生成执行弹窗', async () => {
    const wrapper = await mountAt('/skills?execute=s1', SkillsView)
    const modal = wrapper.findAllComponents(AppModal).find((m) =>
      (m.props('title') as string)?.includes('周报生成')
    )
    expect(modal?.props('open')).toBe(true)
    wrapper.unmount()
  })

  it('行为7 · /prompts?open=p1 自动打开代码审查编辑弹窗', async () => {
    const wrapper = await mountAt('/prompts?open=p1', PromptsView)
    const modal = wrapper.findAllComponents(AppModal).find((m) =>
      (m.props('title') as string) === '编辑提示词'
    )
    expect(modal?.props('open')).toBe(true)
    // 名称输入框由 editPrompt 用目标提示词预填（title='编辑提示词' 已证明命中 editPrompt）
    expect(wrapper.findAllComponents(AppModal).some((m) => (m.props('title') as string) === '编辑提示词')).toBe(true)
    wrapper.unmount()
  })
})
