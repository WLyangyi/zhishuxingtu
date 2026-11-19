import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { graphApi } from '@/api/graph'
import { useGraphStore } from '../graph'
import type { GraphData } from '@/types/graph'

vi.mock('@/api/graph', () => ({
  graphApi: {
    getGlobal: vi.fn()
  }
}))

const node = (id: string, label: string) => ({
  id,
  label,
  type: 'note' as const,
  color: '#8fa3b8',
  size: 18
})
const dataA: GraphData = { nodes: [node('n1', '一')], edges: [] }
const dataB: GraphData = { nodes: [node('n1', '一'), node('n2', '二')], edges: [] }

function result(data: GraphData | null, etag: string, notModified = false) {
  return Promise.resolve({
    response: data ? { success: true, message: 'ok', data } : null,
    etag,
    notModified
  })
}

describe('graphStore 缓存与静默刷新', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('首次加载请求网络并缓存数据与 ETag', async () => {
    vi.mocked(graphApi.getGlobal).mockReturnValue(result(dataA, 'etag-a'))
    const store = useGraphStore()

    const loaded = await store.load()

    expect(loaded).toBe(dataA)
    expect(store.data).toBe(dataA)
    expect(store.etag).toBe('etag-a')
    expect(graphApi.getGlobal).toHaveBeenCalledWith(undefined)
  })

  it('二次加载先用缓存返回，后台带 ETag 静默刷新', async () => {
    vi.mocked(graphApi.getGlobal)
      .mockReturnValueOnce(result(dataA, 'etag-a'))
      .mockReturnValueOnce(result(null, 'etag-a', true))
    const store = useGraphStore()
    await store.load()

    const cached = await store.load()
    expect(cached).toBe(dataA)
    expect(graphApi.getGlobal).toHaveBeenLastCalledWith('etag-a')

    await vi.waitFor(() => expect(graphApi.getGlobal).toHaveBeenCalledTimes(2))
    expect(store.data).toBe(dataA) // 304 不替换数据引用，避免重算布局
  })

  it('后台刷新拿到新数据时更新缓存与 ETag', async () => {
    vi.mocked(graphApi.getGlobal)
      .mockReturnValueOnce(result(dataA, 'etag-a'))
      .mockReturnValueOnce(result(dataB, 'etag-b'))
    const store = useGraphStore()
    await store.load()

    await store.load()
    await vi.waitFor(() => expect(store.data).toBe(dataB))
    expect(store.etag).toBe('etag-b')
  })

  it('强制刷新始终重新请求网络', async () => {
    vi.mocked(graphApi.getGlobal)
      .mockReturnValueOnce(result(dataA, 'etag-a'))
      .mockReturnValueOnce(result(dataB, 'etag-b'))
    const store = useGraphStore()
    await store.load()

    const loaded = await store.load(true)

    expect(loaded).toBe(dataB)
    expect(graphApi.getGlobal).toHaveBeenLastCalledWith(undefined)
  })
})
