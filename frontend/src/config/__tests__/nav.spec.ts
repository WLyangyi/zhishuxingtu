import { describe, expect, it } from 'vitest'
import { LAB_NAV, PRIMARY_NAV, pageMetaOf } from '../nav'

describe('信息架构配置', () => {
  it('每个主入口都有页面标题与语境词', () => {
    expect(pageMetaOf('Home')).toMatchObject({ title: '观测台', kicker: 'OBSERVATORY' })
    expect(pageMetaOf('Library')).toMatchObject({ title: '我的笔记', kicker: 'LIBRARY' })
    expect(pageMetaOf('Graph')).toMatchObject({ title: '关系图谱', kicker: 'STAR ATLAS' })
    expect(pageMetaOf('AIAssistant')).toMatchObject({ title: 'AI 助手', kicker: 'OBSERVER' })
    expect(pageMetaOf('AgentObservability')).toMatchObject({ title: '可观测面板' })
  })

  it('未知路由回落到品牌页头', () => {
    expect(pageMetaOf('NotExists').title).toBe('知枢星图')
    expect(pageMetaOf(undefined).kicker).toBe('STAR ATLAS')
  })

  it('导航路径唯一且都以斜杠开头', () => {
    const paths = [...PRIMARY_NAV, ...LAB_NAV].map((item) => item.to)
    expect(new Set(paths).size).toBe(paths.length)
    expect(paths.every((path) => path.startsWith('/'))).toBe(true)
  })
})
