import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppSwitch from '../AppSwitch.vue'

describe('AppSwitch', () => {
  it('点击后切换为开启', async () => {
    const wrapper = mount(AppSwitch, { props: { modelValue: false } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([true])
  })

  it('已开启时点击切换为关闭', async () => {
    const wrapper = mount(AppSwitch, { props: { modelValue: true } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })

  it('禁用时不响应点击', async () => {
    const wrapper = mount(AppSwitch, { props: { modelValue: false, disabled: true } })
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
})
