import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppInput from '../AppInput.vue'

describe('AppInput', () => {
  it('输入时发出 update:modelValue', async () => {
    const wrapper = mount(AppInput, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('精密星图')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['精密星图'])
  })

  it('错误态带 aria-invalid 并显示错误文案', () => {
    const wrapper = mount(AppInput, {
      props: { modelValue: '', invalid: true, error: '标题不能为空' }
    })

    expect(wrapper.find('input').attributes('aria-invalid')).toBe('true')
    expect(wrapper.text()).toContain('标题不能为空')
  })

  it('禁用时不可输入', async () => {
    const wrapper = mount(AppInput, { props: { modelValue: '只读', disabled: true } })
    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
  })
})
