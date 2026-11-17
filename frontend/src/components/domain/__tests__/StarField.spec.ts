import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import StarField from '../StarField.vue'

describe('StarField', () => {
  it('渲染远中近三层星场画布', () => {
    const wrapper = mount(StarField, { props: { static: true } })
    expect(wrapper.findAll('canvas')).toHaveLength(3)
    expect(wrapper.find('.star-field__layer--near').exists()).toBe(true)
    wrapper.unmount()
  })

  it('静态模式下不启动动画循环', () => {
    const raf = vi.spyOn(window, 'requestAnimationFrame')
    const wrapper = mount(StarField, { props: { static: true, parallax: false } })
    expect(raf).not.toHaveBeenCalled()
    wrapper.unmount()
    raf.mockRestore()
  })

  it('开启视差时监听指针移动', () => {
    const add = vi.spyOn(window, 'addEventListener')
    const wrapper = mount(StarField, { props: { static: false, parallax: true } })
    expect(add.mock.calls.some(([event]) => event === 'pointermove')).toBe(true)
    wrapper.unmount()
    add.mockRestore()
  })
})
