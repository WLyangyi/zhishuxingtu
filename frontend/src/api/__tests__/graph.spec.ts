import { beforeEach, describe, expect, it, vi } from 'vitest'
import { graphApi } from '../graph'

vi.mock('@/api', () => ({
  default: { get: vi.fn() }
}))

import api from '@/api'

const payload = { success: true, message: 'ok', data: { nodes: [], edges: [] } }

describe('graphApi ETag', () => {
  beforeEach(() => vi.clearAllMocks())

  it('200 响应带出 ETag', async () => {
    vi.mocked(api.get).mockResolvedValue({
      status: 200,
      headers: { etag: 'snapshot-1' },
      data: payload
    } as never)

    const result = await graphApi.getGlobal()

    expect(result.notModified).toBe(false)
    expect(result.etag).toBe('snapshot-1')
    expect(result.response).toBe(payload)
  })

  it('304 响应不返回数据并保留 ETag', async () => {
    vi.mocked(api.get).mockResolvedValue({
      status: 304,
      headers: {},
      data: ''
    } as never)

    const result = await graphApi.getGlobal('snapshot-1')

    expect(result.notModified).toBe(true)
    expect(result.response).toBeNull()
    expect(result.etag).toBe('snapshot-1')
    expect(api.get).toHaveBeenCalledWith('/graph/global', expect.objectContaining({
      headers: { 'If-None-Match': 'snapshot-1' }
    }))
  })
})
