import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { notesApi } from '@/api/notes'
import SearchResults from '../SearchResults.vue'

vi.mock('@/api/notes', () => ({
  notesApi: { list: vi.fn() }
}))

vi.mock('@/stores/folders', () => ({
  useFoldersStore: () => ({ folders: [], fetchFolders: () => Promise.resolve() })
}))

const notes = [
  {
    id: 'n1',
    title: 'RAG 架构',
    content: '介绍 RAG 与 [[向量检索]]',
    folder_id: null,
    linked_note_ids: [],
    tags: [{ id: 'g1', name: 'RAG', color: '#e8ae4c' }],
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-02T00:00:00'
  },
  {
    id: 'n2',
    title: '向量检索',
    content: 'FAISS 实现细节',
    folder_id: null,
    linked_note_ids: [],
    tags: [],
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00'
  }
]

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/search', name: 'Search', component: SearchResults },
      { path: '/notes/:id', component: { template: '<div>笔记详情</div>' } },
      { path: '/library', component: { template: '<div>资料库</div>' } },
      { path: '/ai', component: { template: '<div>AI</div>' } }
    ]
  })
}

async function mountSearch(query = '') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push(query ? `/search?q=${query}` : '/search')
  await router.isReady()

  const wrapper = mount(SearchResults, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('SearchResults 视图', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(notesApi.list).mockReturnValue(Promise.resolve({
      success: true,
      message: 'ok',
      data: { items: notes, total: notes.length, page: 1, page_size: 100 }
    }) as never)
  })

  it('按路由关键词加载并分组高亮命中词', async () => {
    const { wrapper } = await mountSearch('RAG')

    expect(notesApi.list).toHaveBeenCalledWith({ page_size: 100, page: 1 })
    expect(wrapper.findAll('.search__group').length).toBe(2) // NOTES + TAGS
    expect(wrapper.find('.search__group .hit__title').html()).toContain('<mark>RAG</mark>')
    expect(wrapper.text()).toContain('RAG 架构')
    expect(wrapper.text()).toContain('1 篇笔记使用')

    wrapper.unmount()
  })

  it('类型 tab 只展示对应分组', async () => {
    const { wrapper } = await mountSearch('RAG')
    const tagTab = wrapper.findAll('.search__tab').find(tab => tab.text().includes('标签'))
    expect(tagTab).toBeDefined()

    await tagTab!.trigger('click')

    expect(wrapper.findAll('.search__group').length).toBe(1)
    expect(wrapper.text()).toContain('TAGS · 标签')
    expect(wrapper.text()).not.toContain('NOTES · 笔记')

    wrapper.unmount()
  })

  it('点击笔记结果跳转到对应笔记', async () => {
    const { wrapper, router } = await mountSearch('RAG')

    await wrapper.find('a.hit').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/notes/n1')
    wrapper.unmount()
  })

  it('点击标签结果跳转到按标签过滤的笔记库', async () => {
    const { wrapper, router } = await mountSearch('RAG')

    const tagHit = wrapper.findAll('button.hit').find(button => button.text().includes('#RAG'))
    expect(tagHit).toBeDefined()
    await tagHit!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/library')
    expect(router.currentRoute.value.query.tag).toBe('g1')
    wrapper.unmount()
  })

  it('点击双链结果跳转到目标笔记', async () => {
    const { wrapper, router } = await mountSearch('向量')

    const linkHit = wrapper.findAll('button.hit').find(button => button.text().includes('[[向量检索]]'))
    expect(linkHit).toBeDefined()
    await linkHit!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/notes/n2')
    wrapper.unmount()
  })
})
