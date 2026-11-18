import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { notesApi } from '@/api/notes'
import { foldersApi } from '@/api/folders'
import { categoriesApi } from '@/api/categories'
import { tagsApi } from '@/api/tags'
import Library from '../Library.vue'
import { useNotificationStore } from '@/stores/notification'
import type { Category } from '@/types/category'
import type { FolderTree } from '@/types/folder'
import type { Note } from '@/types/note'

vi.mock('@/api/notes', () => ({
  notesApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    recordView: vi.fn()
  }
}))

vi.mock('@/api/folders', () => ({
  foldersApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() }
}))

vi.mock('@/api/categories', () => ({
  categoriesApi: {
    getCategories: vi.fn(),
    createCategory: vi.fn(),
    updateCategory: vi.fn(),
    deleteCategory: vi.fn()
  },
  contentsApi: {}
}))

vi.mock('@/api/tags', () => ({
  tagsApi: { list: vi.fn(), create: vi.fn() }
}))

const category: Category = {
  id: 'c1',
  name: '工作',
  icon: 'folder',
  color: '#8fa3b8',
  sort_order: 0,
  is_system: false,
  created_at: '',
  content_types: []
}

const folder: FolderTree = {
  id: 'f1',
  name: '研发',
  parent_id: null,
  level: 0,
  category_id: 'c1',
  note_count: 1,
  created_at: '',
  children: []
}

function note(id: string, title: string, categoryId: string | null, folderId: string | null): Note {
  return {
    id,
    title,
    content: `${title} 的正文`,
    folder_id: folderId,
    category_id: categoryId,
    linked_note_ids: [],
    tags: [],
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-02T00:00:00'
  } as Note
}

const noteList = [
  note('n1', '部署手册', 'c1', null),
  note('n2', '会议纪要', 'c1', 'f1')
]

function ok<T>(data: T) {
  return Promise.resolve({ code: 0, message: 'ok', data })
}

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/library', name: 'Library', component: { template: '<div />' } },
      { path: '/library/:categoryId', name: 'LibraryDetail', component: { template: '<div />' } },
      { path: '/notes/new', name: 'NewNote', component: { template: '<div />' } },
      { path: '/notes/:id', name: 'NoteEditor', component: { template: '<div />' } },
      { path: '/import-history', name: 'ImportHistory', component: { template: '<div />' } }
    ]
  })
}

async function mountLibrary(route = '/library') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push(route)
  await router.isReady()
  const wrapper = mount(Library, {
    global: { plugins: [router, pinia] },
    attachTo: document.body
  })
  await flushPromises()
  return wrapper
}

let createdFolders: FolderTree[] = []

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  createdFolders = []
  folder.name = '研发'
  vi.mocked(notesApi.list).mockReturnValue(ok({ items: noteList, total: 2, page: 1, page_size: 100 }) as never)
  vi.mocked(foldersApi.list).mockImplementation(
    (() => ok([folder, ...createdFolders])) as never
  )
  vi.mocked(foldersApi.create).mockImplementation(((data: { name: string; category_id?: string; parent_id?: string }) => {
    const created: FolderTree = {
      ...folder,
      id: 'f9',
      name: data.name,
      category_id: data.category_id ?? 'c1',
      parent_id: data.parent_id ?? null,
      children: []
    }
    createdFolders.push(created)
    return ok(created)
  }) as never)
  vi.mocked(foldersApi.update).mockImplementation(((_id: string, data: { name?: string }) => {
    Object.assign(folder, { name: data.name ?? folder.name })
    return ok(folder)
  }) as never)
  vi.mocked(foldersApi.delete).mockReturnValue(ok(null) as never)
  vi.mocked(categoriesApi.getCategories).mockReturnValue(ok([category]) as never)
  vi.mocked(categoriesApi.createCategory).mockReturnValue(
    ok({ ...category, id: 'c9', name: '素材库' }) as never
  )
  vi.mocked(categoriesApi.updateCategory).mockImplementation(((_id: string, data: { name?: string }) =>
    ok({ ...category, name: data.name ?? category.name })) as never)
  vi.mocked(categoriesApi.deleteCategory).mockReturnValue(ok(null) as never)
  vi.mocked(tagsApi.list).mockReturnValue(ok([]) as never)
})

describe('Library 分类/文件夹 CRUD（P6-③）', () => {
  it('行为1 · 树头新建分类：提交后调用创建接口并渲染到树', async () => {
    const wrapper = await mountLibrary()

    await wrapper.find('.tree__add').trigger('click')
    expect(wrapper.findComponent({ name: 'AppModal' }).exists()).toBe(true)

    const input = document.querySelector('.zs-modal input') as HTMLInputElement
    input.value = '素材库'
    input.dispatchEvent(new Event('input'))
    await flushPromises()

    const confirm = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('创建')
    ) as HTMLButtonElement
    confirm.click()
    await flushPromises()

    expect(categoriesApi.createCategory).toHaveBeenCalledWith({ name: '素材库' })
    expect(wrapper.text()).toContain('素材库')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为2 · 分类行菜单新建子文件夹', async () => {
    const wrapper = await mountLibrary()

    // 分类行 ⋯ 按钮 → 菜单
    const categoryRow = wrapper.findAll('.tree__item--category')[0]
    await categoryRow.find('.tree__more').trigger('click')
    expect(wrapper.find('.tree-menu').exists()).toBe(true)

    // 菜单项「新建文件夹」→ 表单弹窗（teleport 到 body）
    const menuItem = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('新建文件夹'))
    expect(menuItem).toBeTruthy()
    await menuItem!.trigger('click')
    expect(document.body.textContent).toContain('新建文件夹')

    const input = document.querySelector('.zs-modal input') as HTMLInputElement
    input.value = 'AI 落地'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    const confirm = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('创建')
    ) as HTMLButtonElement
    confirm.click()
    await flushPromises()

    expect(foldersApi.create).toHaveBeenCalledWith({ name: 'AI 落地', category_id: 'c1' })
    expect(wrapper.text()).toContain('AI 落地')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为3 · 重命名分类：预填原名，提交后树更新', async () => {
    const wrapper = await mountLibrary()

    const categoryRow = wrapper.findAll('.tree__item--category')[0]
    await categoryRow.find('.tree__more').trigger('click')
    const renameItem = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('重命名'))
    await renameItem!.trigger('click')

    // 预填原名
    const input = document.querySelector('.zs-modal input') as HTMLInputElement
    expect(input.value).toBe('工作')

    input.value = '工作区'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    const confirm = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('保存')
    ) as HTMLButtonElement
    confirm.click()
    await flushPromises()

    expect(categoriesApi.updateCategory).toHaveBeenCalledWith('c1', { name: '工作区' })
    expect(wrapper.text()).toContain('工作区')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为4 · 删除分类：确认弹窗双分支，取消不删、确认后树移除', async () => {
    const wrapper = await mountLibrary()

    const categoryRow = wrapper.findAll('.tree__item--category')[0]
    await categoryRow.find('.tree__more').trigger('click')
    const deleteItem = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('删除'))
    expect(deleteItem).toBeTruthy()
    await deleteItem!.trigger('click')

    // 确认弹窗出现（danger 确认按钮）
    const footerButtons = () => [...document.querySelectorAll('.zs-modal__footer button')]
    expect(document.body.textContent).toContain('删除分类')

    // 取消 → 不删除
    const cancel = footerButtons().find((b) => b.textContent?.includes('取消')) as HTMLButtonElement
    cancel.click()
    await flushPromises()
    expect(categoriesApi.deleteCategory).not.toHaveBeenCalled()

    // 再开菜单并确认删除
    const row2 = wrapper.findAll('.tree__item--category')[0]
    await row2.find('.tree__more').trigger('click')
    const deleteItem2 = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('删除'))
    await deleteItem2!.trigger('click')
    const confirm = footerButtons().find((b) => b.textContent?.includes('删除')) as HTMLButtonElement
    confirm.click()
    await flushPromises()

    expect(categoriesApi.deleteCategory).toHaveBeenCalledWith('c1')
    expect(wrapper.text()).not.toContain('工作')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为5 · 重命名与删除文件夹', async () => {
    const wrapper = await mountLibrary()

    // 重命名文件夹
    const folderRow = wrapper.findAll('.tree__item--folder')[0]
    await folderRow.find('.tree__more').trigger('click')
    const renameItem = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('重命名'))
    await renameItem!.trigger('click')

    const input = document.querySelector('.zs-modal input') as HTMLInputElement
    expect(input.value).toBe('研发')
    input.value = '研发部'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    const save = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('保存')
    ) as HTMLButtonElement
    save.click()
    await flushPromises()

    expect(foldersApi.update).toHaveBeenCalledWith('f1', { name: '研发部' })
    expect(wrapper.text()).toContain('研发部')

    // 删除文件夹
    const folderRow2 = wrapper.findAll('.tree__item--folder')[0]
    await folderRow2.find('.tree__more').trigger('click')
    const deleteItem = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('删除'))
    await deleteItem!.trigger('click')
    const confirm = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('删除')
    ) as HTMLButtonElement
    confirm.click()
    await flushPromises()

    expect(foldersApi.delete).toHaveBeenCalledWith('f1')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('行为6 · 删除失败时分类保留并提示错误', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const notification = useNotificationStore()
    const errorSpy = vi.spyOn(notification, 'error')

    const router = makeRouter()
    await router.push('/library')
    await router.isReady()
    vi.mocked(categoriesApi.deleteCategory).mockRejectedValue({
      isAxiosError: true,
      message: 'Request failed',
      response: { status: 409, data: { detail: '分类下仍有内容，无法删除' } }
    })
    const wrapper = mount(Library, { global: { plugins: [router, pinia] }, attachTo: document.body })
    await flushPromises()

    const categoryRow = wrapper.findAll('.tree__item--category')[0]
    await categoryRow.find('.tree__more').trigger('click')
    const deleteItem = wrapper.findAll('.tree-menu__item').find((i) => i.text().includes('删除'))
    await deleteItem!.trigger('click')
    const confirm = [...document.querySelectorAll('.zs-modal__footer button')].find((b) =>
      b.textContent?.includes('删除')
    ) as HTMLButtonElement
    confirm.click()
    await flushPromises()

    // 分类保留在树中
    expect(wrapper.text()).toContain('工作')
    // 出现错误提示
    expect(errorSpy).toHaveBeenCalled()

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
