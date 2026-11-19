import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { homeApi } from '@/api/home'
import { notesApi } from '@/api/notes'
import Home from '../Home.vue'

vi.mock('@/api/home', () => ({ homeApi: { overview: vi.fn() } }))
vi.mock('@/api/notes', () => ({ notesApi: { list: vi.fn() } }))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ user: { username: '测试观测员' } })
}))

const overview = {
  stats: { notes: 12, tags: 3, folders: 2, categories: 3, words: 4800, links: 5 },
  recent_notes: [{
    id: 'n2',
    title: '最近编辑的笔记',
    excerpt: '摘要内容',
    updated_at: '2026-01-02T00:00:00',
    folder_id: null,
    category_id: null,
    link_count: 1
  }],
  recent_reads: [{
    note_id: 'n1',
    title: '继续阅读的笔记',
    excerpt: '上次读到这里',
    viewed_at: '2026-01-03T00:00:00'
  }],
  top_tags: [{ id: 'g1', name: 'RAG', note_count: 4 }],
  areas: [{ id: 'c1', name: '工作', note_count: 7 }]
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: Home },
      { path: '/notes/:id', component: { template: '<div>笔记</div>' } }
    ]
  })
}

async function mountHome() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push('/')
  await router.isReady()
  const wrapper = mount(Home, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('Home 视图', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(homeApi.overview).mockReturnValue(Promise.resolve({
      success: true, message: 'ok', data: overview
    }) as never)
  })

  it('渲染 overview 聚合数据', async () => {
    const { wrapper } = await mountHome()

    expect(wrapper.text()).toContain('测试观测员')
    expect(wrapper.text()).toContain('最近编辑的笔记')
    expect(wrapper.text()).toContain('3 个标签')
    expect(wrapper.text()).toContain('WORK')
    expect(wrapper.text()).toContain('12 篇笔记')

    wrapper.unmount()
  })

  it('继续阅读卡片跳到上次阅读的笔记', async () => {
    const { wrapper, router } = await mountHome()

    const link = wrapper.find('a.continue__item')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('/notes/n1')
    await link.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/notes/n1')
    wrapper.unmount()
  })

  it('overview 失败时回退到笔记列表', async () => {
    vi.mocked(homeApi.overview).mockReturnValue(Promise.reject(new Error('500')) as never)
    vi.mocked(notesApi.list).mockReturnValue(Promise.resolve({
      success: true,
      message: 'ok',
      data: {
        items: [{ ...overview.recent_notes[0], id: 'fallback-1', title: '回退笔记' }],
        total: 1,
        page: 1,
        page_size: 5
      }
    }) as never)

    const { wrapper } = await mountHome()

    expect(notesApi.list).toHaveBeenCalledWith({ page_size: 5 })
    expect(wrapper.text()).toContain('回退笔记')

    wrapper.unmount()
  })
})
