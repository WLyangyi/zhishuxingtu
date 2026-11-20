import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { agentApi } from '@/api/agent'
import AIAssistant from '../AIAssistant.vue'

const sseState = vi.hoisted(() => ({
  connects: [] as Array<{ url: string; body: Record<string, unknown>; options: any }>
}))

vi.mock('@/utils/sse', () => ({
  SSEClient: class {
    connect(url: string, body: Record<string, unknown>, options: any) {
      sseState.connects.push({ url, body, options })
      return Promise.resolve()
    }
    abort() {}
  }
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ token: '', fetchUser: () => Promise.resolve(), logout: () => {} })
}))

vi.mock('@/api/agent', () => ({
  agentApi: {
    listSessions: vi.fn(),
    createSession: vi.fn(),
    getMessages: vi.fn(),
    getTimeline: vi.fn(),
    getPreferences: vi.fn(),
    deleteSession: vi.fn(),
    clearSession: vi.fn(),
    putPreference: vi.fn(),
    deletePreference: vi.fn(),
    listTasks: vi.fn(),
    switchTask: vi.fn(),
    restoreTask: vi.fn()
  }
}))

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ai', name: 'AIAssistant', component: AIAssistant },
      { path: '/ai/observability', component: { template: '<div>可观测</div>' } },
      { path: '/library', component: { template: '<div>资料库</div>' } },
      { path: '/notes/:id', component: { template: '<div>笔记</div>' } }
    ]
  })
}

async function mountAssistant() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push('/ai')
  await router.isReady()

  const wrapper = mount(AIAssistant, {
    global: {
      plugins: [pinia, router],
      stubs: { RouterLink: { template: '<a><slot /></a>' } }
    }
  })
  await flushPromises()
  return wrapper
}

describe('AIAssistant 视图', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sseState.connects.length = 0
    vi.mocked(agentApi.listSessions).mockReturnValue(Promise.resolve([
      { id: 's1', title: '既有会话', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-02T00:00:00' }
    ]) as never)
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [], pending_approval: null
    }) as never)
    vi.mocked(agentApi.getTimeline).mockReturnValue(Promise.resolve([]) as never)
    vi.mocked(agentApi.getPreferences).mockReturnValue(Promise.resolve({}) as never)
    vi.mocked(agentApi.createSession).mockReturnValue(Promise.resolve({
      id: 's-new', title: '新会话'
    }) as never)
  })

  it('挂载后加载会话列表并切换到首个会话', async () => {
    const wrapper = await mountAssistant()

    expect(wrapper.text()).toContain('既有会话')
    expect(agentApi.getMessages).toHaveBeenCalledWith('s1')
    wrapper.unmount()
  })

  it('可展开会话栏与 Inspector 两栏', async () => {
    const wrapper = await mountAssistant()

    await wrapper.find('button[aria-label="打开会话"]').trigger('click')
    expect(wrapper.find('.assistant__sessions').classes()).toContain('assistant__sessions--open')

    await wrapper.find('button[aria-label="打开 Inspector"]').trigger('click')
    expect(wrapper.find('.assistant__inspector').classes()).toContain('assistant__inspector--open')

    wrapper.unmount()
  })

  it('发送消息后走 SSE 流式输出，完成后落成助手消息', async () => {
    const wrapper = await mountAssistant()

    await wrapper.find('textarea.composer__input').setValue('总结知识库')
    await wrapper.find('button[aria-label="发送"]').trigger('click')
    await flushPromises()

    expect(sseState.connects).toHaveLength(1)
    expect(sseState.connects[0].url).toContain('/api/agent/chat/stream?')
    expect(sseState.connects[0].url).toContain('question=')
    const options = sseState.connects[0].options

    options.onMessage({ type: 'thought', content: '检索知识库' })
    options.onMessage({ type: 'final_answer', answer: '这是流式答案' })
    await nextTick()
    expect(wrapper.find('.stream-trace').text()).toContain('检索知识库')
    expect(wrapper.find('.stream-answer').text()).toContain('这是流式答案')

    options.onComplete()
    await flushPromises()
    expect(wrapper.text()).toContain('这是流式答案')
    expect(wrapper.find('.stream-block').exists()).toBe(false)

    wrapper.unmount()
  })

  it('审批卡出现后批准会走 resume 流并留下审批记录', async () => {
    const wrapper = await mountAssistant()
    await wrapper.find('textarea.composer__input').setValue('保存为笔记')
    await wrapper.find('button[aria-label="发送"]').trigger('click')
    await flushPromises()

    const options = sseState.connects[0].options
    options.onMessage({
      type: 'approval_required',
      tool_name: 'create_note',
      title: '写入确认',
      description: '将总结写入知识库',
      preview: { title: '总结' },
      session_id: 's1',
      tool_call_id: 'tc1'
    })
    await nextTick()
    expect(wrapper.find('.approval-wrap').exists()).toBe(true)
    // 后端在 approval_required 后关闭本轮流；onComplete 结束 loading，审批卡才进入可操作态
    options.onComplete()
    await flushPromises()

    const approve = wrapper.findAll('button').find(button => button.text().includes('批准执行'))
    expect(approve).toBeDefined()
    await approve!.trigger('click')
    await flushPromises()

    expect(sseState.connects).toHaveLength(2)
    expect(sseState.connects[1].url).toContain('/api/agent/resume')
    expect(sseState.connects[1].body).toMatchObject({ approved: true, session_id: 's1' })
    expect(wrapper.text()).toContain('已批准 · create_note')

    wrapper.unmount()
  })

  it('拒绝审批时 resume 请求带 approved=false', async () => {
    const wrapper = await mountAssistant()
    await wrapper.find('textarea.composer__input').setValue('保存为笔记')
    await wrapper.find('button[aria-label="发送"]').trigger('click')
    await flushPromises()

    const options = sseState.connects[0].options
    options.onMessage({
      type: 'approval_required',
      tool_name: 'create_note',
      session_id: 's1',
      tool_call_id: 'tc1'
    })
    await nextTick()
    options.onComplete()
    await flushPromises()
    const reject = wrapper.findAll('button').find(button => button.text() === '拒绝')
    expect(reject).toBeDefined()
    await reject!.trigger('click')
    await flushPromises()

    expect(sseState.connects[1].body).toMatchObject({ approved: false })
    expect(wrapper.text()).toContain('已拒绝 · create_note')

    wrapper.unmount()
  })
})

describe('AIAssistant 会话增强（P2-6）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sseState.connects.length = 0
    vi.mocked(agentApi.listSessions).mockImplementation(((q?: string) => {
      const all = [
        { id: 's1', title: '周报生成讨论', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-02T00:00:00' },
        { id: 's2', title: 'RAG 检索调优', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-02T00:00:00' }
      ]
      const keyword = (q || '').trim().toLowerCase()
      return Promise.resolve(keyword ? all.filter((s) => s.title.toLowerCase().includes(keyword)) : all)
    }) as never)
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [], pending_approval: null
    }) as never)
    vi.mocked(agentApi.getTimeline).mockReturnValue(Promise.resolve([
      { id: 'e1', type: 'tool', tool_name: 'search', args: { q: 'x' } }
    ]) as never)
    vi.mocked(agentApi.getPreferences).mockReturnValue(Promise.resolve({}) as never)
  })

  it('会话列表搜索框按标题过滤并带 q 请求后端', async () => {
    const wrapper = await mountAssistant()
    const search = wrapper.find('.sessions__search input')
    expect(search.exists()).toBe(true)

    await search.setValue('rag')
    await flushPromises()

    expect(agentApi.listSessions).toHaveBeenCalledWith('rag')
    expect(wrapper.text()).toContain('RAG 检索调优')
    expect(wrapper.text()).not.toContain('周报生成讨论')
    wrapper.unmount()
  })

  it('Inspector 导出按钮生成 JSON Blob 下载', async () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:mock')
    const revokeObjectURL = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectURL, configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectURL, configurable: true })
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    const wrapper = await mountAssistant()
    const exportBtn = wrapper.find('button[data-test="export-trace"]')
    expect(exportBtn.exists()).toBe(true)
    await exportBtn.trigger('click')

    expect(createObjectURL).toHaveBeenCalled()
    const blob = createObjectURL.mock.calls[0][0] as Blob
    expect(blob).toBeInstanceOf(Blob)
    expect(clickSpy).toHaveBeenCalled()

    wrapper.unmount()
    clickSpy.mockRestore()
  })
})

describe('AIAssistant 锚点卡片（阶段1b）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sseState.connects.length = 0
  })

  function mockOnMode(overrides: Partial<{ core_intent: unknown }> = {}) {
    vi.mocked(agentApi.listSessions).mockReturnValue(Promise.resolve([
      {
        id: 's1',
        title: '周报生成',
        created_at: '2026-01-01T00:00:00',
        updated_at: '2026-01-02T00:00:00',
        core_intent: overrides.core_intent !== undefined ? overrides.core_intent : { goal: '生成本周工作周报', version: 2 }
      }
    ]) as never)
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [],
      pending_approval: null,
      core_intent: null
    }) as never)
    vi.mocked(agentApi.getTimeline).mockReturnValue(Promise.resolve([]) as never)
    vi.mocked(agentApi.getPreferences).mockReturnValue(Promise.resolve({}) as never)
  }

  it('会话列表展示目标摘要卡片', async () => {
    mockOnMode()
    const wrapper = await mountAssistant()
    expect(wrapper.text()).toContain('生成本周工作周报')
    wrapper.unmount()
  })

  it('switchChat 展示锚点条（goal + version）', async () => {
    mockOnMode()
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [],
      pending_approval: null,
      core_intent: { goal: '生成本周工作周报', constraints: { language: '中文' }, acceptance_criteria: ['覆盖本周要点'] }
    }) as never)

    const wrapper = await mountAssistant()
    const bar = wrapper.find('[data-test="anchor-bar"]')
    expect(bar.exists()).toBe(true)
    expect(bar.text()).toContain('生成本周工作周报')
    expect(bar.text()).toContain('v2')
    wrapper.unmount()
  })

  it('off/shadow 模式（core_intent 为 null）时锚点条隐藏', async () => {
    mockOnMode({ core_intent: null })
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [], pending_approval: null, core_intent: null
    }) as never)

    const wrapper = await mountAssistant()
    expect(wrapper.find('[data-test="anchor-bar"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('锚点 SystemMessage 不进聊天流，消息正常渲染', async () => {
    mockOnMode({ core_intent: null })
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [
        { role: 'user', content: '你好' },
        { role: 'assistant', content: '你好呀，有什么可以帮你？' }
      ],
      pending_approval: null,
      core_intent: null
    }) as never)

    const wrapper = await mountAssistant()
    expect(wrapper.find('[data-test="anchor-bar"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('你好呀，有什么可以帮你？')
    wrapper.unmount()
  })

  it('流结束后版本变化时锚点条显示「已更新」', async () => {
    mockOnMode()
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [], pending_approval: null,
      core_intent: { goal: '生成本周工作周报' }
    }) as never)

    const wrapper = await mountAssistant()
    // 初始 version=2,无更新提示
    expect(wrapper.find('[data-test="anchor-bar"]').text()).not.toContain('已更新')

    // 模拟流结束后 listSessions 返回 version=3
    vi.mocked(agentApi.listSessions).mockReturnValue(Promise.resolve([
      { id: 's1', title: '周报生成', core_intent: { goal: '生成本周工作周报', version: 3 } }
    ]) as never)
    await wrapper.find('textarea.composer__input').setValue('继续')
    await wrapper.find('button[aria-label="发送"]').trigger('click')
    await flushPromises()
    const options = sseState.connects[0].options
    options.onMessage({ type: 'final_answer', answer: '好的' })
    options.onComplete()
    await flushPromises()

    expect(wrapper.find('[data-test="anchor-bar"]').text()).toContain('已更新')
    expect(wrapper.find('[data-test="anchor-bar"]').text()).toContain('v3')
    wrapper.unmount()
  })
})

describe('AIAssistant 任务切换（阶段2.6）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sseState.connects.length = 0
    vi.mocked(agentApi.listSessions).mockReturnValue(Promise.resolve([
      { id: 's1', title: '周报会话', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-02T00:00:00' }
    ]) as never)
    vi.mocked(agentApi.getMessages).mockReturnValue(Promise.resolve({
      messages: [], pending_approval: null, core_intent: null
    }) as never)
    vi.mocked(agentApi.getTimeline).mockReturnValue(Promise.resolve([]) as never)
    vi.mocked(agentApi.getPreferences).mockReturnValue(Promise.resolve({}) as never)
    vi.mocked(agentApi.switchTask).mockResolvedValue({} as never)
    vi.mocked(agentApi.restoreTask).mockResolvedValue({} as never)
  })

  function mockTasks(tasks: unknown[]) {
    vi.mocked(agentApi.listTasks).mockReturnValue(Promise.resolve(tasks) as never)
  }

  it('switchChat 加载任务列表并展示 task-bar', async () => {
    mockTasks([
      { id: 't1', session_id: 's1', title: '写周报', goal: '', constraints: {}, acceptance_criteria: [], phase: 'executing', status: 'active', depends_on: null, intent_version: 1, is_current: true, created_at: null }
    ])
    const wrapper = await mountAssistant()
    const bar = wrapper.find('[data-test="task-bar"]')
    expect(bar.exists()).toBe(true)
    expect(agentApi.listTasks).toHaveBeenCalledWith('s1')
    expect(bar.text()).toContain('写周报')
    wrapper.unmount()
  })

  it('task-bar 展示当前任务与进度(phase/status)', async () => {
    mockTasks([
      { id: 't1', session_id: 's1', title: '写周报', goal: '', constraints: {}, acceptance_criteria: [], phase: 'executing', status: 'active', depends_on: null, intent_version: 1, is_current: true, created_at: null },
      { id: 't2', session_id: 's1', title: '做调研', goal: '', constraints: {}, acceptance_criteria: [], phase: 'clarify', status: 'completed', depends_on: 't1', intent_version: 0, is_current: false, created_at: null }
    ])
    const wrapper = await mountAssistant()
    const bar = wrapper.find('[data-test="task-bar"]')
    expect(bar.text()).toContain('executing')
    expect(bar.text()).toContain('当前')
    expect(bar.text()).toContain('completed')
    wrapper.unmount()
  })

  it('点击非当前任务触发 switchTask 并刷新', async () => {
    mockTasks([
      { id: 't1', session_id: 's1', title: '写周报', goal: '', constraints: {}, acceptance_criteria: [], phase: 'executing', status: 'active', depends_on: null, intent_version: 1, is_current: true, created_at: null },
      { id: 't2', session_id: 's1', title: '做调研', goal: '', constraints: {}, acceptance_criteria: [], phase: 'clarify', status: 'completed', depends_on: 't1', intent_version: 0, is_current: false, created_at: null }
    ])
    const wrapper = await mountAssistant()
    const chips = wrapper.findAll('.task-chip')
    expect(chips[0].attributes('disabled')).toBeDefined()
    await chips[1].trigger('click')
    await flushPromises()
    expect(agentApi.switchTask).toHaveBeenCalledWith('s1', 't2')
    expect(agentApi.listTasks).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('无任务时 task-bar 隐藏', async () => {
    mockTasks([])
    const wrapper = await mountAssistant()
    expect(wrapper.find('[data-test="task-bar"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
