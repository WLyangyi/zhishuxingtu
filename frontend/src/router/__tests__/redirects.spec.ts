import { beforeEach, describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter, type RouteRecordRaw } from 'vue-router'
import { defineComponent } from 'vue'
import { routes } from '@/router'

/**
 * P0 行为：旧地址必须仍能到达正确页面（书签与外部链接不失效）。
 * 使用与线上同一份路由配置 + 内存历史 + 组件桩，
 * 验证用户实际落点，不加载页面实现，也不检查内部表结构。
 */
const PageStub = defineComponent({ render: () => null })

function withStubbedPages(records: RouteRecordRaw[]): RouteRecordRaw[] {
  return records.map((record) => {
    const stubbed = { ...record } as Record<string, unknown>
    if (stubbed.component) stubbed.component = PageStub
    if (stubbed.children) stubbed.children = withStubbedPages(record.children as RouteRecordRaw[])
    return stubbed as unknown as RouteRecordRaw
  })
}

const testRouter = createRouter({
  history: createMemoryHistory(),
  routes: withStubbedPages(routes)
})

async function navigate(path: string) {
  await testRouter.push(path)
  await testRouter.isReady()
  return testRouter.currentRoute.value
}

describe('信息架构：旧路由可达性', () => {
  beforeEach(async () => {
    await testRouter.replace('/')
  })

  it('旧分类地址重定向到「我的笔记」', async () => {
    expect((await navigate('/categories')).path).toBe('/library')
    expect((await navigate('/categories/cat-1')).path).toBe('/library/cat-1')
  })

  it('旧实验室与可观测地址归入新分组', async () => {
    expect((await navigate('/prompt-lab')).path).toBe('/lab')
    expect((await navigate('/observability')).path).toBe('/ai/observability')
  })

  it('个人区旧别名收敛到主入口', async () => {
    expect((await navigate('/personal/graph')).path).toBe('/graph')
    expect((await navigate('/personal/ai')).path).toBe('/ai')
    expect((await navigate('/personal/search')).path).toBe('/search')
  })

  it('旧工作区与素材区带上区域参数进入「我的笔记」', async () => {
    const work = await navigate('/work')
    expect(work.path).toBe('/library')
    expect(work.query.area).toBe('work')

    const assets = await navigate('/assets')
    expect(assets.path).toBe('/library')
    expect(assets.query.area).toBe('assets')
  })

  it('旧内容编辑地址保留分类与内容标识', async () => {
    const route = await navigate('/categories/cat-1/content/note-9')
    expect(route.path).toBe('/library/cat-1/content/note-9')
    expect(route.params).toMatchObject({ categoryId: 'cat-1', id: 'note-9' })
  })
})
