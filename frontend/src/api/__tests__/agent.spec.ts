import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'
import { agentApi } from '../agent'
import type { AgentMessage, WebSource } from '../agent'
import type { SSEMessage } from '@/utils/sse'

vi.mock('@/api', () => ({
  default: { get: vi.fn(), post: vi.fn() }
}))

import api from '@/api'

describe('agentApi.listSessions（P2-6）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('无关键词时不带 params', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { data: [] } } as never)
    await agentApi.listSessions()
    expect(api.get).toHaveBeenCalledWith('/agent/sessions', undefined)
  })

  it('带关键词时把 q 作为查询参数传给后端', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { data: [] } } as never)
    await agentApi.listSessions('周报')
    expect(api.get).toHaveBeenCalledWith('/agent/sessions', { params: { q: '周报' } })
  })

  it('返回后端解包后的会话数组', async () => {
    const sessions = [{ id: 's1', title: '会话一' }]
    vi.mocked(api.get).mockResolvedValue({ data: { data: sessions } } as never)
    const result = await agentApi.listSessions()
    expect(result).toEqual(sessions)
  })
})

describe('agentApi.saveSource（联网来源入库）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('向会话来源保存端点发送 POST 并返回笔记', async () => {
    const note = { id: 'n1', title: '页面标题', folder_id: null }
    vi.mocked(api.post).mockResolvedValue({ data: { data: note } } as never)

    const result = await agentApi.saveSource('s1', 'source-1')

    expect(api.post).toHaveBeenCalledWith('/agent/sessions/s1/sources/source-1/save')
    expect(result).toEqual(note)
  })

  it('历史消息与 SSE 使用同一来源契约', () => {
    expectTypeOf<AgentMessage['sources']>().toEqualTypeOf<WebSource[] | undefined>()
    expectTypeOf<SSEMessage['sources']>().toEqualTypeOf<WebSource[] | undefined>()
  })
})

describe('agentApi.getVisualEvidenceImage（原图核验）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('按受保护端点获取 PNG Blob', async () => {
    const blob = new Blob(['png'], { type: 'image/png' })
    vi.mocked(api.get).mockResolvedValue({ data: blob } as never)

    const result = await agentApi.getVisualEvidenceImage('n1', 'asset-1')

    expect(api.get).toHaveBeenCalledWith('/import/notes/n1/assets/asset-1/image', { responseType: 'blob' })
    expect(result).toBe(blob)
  })
})
