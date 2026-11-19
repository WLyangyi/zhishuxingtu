import { beforeEach, describe, expect, it, vi } from 'vitest'
import { agentApi } from '../agent'

vi.mock('@/api', () => ({
  default: { get: vi.fn() }
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
