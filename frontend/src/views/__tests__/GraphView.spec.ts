import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GraphView from '../GraphView.vue'

const graph = vi.hoisted(() => ({
  data: null as any,
  error: '',
  load: vi.fn()
}))

vi.mock('@/stores/graph', () => ({ useGraphStore: () => graph }))
vi.mock('@/stores/theme', () => ({ useThemeStore: () => ({ isDark: true }) }))

const data = {
  nodes: [
    { id: 'n1', label: '笔记一', type: 'note', color: '#8fa3b8', size: 18 },
    { id: 't1', label: '标签', type: 'tag', color: '#e8ae4c', size: 15 }
  ],
  edges: [{ source: 'n1', target: 't1', type: 'has_tag' }]
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/graph', component: GraphView },
      { path: '/notes/new', component: { template: '<div>新建笔记</div>' } },
      { path: '/notes/:id', component: { template: '<div>笔记</div>' } }
    ]
  })
}

async function mountGraph() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push('/graph')
  await router.isReady()

  const wrapper = mount(GraphView, {
    global: {
      plugins: [pinia, router],
      stubs: {
        SegmentedControl: {
          props: ['modelValue', 'items'],
          template: `<button class="layout-stub" @click="$emit('update:modelValue','radial')">{{ modelValue }}</button>`
        }
      }
    }
  })
  return { wrapper, router }
}

describe('GraphView 视图', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    graph.data = data
    graph.error = ''
    graph.load.mockImplementation(() => Promise.resolve(data))
  })

  it('加载中显示状态卡片', async () => {
    graph.load.mockImplementation(() => new Promise(() => {}))
    const { wrapper } = await mountGraph()
    await nextTick()

    expect(wrapper.text()).toContain('LOADING STAR ATLAS…')
    wrapper.unmount()
  })

  it('加载失败显示错误与重新加载按钮', async () => {
    graph.load.mockImplementation(() => Promise.reject(new Error('network')))
    const { wrapper } = await mountGraph()
    await flushPromises()

    expect(wrapper.text()).toContain('星图加载失败')
    expect(wrapper.findAll('button').some(button => button.text() === '重新加载')).toBe(true)
    wrapper.unmount()
  })

  it('空数据显示空态', async () => {
    graph.load.mockImplementation(() => Promise.resolve({ nodes: [], edges: [] }))
    const { wrapper } = await mountGraph()
    await flushPromises()

    expect(wrapper.text()).toContain('星图还是空的')
    wrapper.unmount()
  })

  it('类型过滤联动更新节点统计', async () => {
    const { wrapper } = await mountGraph()
    await flushPromises()
    expect(wrapper.find('.graph__stats').text()).toContain('2 STARS')

    const noteFilter = wrapper.findAll('.graph__filter').find(button => button.text().includes('笔记'))
    expect(noteFilter).toBeDefined()
    await noteFilter!.trigger('click')
    await nextTick()

    expect(wrapper.find('.graph__stats').text()).toContain('1 STARS')
    wrapper.unmount()
  })

  it('连接列表展示全部连接而非仅前 8 条', async () => {
    const many = {
      nodes: [
        { id: 'center', label: '中心', type: 'note', color: '#8fa3b8', size: 18 },
        ...Array.from({ length: 10 }, (_, index) => ({
          id: `n${index}`,
          label: `邻居${index}`,
          type: 'note' as const,
          color: '#8fa3b8',
          size: 18
        }))
      ],
      edges: Array.from({ length: 10 }, (_, index) => ({
        source: 'center',
        target: `n${index}`,
        type: 'links_to'
      }))
    }
    graph.load.mockImplementation(() => Promise.resolve(many))
    const { wrapper } = await mountGraph()
    await flushPromises()

    ;(wrapper.vm as any).selectById('center')
    await nextTick()

    expect(wrapper.findAll('.graph__connection').length).toBe(10)
    expect(wrapper.text()).toContain('邻居9')
    wrapper.unmount()
  })

  it('布局控件切换到径向', async () => {
    const { wrapper } = await mountGraph()
    await flushPromises()

    expect(wrapper.find('.layout-stub').text()).toBe('force')
    await wrapper.find('.layout-stub').trigger('click')
    await nextTick()
    expect(wrapper.find('.layout-stub').text()).toBe('radial')
    wrapper.unmount()
  })
})
