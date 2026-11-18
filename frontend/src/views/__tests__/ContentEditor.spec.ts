import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { categoriesApi, contentsApi } from '@/api/categories'
import { tagsApi } from '@/api/tags'
import AppModal from '@/components/ui/AppModal.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import ContentEditor from '../ContentEditor.vue'
import { useNotificationStore } from '@/stores/notification'
import type { Category, Content } from '@/types/category'
import type { Tag } from '@/types'

vi.mock('@/api/categories', () => ({
  categoriesApi: {
    getCategories: vi.fn()
  },
  contentsApi: {
    getContent: vi.fn(),
    getBacklinks: vi.fn(),
    createContent: vi.fn(),
    updateContent: vi.fn(),
    deleteContent: vi.fn()
  }
}))

vi.mock('@/api/tags', () => ({
  tagsApi: {
    list: vi.fn(),
    create: vi.fn()
  }
}))

const typeDoc = { id: 't1', name: '文档', icon: 'file-text', color: '#e8ae4c', field_schema: {} }
const typeImage = { id: 't2', name: '图片', icon: 'image', color: '#8fa3b8', field_schema: {} }

const category: Category = {
  id: 'c1',
  name: '工作',
  icon: 'folder',
  color: '#8fa3b8',
  sort_order: 0,
  is_system: false,
  created_at: '2026-01-01T00:00:00',
  content_types: [typeDoc]
}

const categoryAssets: Category = {
  id: 'c2',
  name: '素材',
  icon: 'folder',
  color: '#9aa68c',
  sort_order: 1,
  is_system: false,
  created_at: '2026-01-01T00:00:00',
  content_types: [typeImage]
}

const categoryEmpty: Category = {
  id: 'c3',
  name: '个人',
  icon: 'folder',
  color: '#d98c7a',
  sort_order: 2,
  is_system: false,
  created_at: '2026-01-01T00:00:00',
  content_types: []
}

const content: Content = {
  id: 'n1',
  type_id: 't1',
  category_id: 'c1',
  user_id: 'u1',
  title: '部署手册',
  content: '## 步骤\n\nFAISS 索引构建后运行冒烟测试。',
  extra_fields: {},
  linked_content_ids: [],
  file_path: null,
  file_url: null,
  file_size: 0,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-02T00:00:00',
  content_type: typeDoc,
  category,
  tags: [{ id: 'g1', name: 'RAG', color: '#e8ae4c' }]
}

const tags: Tag[] = [
  { id: 'g1', name: 'RAG', color: '#e8ae4c', note_count: 2, created_at: '' },
  { id: 'g2', name: 'Vue', color: '#8fa3b8', note_count: 1, created_at: '' }
]

function ok<T>(data: T) {
  return Promise.resolve({ code: 0, message: 'ok', data })
}

export function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/library', name: 'Library', component: { template: '<div />' } },
      {
        path: '/library/:categoryId',
        name: 'LibraryDetail',
        component: { template: '<div />' }
      },
      {
        path: '/library/:categoryId/content/new',
        name: 'NewContent',
        component: { template: '<div />' }
      },
      {
        path: '/library/:categoryId/content/:id',
        name: 'ContentEditor',
        component: { template: '<div />' }
      }
    ]
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(categoriesApi.getCategories).mockReturnValue(
    ok([category, categoryAssets, categoryEmpty]) as never
  )
  vi.mocked(contentsApi.getContent).mockImplementation(((id: string) =>
    id === 'n1' ? ok(content) : Promise.reject(new Error('404'))) as never)
  vi.mocked(contentsApi.getBacklinks).mockReturnValue(
    ok({ items: [{ id: 'b1', title: '架构总览' }], total: 1 }) as never
  )
  vi.mocked(contentsApi.createContent).mockReturnValue(ok({ ...content, id: 'n2' }) as never)
  vi.mocked(contentsApi.updateContent).mockReturnValue(ok(content) as never)
  vi.mocked(contentsApi.deleteContent).mockReturnValue(ok(null) as never)
  vi.mocked(tagsApi.list).mockReturnValue(ok(tags) as never)
  vi.mocked(tagsApi.create).mockImplementation(((data: { name: string }) =>
    ok({ id: 'g9', name: data.name, color: '#e8ae4c', note_count: 0, created_at: '' })) as never)
})

describe('ContentEditor（P6 重制）', () => {
  it('行为1 · 加载详情：标题、正文、反向链接与设计词汇渲染', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, { global: { plugins: [router, pinia] } })
    await flushPromises()

    expect(contentsApi.getContent).toHaveBeenCalledWith('n1')
    expect(contentsApi.getBacklinks).toHaveBeenCalledWith('n1')

    // 新设计词汇：描边字空间层 + readout 元信息
    expect(wrapper.find('.ce__outline').exists()).toBe(true)
    expect(wrapper.find('.ce__outline').text()).toMatch(/COMPOSE/i)

    // 标题与正文填充
    expect((wrapper.find('.ce__title').element as HTMLTextAreaElement).value).toBe('部署手册')
    expect((wrapper.find('.ce__input').element as HTMLTextAreaElement).value).toContain('FAISS')

    // 反向链接列表
    const backlinks = wrapper.findAll('.ce__backlink')
    expect(backlinks).toHaveLength(1)
    expect(backlinks[0].text()).toContain('架构总览')

    wrapper.unmount()
  })

  it('行为2 · 新建模式：空表单、分类按路由预选、标题自动聚焦', async () => {
    const router = makeRouter()
    await router.push({ name: 'NewContent', params: { categoryId: 'c1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    expect(contentsApi.getContent).not.toHaveBeenCalled()
    expect((wrapper.find('.ce__title').element as HTMLTextAreaElement).value).toBe('')
    expect((wrapper.find('.ce__input').element as HTMLTextAreaElement).value).toBe('')

    const selects = wrapper.findAllComponents(AppSelect)
    expect(selects[0].props('modelValue')).toBe('c1')

    // 新建模式：标题框获得焦点，直接开写
    expect(document.activeElement).toBe(wrapper.find('.ce__title').element)

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为3 · 空标题保存拦截：弹出警告且不发起创建请求', async () => {
    const router = makeRouter()
    await router.push({ name: 'NewContent', params: { categoryId: 'c1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const notification = useNotificationStore()
    const warnSpy = vi.spyOn(notification, 'warning')

    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    // 只填正文，标题留空
    await wrapper.find('.ce__input').setValue('没有标题的正文')
    const saveButton = wrapper.findAll('button').find((b) => b.text().includes('保存'))
    expect(saveButton).toBeTruthy()
    await saveButton!.trigger('click')
    await flushPromises()

    expect(contentsApi.createContent).not.toHaveBeenCalled()
    expect(warnSpy).toHaveBeenCalled()

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为4 · 创建内容：payload 正确并跳转到详情页', async () => {
    const router = makeRouter()
    await router.push({ name: 'NewContent', params: { categoryId: 'c1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    // 分类加载后，内容类型应自动预选第一个
    const selects = wrapper.findAllComponents(AppSelect)
    expect(selects[1].props('modelValue')).toBe('t1')

    await wrapper.find('.ce__title').setValue('部署手册 v2')
    await wrapper.find('.ce__input').setValue('新的部署步骤')

    const saveButton = wrapper.findAll('button').find((b) => b.text().includes('保存'))
    await saveButton!.trigger('click')
    await flushPromises()

    expect(contentsApi.createContent).toHaveBeenCalledTimes(1)
    expect(contentsApi.createContent).toHaveBeenCalledWith({
      title: '部署手册 v2',
      content: '新的部署步骤',
      type_id: 't1',
      category_id: 'c1',
      tag_ids: []
    })
    expect(router.currentRoute.value.fullPath).toBe('/library/c1/content/n2')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为5 · 更新内容：编辑后进入脏状态，保存调用更新接口', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    // 修改标题 → 状态点进入未保存（DIRTY）
    await wrapper.find('.ce__title').setValue('部署手册（修订）')
    expect(wrapper.find('.ce__save-text').text()).toBe('DIRTY')

    const saveButton = wrapper.findAll('button').find((b) => b.text().includes('保存'))
    await saveButton!.trigger('click')
    await flushPromises()

    expect(contentsApi.updateContent).toHaveBeenCalledTimes(1)
    expect(contentsApi.updateContent).toHaveBeenCalledWith('n1', {
      title: '部署手册（修订）',
      content: '## 步骤\n\nFAISS 索引构建后运行冒烟测试。',
      type_id: 't1',
      category_id: 'c1',
      tag_ids: ['g1']
    })

    // 保存成功 → 状态点 SAVED
    expect(wrapper.find('.ce__save-text').text()).toBe('SAVED')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为6 · 删除需确认：确认后删除并返回列表，取消不删除', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    // 点删除 → 确认弹窗打开（不再用 window.confirm）
    const deleteButton = wrapper.findAll('button').find((b) => b.text().includes('删除'))
    await deleteButton!.trigger('click')
    await flushPromises()

    const modal = wrapper.findComponent(AppModal)
    expect(modal.exists()).toBe(true)
    expect(modal.props('open')).toBe(true)

    // 取消 → 不删除
    const cancelButton = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('取消')
    )
    expect(cancelButton).toBeTruthy()
    ;(cancelButton as HTMLButtonElement).click()
    await flushPromises()
    expect(contentsApi.deleteContent).not.toHaveBeenCalled()
    expect(modal.props('open')).toBe(false)

    // 重新打开并确认 → 删除 + 返回分类列表
    await deleteButton!.trigger('click')
    await flushPromises()
    const confirmButton = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('删除')
    )
    ;(confirmButton as HTMLButtonElement).click()
    await flushPromises()

    expect(contentsApi.deleteContent).toHaveBeenCalledWith('n1')
    expect(router.currentRoute.value.fullPath).toBe('/library/c1')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为7 · 标签勾选：点击切换选中态并反映到保存 payload', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    const tagChip = (name: string) =>
      wrapper.findAll('.ce__tag').find((c) => c.text() === `#${name}`)!
    expect(tagChip('RAG').classes()).toContain('ce__tag--on')
    expect(tagChip('Vue').classes()).not.toContain('ce__tag--on')

    // 勾选 Vue
    await tagChip('Vue').trigger('click')
    expect(tagChip('Vue').classes()).toContain('ce__tag--on')

    // 保存 → payload 携带两个标签
    const saveButton = wrapper.findAll('button').find((b) => b.text().includes('保存'))
    await saveButton!.trigger('click')
    await flushPromises()
    expect(vi.mocked(contentsApi.updateContent).mock.calls[0][1].tag_ids).toEqual(['g1', 'g2'])

    // 取消勾选 RAG
    await tagChip('RAG').trigger('click')
    expect(tagChip('RAG').classes()).not.toContain('ce__tag--on')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为8 · 新建标签：Enter 创建并自动勾选，Esc 关闭输入', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    // 打开新建标签输入
    await wrapper.find('.ce__tag-add').trigger('click')
    const newInput = wrapper.find('.ce__tag-new-input')
    expect(newInput.exists()).toBe(true)
    expect(document.activeElement).toBe(newInput.element)

    // Esc 关闭
    await newInput.trigger('keydown.escape')
    expect(wrapper.find('.ce__tag-new-input').exists()).toBe(false)

    // 再次打开，输入名称并回车
    await wrapper.find('.ce__tag-add').trigger('click')
    await wrapper.find('.ce__tag-new-input').setValue('测试标签')
    await wrapper.find('.ce__tag-new-input').trigger('keydown.enter')
    await flushPromises()

    expect(tagsApi.create).toHaveBeenCalledWith({ name: '测试标签' })
    const newChip = wrapper.findAll('.ce__tag').find((c) => c.text() === '#测试标签')
    expect(newChip).toBeTruthy()
    expect(newChip!.classes()).toContain('ce__tag--on')
    expect(wrapper.find('.ce__tag-new-input').exists()).toBe(false)

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为9 · 反向链接点击跳转到对应内容', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    const backlink = wrapper.find('.ce__backlink')
    expect(backlink.text()).toContain('架构总览')
    await backlink.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/library/c1/content/b1')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为10 · 内容不存在：空状态提示且隐藏保存操作，返回按钮可回列表', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'missing' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    expect(wrapper.text()).toContain('内容不存在')
    expect(wrapper.find('.ce__title').exists()).toBe(false)
    // 错误态下没有可保存的东西
    expect(wrapper.findAll('button').find((b) => b.text().includes('保存'))).toBeUndefined()

    const back = wrapper.findAll('button').find((b) => b.text().includes('返回'))
    await back!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/library')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为11 · 分类切换联动：类型落到新分类第一个；空类型分类清空类型', async () => {
    const router = makeRouter()
    await router.push({ name: 'ContentEditor', params: { categoryId: 'c1', id: 'n1' } })
    await router.isReady()

    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(ContentEditor, {
      global: { plugins: [router, pinia] },
      attachTo: document.body
    })
    await flushPromises()

    const selects = wrapper.findAllComponents(AppSelect)

    // 切到「素材」c2 → 类型自动落到 t2 图片
    await selects[0].vm.$emit('update:modelValue', 'c2')
    await flushPromises()
    expect(selects[0].props('modelValue')).toBe('c2')
    expect(selects[1].props('modelValue')).toBe('t2')

    // 切到「个人」c3（无类型）→ 类型清空，不得残留 t1/t2
    await selects[0].vm.$emit('update:modelValue', 'c3')
    await flushPromises()
    expect(selects[1].props('modelValue')).toBe('')

    // 空类型下保存 → 拦截
    const saveButton = wrapper.findAll('button').find((b) => b.text().includes('保存'))
    await saveButton!.trigger('click')
    await flushPromises()
    expect(contentsApi.updateContent).not.toHaveBeenCalled()

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
