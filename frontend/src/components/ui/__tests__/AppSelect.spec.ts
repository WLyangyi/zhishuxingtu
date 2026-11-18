import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppSelect from '../AppSelect.vue'

describe('AppSelect 空值防御（P6 修复回归保护）', () => {
  it('options 中 value 为空字符串的项被跳过，组件渲染不抛异常', async () => {
    // Reka UI 的 SelectItem 禁止空字符串 value（空串被保留给 placeholder 清空语义），
    // 直接传入会让渲染树抛异常并冻结整个页面。AppSelect 必须在组件层兜底过滤。
    const errors: unknown[] = []
    const wrapper = mount(AppSelect, {
      props: {
        modelValue: 'a',
        label: '测试',
        options: [
          { label: '全部', value: '' },
          { label: '选项A', value: 'a' },
          { label: '选项B', value: 'b' }
        ]
      },
      global: {
        config: {
          errorHandler(err: unknown) {
            errors.push(err)
          }
        }
      }
    })
    await flushPromises()

    expect(errors).toHaveLength(0)
    // 触发器仍正常渲染
    expect(wrapper.find('.select-trigger').exists()).toBe(true)

    wrapper.unmount()
  })
})
