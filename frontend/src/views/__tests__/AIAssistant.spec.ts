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
    deletePreference: vi.fn()
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
