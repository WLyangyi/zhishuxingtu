import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick, type Component } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import ErrorBoundary from '../ErrorBoundary.vue'

const Boom = defineComponent({
  setup() {
    throw new Error('render boom')
  },
  template: '<div>不应出现</div>'
})

function mountWithBoom(slotComponent: Component = Boom) {
  const onGlobalError = vi.fn()
  const wrapper = mount(ErrorBoundary, {
    slots: { default: () => h(slotComponent) },
    global: {
      config: {
        errorHandler: onGlobalError
      }
    }
  })
  return { wrapper, onGlobalError }
}

describe('ErrorBoundary 局部错误兜底', () => {
  it('子树渲染抛错时显示兜底卡片，异常不逃逸到全局', async () => {
    const { wrapper, onGlobalError } = mountWithBoom()
    await nextTick()

    expect(wrapper.text()).toContain('此区域加载失败')
    expect(wrapper.text()).not.toContain('不应出现')
    expect(onGlobalError).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('点击重试后重新渲染子树，成功时恢复正常内容', async () => {
    let attempts = 0
    const Flaky = defineComponent({
      setup() {
        attempts += 1
        if (attempts === 1) throw new Error('first render boom')
      },
      template: '<div>恢复正常</div>'
    })

    const { wrapper, onGlobalError } = mountWithBoom(Flaky)
    await nextTick()
    expect(wrapper.text()).toContain('此区域加载失败')

    const retry = wrapper.findAll('button').find(b => b.text().includes('重试'))
    expect(retry).toBeDefined()
    await retry!.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('恢复正常')
    expect(onGlobalError).not.toHaveBeenCalled()

    wrapper.unmount()
  })
})
