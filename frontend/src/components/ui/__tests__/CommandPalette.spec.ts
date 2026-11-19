import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CommandPalette from '../CommandPalette.vue'

const { push } = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

const notes = [
  { id: 'note-1', label: 'Agentic RAG 设计笔记' },
  { id: 'note-2', label: '知识图谱布局' },
  { id: 'note-3', label: '向量检索实验' },
  { id: 'note-4', label: '提示词版本管理' },
  { id: 'note-5', label: '导入管线复盘' },
  { id: 'note-6', label: '第六篇笔记' }
]

const actions = [{ id: 'action-1', label: '新建笔记', hint: '⌘ N' }]

describe('CommandPalette', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('输入关键词后只保留匹配结果', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, notes, actions },
      global: { stubs: { teleport: true } }
    })
    await nextTick()

    await wrapper.find('.palette__input').setValue('rag')
    expect(wrapper.text()).toContain('Agentic RAG 设计笔记')
    expect(wrapper.text()).not.toContain('观测台')
    expect(wrapper.text()).not.toContain('知识图谱布局')
    wrapper.unmount()
  })

  it('回车执行当前选中项并关闭面板', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, notes, actions },
      global: { stubs: { teleport: true } }
    })
    await nextTick()

    const input = wrapper.find('.palette__input')
    await input.setValue('rag')
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ id: 'note-1' })
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
    wrapper.unmount()
  })

  it('Esc 关闭面板', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true },
      global: { stubs: { teleport: true } }
    })
    await nextTick()

    await wrapper.find('.palette__input').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
    wrapper.unmount()
  })

  it('拼音全拼与首字母也能过滤中文命令（P2-5 补充）', async () => {
    const cnActions = [
      { id: 'a1', label: '新建笔记', hint: '在文件夹中新建' },
      { id: 'a2', label: '关系图谱', hint: '/graph' }
    ]
    const wrapper = mount(CommandPalette, {
      props: { open: true, pages: [], notes: [], actions: cnActions },
      global: { stubs: { teleport: true } }
    })
    await nextTick()

    await wrapper.find('.palette__input').setValue('xinjian')
    expect(wrapper.text()).toContain('新建笔记')
    expect(wrapper.text()).not.toContain('关系图谱')

    await wrapper.find('.palette__input').setValue('gxtp')
    expect(wrapper.text()).toContain('关系图谱')
    expect(wrapper.text()).not.toContain('新建笔记')
    wrapper.unmount()
  })

  it('空查询只展示最近 5 篇笔记', async () => {
    const wrapper = mount(CommandPalette, {
      props: { open: true, notes, actions },
      global: { stubs: { teleport: true } }
    })
    await nextTick()

    expect(wrapper.text()).toContain('知识图谱布局')
    expect(wrapper.text()).not.toContain('第六篇笔记')
    wrapper.unmount()
  })
})
