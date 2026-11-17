import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MessageBubble from '../MessageBubble.vue'

describe('MessageBubble', () => {
  it('AI 消息直接排版，不使用气泡', () => {
    const wrapper = mount(MessageBubble, {
      props: { role: 'assistant', name: '观测员' },
      slots: { default: '这是检索到的结论。' }
    })
    expect(wrapper.classes()).toContain('message--assistant')
    expect(wrapper.text()).toContain('观测员')
    expect(wrapper.text()).toContain('这是检索到的结论。')
  })

  it('用户消息靠右显示', () => {
    const wrapper = mount(MessageBubble, {
      props: { role: 'user' },
      slots: { default: '帮我整理今天的笔记。' }
    })
    expect(wrapper.classes()).toContain('message--user')
  })

  it('流式输出时显示金色光标', () => {
    const wrapper = mount(MessageBubble, {
      props: { role: 'assistant', streaming: true },
      slots: { default: '正在生成' }
    })
    expect(wrapper.find('.message__cursor').exists()).toBe(true)
  })
})
