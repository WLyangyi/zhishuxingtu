import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { notesApi } from '@/api/notes'
import { foldersApi } from '@/api/folders'
import { categoriesApi } from '@/api/categories'
import { tagsApi } from '@/api/tags'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import NoteEditor from '../NoteEditor.vue'
import type { Note } from '@/types/note'

vi.mock('@/api/notes', () => ({
  notesApi: {
    list: vi.fn(),
    get: vi.fn(),
    getBacklinks: vi.fn(),
    getUnlinkedMentions: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    recordView: vi.fn()
  }
}))

vi.mock('@/api/folders', () => ({
  foldersApi: { list: vi.fn() }
}))

vi.mock('@/api/categories', () => ({
  categoriesApi: { getCategories: vi.fn() },
  contentsApi: {
    getContent: vi.fn(),
    getBacklinks: vi.fn(),
    createContent: vi.fn(),
    updateContent: vi.fn(),
    deleteContent: vi.fn()
  }
}))

vi.mock('@/api/tags', () => ({
  tagsApi: { list: vi.fn(), create: vi.fn() }
}))

const existing: Note = {
  id: 'n1',
  title: '笔记本',
  content: '已有内容',
  folder_id: null,
  linked_note_ids: [],
  tags: [],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-02T00:00:00'
}

function ok<T>(data: T) {
  return Promise.resolve({ code: 0, message: 'ok', data })
}

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/library', name: 'Library', component: { template: '<div />' } },
      { path: '/notes/new', name: 'NewNote', component: { template: '<div />' } },
      { path: '/notes/:id', name: 'NoteEditor', component: { template: '<div />' } }
    ]
  })
}

async function mountEditor() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push({ name: 'NoteEditor', params: { id: 'n1' } })
  await router.isReady()
  const wrapper = mount(NoteEditor, {
    global: { plugins: [router, pinia] },
    attachTo: document.body
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(notesApi.list).mockReturnValue(ok({ items: [], total: 0, page: 1, page_size: 100 }) as never)
  vi.mocked(notesApi.get).mockReturnValue(ok(existing) as never)
  vi.mocked(notesApi.getBacklinks).mockReturnValue(ok({ items: [], total: 0 }) as never)
  vi.mocked(notesApi.getUnlinkedMentions).mockReturnValue(Promise.resolve([]) as never)
  // reportNoteView 内部对返回值链式 .catch，mock 必须返回 Promise
  vi.mocked(notesApi.recordView).mockReturnValue(Promise.resolve({ code: 0, data: null }) as never)
  vi.mocked(foldersApi.list).mockReturnValue(ok([]) as never)
  vi.mocked(categoriesApi.getCategories).mockReturnValue(ok([]) as never)
  vi.mocked(tagsApi.list).mockReturnValue(ok([]) as never)
})

describe('NoteEditor 未链接提及（P2-4）', () => {
  const otherNote: Note = {
    id: 'n2',
    title: 'Agent 记忆',
    content: '',
    folder_id: null,
    linked_note_ids: [],
    tags: [],
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-02T00:00:00'
  }

  it('rail 列出正文中的未链接提及，一键建链后转为出链', async () => {
    vi.mocked(notesApi.list).mockReturnValue(
      ok({ items: [existing, otherNote], total: 2, page: 1, page_size: 100 }) as never
    )
    vi.mocked(notesApi.get).mockReturnValue(
      ok({ ...existing, content: '今天提到了 Agent 记忆 但还没建链' }) as never
    )

    const wrapper = await mountEditor()

    const mentionSection = wrapper.findAll('.rail__block').find((block) =>
      block.text().includes('未链接提及')
    )
    expect(mentionSection).toBeDefined()
    expect(mentionSection!.text()).toContain('Agent 记忆')

    // 一键建链：把纯文本提及替换为 [[...]]，出链计数 +1
    const linkRow = mentionSection!.find('.rail__mention-link')
    expect(linkRow.exists()).toBe(true)
    await linkRow.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('1 LINKS')
    // 建链后未链接提及区块整体消失（v-if 长度为 0）
    const mentionAfter = wrapper
      .findAll('.rail__block')
      .find((block) => block.text().includes('未链接提及'))
    expect(mentionAfter).toBeUndefined()

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('服务端预计算的提及并入 rail，且与本地结果按 id 去重', async () => {
    // 本地 allNotes 不含该笔记（模拟 >500 篇分页上限），只有服务端接口能给出
    const serverOnly = { id: 'n9', title: '仅服务端可见的笔记' }
    vi.mocked(notesApi.list).mockReturnValue(
      ok({ items: [existing, otherNote], total: 2, page: 1, page_size: 100 }) as never
    )
    vi.mocked(notesApi.get).mockReturnValue(
      ok({ ...existing, content: '提到 Agent 记忆 与 仅服务端可见的笔记' }) as never
    )
    vi.mocked(notesApi.getUnlinkedMentions).mockReturnValue(
      Promise.resolve([otherNote, serverOnly].map((n) => ({ id: n.id, title: n.title, created_at: '' }))) as never
    )

    const wrapper = await mountEditor()

    expect(notesApi.getUnlinkedMentions).toHaveBeenCalledWith('n1')
    const mentionSection = wrapper.findAll('.rail__block').find((block) =>
      block.text().includes('未链接提及')
    )
    // 两条都在，且 otherNote 只出现一次（去重）
    expect(mentionSection!.text()).toContain('Agent 记忆')
    expect(mentionSection!.text()).toContain('仅服务端可见的笔记')
    expect(mentionSection!.findAll('.rail__mention-link')).toHaveLength(2)

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})

describe('NoteEditor 编辑态 [[ ]] 内联高亮（P6-②）', () => {
  it('行为4 · overlay 镜像渲染 wiki 段高亮，输入实时更新', async () => {
    const wrapper = await mountEditor()

    // 加载完成默认预览态，点击分段控件第一个选项（编辑）切到编辑态
    const segment = wrapper.findComponent(SegmentedControl)
    const segmentButtons = segment.findAll('button')
    await segmentButtons[0]!.trigger('click')
    await flushPromises()

    const mirror = wrapper.find('.editor__mirror')
    expect(mirror.exists()).toBe(true)

    // 输入包含闭合链接的正文
    await wrapper.find('.editor__input').setValue('看 [[RAG 笔记]] 学习')

    const wikiSpans = wrapper.findAll('.editor__mirror .editor__hl--wiki')
    expect(wikiSpans).toHaveLength(1)
    expect(wikiSpans[0].text()).toBe('[[RAG 笔记]]')
    // 镜像文本与 textarea 内容一致（拼接无损）
    expect(wrapper.find('.editor__mirror').text()).toBe('看 [[RAG 笔记]] 学习')

    // 清空后无高亮段
    await wrapper.find('.editor__input').setValue('没有链接')
    expect(wrapper.findAll('.editor__hl--wiki')).toHaveLength(0)

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
