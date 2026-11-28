import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { WebSource } from '@/api/agent'
import SourceCard from '../SourceCard.vue'

const source: WebSource = {
  source_id: 'source-1',
  ordinal: 1,
  title: '页面标题',
  url: 'https://example.com/a',
  site_name: '示例站点',
  retrieved_at: '2026-11-28T09:59:00+00:00',
  fetched_at: '2026-11-28T10:00:00+00:00',
  excerpt: '用于验证的证据摘录',
  content_state: 'fetched',
  artifact_id: 'artifact-1',
  truncated: false,
}

describe('SourceCard', () => {
  it('展示编号、标题、域名、时间和证据摘录', () => {
    const wrapper = mount(SourceCard, { props: { source } })

    expect(wrapper.text()).toContain('[1]')
    expect(wrapper.text()).toContain('页面标题')
    expect(wrapper.text()).toContain('example.com')
    expect(wrapper.text()).toContain(source.retrieved_at)
    expect(wrapper.text()).toContain('用于验证的证据摘录')
  })

  it('使用安全属性打开来源外链', () => {
    const wrapper = mount(SourceCard, { props: { source } })

    const link = wrapper.get('a.source-card__title')
    expect(link.attributes('href')).toBe(source.url)
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toBe('noopener noreferrer')
  })

  it('点击存入知识库发出 save 事件', async () => {
    const wrapper = mount(SourceCard, { props: { source } })

    await wrapper.get('button.source-card__save').trigger('click')

    expect(wrapper.emitted('save')).toEqual([[source]])
  })

  it('loading 状态显示加载提示', () => {
    const wrapper = mount(SourceCard, { props: { source, state: 'loading' } })

    expect(wrapper.text()).toContain('正在加载来源')
    expect(wrapper.find('button.source-card__save').exists()).toBe(false)
  })

  it('empty 状态显示空提示', () => {
    const wrapper = mount(SourceCard, { props: { source, state: 'empty' } })

    expect(wrapper.text()).toContain('暂无来源')
    expect(wrapper.find('button.source-card__save').exists()).toBe(false)
  })

  it('error 状态显示错误信息', () => {
    const wrapper = mount(SourceCard, {
      props: { source, state: 'error', errorMessage: '来源加载失败，请重试' },
    })

    expect(wrapper.get('[role="alert"]').text()).toContain('来源加载失败，请重试')
    expect(wrapper.find('button.source-card__save').exists()).toBe(false)
  })

  it('fetch_failed 状态说明当前只有搜索摘要', () => {
    const wrapper = mount(SourceCard, {
      props: { source: { ...source, content_state: 'fetch_failed' } },
    })

    expect(wrapper.text()).toContain('正文抓取失败，当前为搜索摘要')
  })

  it('summary 状态明确标注仅搜索摘要', () => {
    const wrapper = mount(SourceCard, {
      props: { source: { ...source, content_state: 'summary', fetched_at: null, artifact_id: null } },
    })

    expect(wrapper.text()).toContain('仅搜索摘要')
  })

  it('截断来源明确标注正文已截断', () => {
    const wrapper = mount(SourceCard, {
      props: { source: { ...source, truncated: true } },
    })

    expect(wrapper.text()).toContain('正文已截断')
  })

  it('已抓取但快照缺失时明确标注快照不可用', () => {
    const wrapper = mount(SourceCard, {
      props: { source: { ...source, artifact_id: null } },
    })

    expect(wrapper.text()).toContain('正文快照不可用')
  })

  it('来源字段中的 HTML 只作为文本显示', () => {
    const title = '<img src=x onerror="window.__sourceXss = true">标题'
    const excerpt = '<script>window.__sourceXss = true</script>摘录'
    const url = 'https://example.com/?q="><svg onload="window.__sourceXss = true">'
    const wrapper = mount(SourceCard, {
      props: { source: { ...source, title, excerpt, url } },
    })

    expect(wrapper.text()).toContain(title)
    expect(wrapper.text()).toContain(excerpt)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('svg').exists()).toBe(false)
    expect(wrapper.find('a').attributes('href')).toBe(url)
    expect(window).not.toHaveProperty('__sourceXss')
  })

  it('非 HTTP(S) 地址不渲染可点击外链', () => {
    const wrapper = mount(SourceCard, {
      props: { source: { ...source, title: '', url: 'javascript:alert(1)' } },
    })

    expect(wrapper.find('a.source-card__title-link').exists()).toBe(false)
    expect(wrapper.text()).toContain('javascript:alert(1)')
  })

  it('保存按钮与来源外链互不嵌套', () => {
    const wrapper = mount(SourceCard, { props: { source } })

    expect(wrapper.find('a button').exists()).toBe(false)
    expect(wrapper.find('button a').exists()).toBe(false)
  })
})
