import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'
import TopBar from '../TopBar.vue'
import { useCommandPalette } from '@/lib/command'

const Stub = { template: '<div />' }

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/library', name: 'Library', component: Stub },
      { path: '/notes/new', name: 'NewNote', component: Stub }
    ]
  })
}

describe('TopBar', () => {
  it('显示当前页面的中文名与语境词', async () => {
    const router = makeRouter()
    await router.push('/library')
    await router.isReady()

    const wrapper = mount(TopBar, { global: { plugins: [router] } })
    expect(wrapper.text()).toContain('我的笔记')
    expect(wrapper.text()).toContain('LIBRARY')
    expect(wrapper.text()).toContain('新建笔记')
    wrapper.unmount()
  })

  it('点击搜索触发器打开命令面板', async () => {
    const router = makeRouter()
    await router.push('/library')
    await router.isReady()

    const wrapper = mount(TopBar, { global: { plugins: [router] } })
    await wrapper.find('.topbar__search').trigger('click')
    expect(useCommandPalette().state.open).toBe(true)
    useCommandPalette().close()
    wrapper.unmount()
  })

  it('移动端菜单按钮发出 open-menu 事件', async () => {
    const router = makeRouter()
    await router.push('/library')
    await router.isReady()

    const wrapper = mount(TopBar, { global: { plugins: [router] } })
    await wrapper.find('.topbar__menu').trigger('click')
    expect(wrapper.emitted('open-menu')).toHaveLength(1)
    wrapper.unmount()
  })

  it('「新建笔记」跳转到编辑器', async () => {
    const router = makeRouter()
    await router.push('/library')
    await router.isReady()

    const wrapper = mount(TopBar, { global: { plugins: [router] } })
    const newNote = wrapper.findAll('button').find((button) => button.text().includes('新建笔记'))
    expect(newNote).toBeTruthy()
    await newNote?.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/notes/new')
    wrapper.unmount()
  })
})
