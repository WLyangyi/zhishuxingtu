import { beforeEach, describe, expect, it, vi } from 'vitest'
import { notesApi } from '../notes'

vi.mock('@/api', () => ({
  default: { get: vi.fn() }
}))

import api from '@/api'

describe('notesApi.getUnlinkedMentions（P2-4 补充）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('请求专用端点并返回解包后的提及数组', async () => {
    const items = [{ id: 'n2', title: 'RAG 混合检索' }]
    vi.mocked(api.get).mockResolvedValue({ data: { data: items } } as never)

    const result = await notesApi.getUnlinkedMentions('n1')

    expect(api.get).toHaveBeenCalledWith('/notes/n1/unlinked-mentions')
    expect(result).toEqual(items)
  })

  it('后端返回空数组时原样返回', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { data: [] } } as never)
    expect(await notesApi.getUnlinkedMentions('n1')).toEqual([])
  })
})
