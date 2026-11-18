import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import AppToast from '../AppToast.vue'
import { useNotificationStore } from '@/stores/notification'

describe('AppToast（P6-④ 通知统一）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    document.body.innerHTML = ''
  })

  it('渲染 notification store 的通知标题与正文', async () => {
    const store = useNotificationStore()
    store.success('已保存', '笔记已写入知识库')

    const wrapper = mount(AppToast, { attachTo: document.body })
    await flushPromises()

    const body = document.body.textContent ?? ''
    expect(body).toContain('已保存')
    expect(body).toContain('笔记已写入知识库')

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('type 映射为 toast 色调类（error/warning）', async () => {
    const store = useNotificationStore()
    store.error('保存失败', '请稍后重试')
    store.warning('请输入标题', '标题不能为空')

    const wrapper = mount(AppToast, { attachTo: document.body })
    await flushPromises()

    expect(document.body.querySelector('.toast--error')).toBeTruthy()
    expect(document.body.querySelector('.toast--warning')).toBeTruthy()

    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('点击关闭按钮移除对应通知', async () => {
    const store = useNotificationStore()
    store.info('提示', '这条要手动关')
    const id = store.notifications[0].id

    const wrapper = mount(AppToast, { attachTo: document.body })
    await flushPromises()

    const close = document.body.querySelector('.toast__close') as HTMLButtonElement
    close.click()
    await flushPromises()

    expect(store.notifications.find((n) => n.id === id)).toBeUndefined()

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
