import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ToolTrace from '../ToolTrace.vue'

describe('ToolTrace', () => {
  it('渲染事件标签、延迟与正文', () => {
    const wrapper = mount(ToolTrace, {
      props: {
        events: [
          { type: 'action', tool_name: 'search_notes', content: '检索「Agent」', latency_ms: 42, status: 'success' },
          { type: 'observation', content: '命中 3 篇笔记' }
        ]
      }
    })

    expect(wrapper.text()).toContain('调用 search_notes')
    expect(wrapper.text()).toContain('42ms')
    expect(wrapper.text()).toContain('成功')
    expect(wrapper.text()).toContain('命中 3 篇笔记')
  })

  it('空状态给出提示', () => {
    const wrapper = mount(ToolTrace, { props: { events: [], emptyText: '暂无轨迹' } })
    expect(wrapper.text()).toContain('暂无轨迹')
  })
})
