import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MetricCard from '../MetricCard.vue'

describe('MetricCard', () => {
  it('数值按千分位显示并保留单位', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'WORDS', value: 182340, unit: '字' }
    })
    expect(wrapper.text()).toContain('182,340')
    expect(wrapper.text()).toContain('字')
    expect(wrapper.text()).toContain('WORDS')
  })

  it('趋势为正时带加号', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'TRACES', value: 96, trend: 12, trendLabel: '较上周' }
    })
    expect(wrapper.text()).toContain('+12%')
  })

  it('加载时显示骨架而非数值', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'NOTES', value: 128, loading: true }
    })
    expect(wrapper.find('.skeleton').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('128')
  })
})
