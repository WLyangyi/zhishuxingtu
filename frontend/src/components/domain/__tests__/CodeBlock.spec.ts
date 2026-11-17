import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CodeBlock from '../CodeBlock.vue'

describe('CodeBlock', () => {
  it('模板变量以金色高亮', () => {
    const wrapper = mount(CodeBlock, {
      props: { code: '请把 {{topic}} 整理成笔记', language: 'PROMPT' }
    })
    const variable = wrapper.find('.code-block__var')
    expect(variable.exists()).toBe(true)
    expect(variable.text()).toBe('{{topic}}')
  })

  it('无变量时整段按普通代码显示', () => {
    const wrapper = mount(CodeBlock, {
      props: { code: 'const total = notes.length', language: 'TS' }
    })
    expect(wrapper.find('.code-block__var').exists()).toBe(false)
    expect(wrapper.text()).toContain('const total = notes.length')
  })
})
