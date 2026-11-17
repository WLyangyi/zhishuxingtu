import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import ApprovalCard from '../ApprovalCard.vue'

describe('ApprovalCard', () => {
  let wrapper: ReturnType<typeof mount> | null = null

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
  })

  it('按 Y 批准执行', async () => {
    wrapper = mount(ApprovalCard, {
      props: { title: '写入笔记：Agentic RAG', status: 'pending' }
    })
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'y' }))
    await nextTick()
    expect(wrapper.emitted('approve')).toHaveLength(1)
  })

  it('按 N 拒绝执行', async () => {
    wrapper = mount(ApprovalCard, {
      props: { title: '写入笔记：Agentic RAG', status: 'pending' }
    })
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'n' }))
    await nextTick()
    expect(wrapper.emitted('reject')).toHaveLength(1)
  })

  it('在输入框中按 Y 不触发审批', async () => {
    wrapper = mount(ApprovalCard, {
      props: { title: '写入笔记', status: 'pending' },
      attachTo: document.body
    })
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'y', bubbles: true }))
    await nextTick()
    expect(wrapper.emitted('approve')).toBeUndefined()
    input.remove()
  })

  it('已批准后折叠为单行记录', () => {
    wrapper = mount(ApprovalCard, {
      props: { title: '写入笔记', status: 'approved', decidedAt: '23:04' }
    })
    expect(wrapper.text()).toContain('已批准')
    expect(wrapper.text()).toContain('23:04')
    expect(wrapper.text()).not.toContain('批准执行')
  })
})
