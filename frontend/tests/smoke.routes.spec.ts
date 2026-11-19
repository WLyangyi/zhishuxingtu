import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, type RouteRecordRaw } from 'vue-router'
import { defineComponent, h, type Component } from 'vue'
import { RouterView } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'
import { routes } from '@/router'

// 系统边界（HTTP）统一打桩：任何 API 都返回符合 Response 包装的空集合，
// 让视图走真实的数据加载与渲染路径，而不是 mock 掉内部协作者。
vi.mock('@/api', () => {
  const note = {
    id: 'note-1',
    title: '示例笔记',
    content: '正文',
    folder_id: null,
    category_id: null,
    tags: [],
    linked_note_ids: [],
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-02T00:00:00'
  }

  // 仓库里两种解包约定并存：部分 api 返回 response.data，部分返回 response.data.data。
  // 因此 payload 同时带 data 字段与顶层集合字段，且 data 本身是可迭代空数组。
  function typedData(url: string): unknown {
    if (/\/notes\/[^/]+\/backlinks$/.test(url)) return []
    if (/\/notes\/[^/]+$/.test(url)) return note
    if (url.includes('/preferences')) return {}
    if (url.includes('/agent/traces')) {
      return {
        data: [],
        meta: { page: 1, limit: 20, total_items: 0, total_pages: 0 },
        source: 'local',
        fallback_reason: ''
      }
    }
    if (/\/agent\/sessions\/[^/]+\/messages$/.test(url)) {
      return { messages: [], pending_approval: null }
    }
    if (url.includes('/observability/summary')) {
      return { pending_approvals: 0, preferences: 0, sessions: 0, tool_calls: 0 }
    }
    if (url.includes('/overview')) {
      return {
        stats: { notes: 0, tags: 0, links: 0, folders: 0 },
        recent_notes: [],
        recent_reads: [],
        top_tags: [],
        areas: []
      }
    }
    if (url.includes('/observability') || url.includes('/metrics')) {
      return { total_items: 0, items: [], runs: [], total: 0 }
    }
    const list: unknown[] = []
    Object.assign(list, {
      items: [],
      total: 0,
      total_items: 0,
      sessions: [],
      runs: [],
      executions: [],
      templates: [],
      prompts: []
    })
    return list
  }

  const respond = (method: string, _url: string) => {
    const url = String(_url)
    const data = method === 'post' && /\/agent\/sessions$/.test(url)
      ? { id: 'session-1', title: '新会话' }
      : typedData(url)
    const payload: Record<string, unknown> = {
      code: 0,
      message: 'ok',
      data,
      items: [],
      total: 0,
      total_items: 0,
      stats: { notes: 0, tags: 0, links: 0, folders: 0 },
      areas: [],
      recent_notes: [],
      recent_reads: [],
      top_tags: [],
      user: { id: 'u1', username: 'tester' }
    }
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      for (const [key, value] of Object.entries(data)) {
        if (key !== 'data') payload[key] = value
      }
    }
    return Promise.resolve({ data: payload })
  }
  const methodRespond = (method: string) => (url: string) => respond(method, url)
  const api = Object.assign(() => Promise.resolve({ data: {} }), {
    get: methodRespond('get'),
    post: methodRespond('post'),
    put: methodRespond('put'),
    patch: methodRespond('patch'),
    delete: methodRespond('delete'),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  })
  return { default: api }
})

interface ViewRoute {
  name: string
  path: string
  routePath: string
  load: () => Promise<Component>
}

/** 从真实路由表提取具名视图（跳过重定向与无 name 的布局壳） */
function collectViewRoutes(): ViewRoute[] {
  const result: ViewRoute[] = []
  for (const record of routes) {
    const candidates = record.children?.length ? record.children : [record]
    for (const child of candidates) {
      if (!child.name || typeof child.component !== 'function') continue
      const fullPath = record.children?.length
        ? `${record.path.replace(/\/$/, '')}/${child.path}`.replace(/\/+/g, '/')
        : child.path
      result.push({
        name: String(child.name),
        path: fullPath.replace(/:([^/]+)/g, 'sample'),
        routePath: fullPath,
        load: child.component as () => Promise<Component>
      })
    }
  }
  return result
}

const allViewRoutes = collectViewRoutes()
const Host = defineComponent({ render: () => h(RouterView) })

async function mountView(target: { name: string; path: string; routePath: string }, component: Component) {
  setActivePinia(createPinia())
  // 注册全部路由，视图内部的 router.push（Home 快捷入口等）不会触发 No match 噪声；
  // 当前被测路由挂真实组件，其余用空壳占位。
  const routesForTest = allViewRoutes.map((route) => ({
    path: route.routePath,
    name: route.name,
    component: route.name === target.name ? component : { template: '<div />' }
  }))
  if (!routesForTest.some(route => route.name === target.name)) {
    routesForTest.push({ path: target.routePath, name: target.name, component })
  }
  const router = createRouter({ history: createMemoryHistory(), routes: routesForTest })
  await router.push(target.path)
  await router.isReady()

  const errors: unknown[] = []
  let wrapper: ReturnType<typeof mount> | null = null
  try {
    wrapper = mount(Host, {
      global: {
        plugins: [router],
        config: {
          errorHandler(err: unknown) {
            errors.push(err)
          }
        }
      }
    })
    await flushPromises()
  } catch (err) {
    // 根组件自身抛错时 Vue 会直接向外抛，而不是走 app.config.errorHandler
    errors.push(err)
  }
  return { wrapper, errors }
}

describe('全路由挂载冒烟测试', () => {
  for (const target of allViewRoutes) {
    it(`${target.name}（${target.path}）挂载不抛未捕获异常`, async () => {
      const module = (await target.load()) as { default?: Component } & Component
      const { wrapper, errors } = await mountView(target, module.default ?? module)

      expect(errors.map(err => err instanceof Error ? err.stack : String(err))).toEqual([])
      expect(wrapper).not.toBeNull()
      expect(wrapper!.find('div').exists()).toBe(true)
      expect(wrapper!.html().length).toBeGreaterThan(0)

      wrapper!.unmount()
    })
  }

  it('门禁自身有效：注入渲染异常的路由会被捕获', async () => {
    const Boom = defineComponent({
      setup() {
        throw new Error('smoke boom')
      },
      template: '<div />'
    })

    const { errors, wrapper } = await mountView(
      { name: 'SyntheticBoom', path: '/smoke-boom', routePath: '/smoke-boom' },
      Boom
    )
    expect(errors.map(String)).toContain('Error: smoke boom')
    wrapper?.unmount()
  })
})
