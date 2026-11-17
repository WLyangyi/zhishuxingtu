import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SegmentedControl from '../SegmentedControl.vue'

const items = [
  { label: '网格', value: 'grid' },
  { label: '列表', value: 'list' }
]

describe('SegmentedControl', () => {
  it('点击片段切换视图', async () => {
    const wrapper = mount(SegmentedControl, { props: { items, modelValue: 'grid' } })
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['list'])
  })

  it('方向键在片段间移动并选中', async () => {
    const wrapper = mount(SegmentedControl, { props: { items, modelValue: 'grid' } })
    await wrapper.findAll('button')[0].trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['list'])
  })

  it('当前项带 aria-checked 标记', () => {
    const wrapper = mount(SegmentedControl, { props: { items, modelValue: 'list' } })
    const buttons = wrapper.findAll('button')
    expect(buttons[0].attributes('aria-checked')).toBe('false')
    expect(buttons[1].attributes('aria-checked')).toBe('true')
  })
})
