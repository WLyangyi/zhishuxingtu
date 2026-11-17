import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AppModal from '../AppModal.vue'

describe('AppModal', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('打开时渲染标题与内容', async () => {
    const wrapper = mount(AppModal, {
      props: { open: true, title: '导入笔记' },
      slots: { default: '拖入文件开始导入' },
      attachTo: document.body
    })
    await nextTick()

    expect(document.body.textContent).toContain('导入笔记')
    expect(document.body.textContent).toContain('拖入文件开始导入')
    wrapper.unmount()
  })

  it('点击关闭按钮请求关闭', async () => {
    const wrapper = mount(AppModal, {
      props: { open: true, title: '导入笔记' },
      attachTo: document.body
    })
    await nextTick()

    const close = document.querySelector<HTMLElement>('[aria-label="关闭"]')
    expect(close).not.toBeNull()
    close?.click()
    await nextTick()

    const events = wrapper.emitted('update:open') ?? []
    expect(events[events.length - 1]).toEqual([false])
    wrapper.unmount()
  })
})
