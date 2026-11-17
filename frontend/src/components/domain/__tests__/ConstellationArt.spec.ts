import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ConstellationArt from '../ConstellationArt.vue'

describe('ConstellationArt', () => {
  it('按预设绘制连线、星点与 ZS 编号', () => {
    const wrapper = mount(ConstellationArt, { props: { variant: 'hero' } })
    expect(wrapper.findAll('path')).toHaveLength(7)
    expect(wrapper.findAll('circle').length).toBeGreaterThanOrEqual(7)
    expect(wrapper.text()).toContain('ZS·128')
  })

  it('支持自定义星点与编号', () => {
    const wrapper = mount(ConstellationArt, {
      props: {
        points: [
          { x: 10, y: 10, r: 2 },
          { x: 40, y: 30, r: 2, gold: true }
        ],
        links: [[0, 1]],
        code: 'ZS·001'
      }
    })
    expect(wrapper.findAll('path')).toHaveLength(1)
    expect(wrapper.text()).toContain('ZS·001')
  })
})
