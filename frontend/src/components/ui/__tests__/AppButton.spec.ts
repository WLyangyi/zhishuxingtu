import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppButton from '../AppButton.vue'

describe('AppButton', () => {
  it('点击时发出 click 事件', async () => {
    const wrapper = mount(AppButton, { slots: { default: '保存' } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('禁用时带 disabled 属性且不响应点击', async () => {
    const wrapper = mount(AppButton, {
      props: { disabled: true },
      slots: { default: '保存' }
    })

    expect(wrapper.attributes('disabled')).toBeDefined()
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeUndefined()
  })

  it('加载中显示进度、标记忙碌并阻止重复提交', async () => {
    const wrapper = mount(AppButton, {
      props: { loading: true },
      slots: { default: '保存' }
    })

    expect(wrapper.attributes('aria-busy')).toBe('true')
    expect(wrapper.find('.spinner').exists()).toBe(true)
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeUndefined()
  })
})
