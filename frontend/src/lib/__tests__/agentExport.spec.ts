import { describe, expect, it } from 'vitest'
import { buildTraceExport, filterSessions } from '../agentExport'
import type { AgentSession, TimelineEvent } from '@/api/agent'

const sessions: AgentSession[] = [
  { id: 's1', title: '周报生成讨论', updated_at: '2026-01-02' },
  { id: 's2', title: 'RAG 检索调优', updated_at: '2026-01-03' },
  { id: 's3', title: '另一个周报', updated_at: '2026-01-01' }
]

const timeline: TimelineEvent[] = [
  { id: 'e1', type: 'thought', content: '先检索', created_at: '2026-01-02T00:00:00' },
  { id: 'e2', type: 'tool', tool_name: 'search', args: { q: 'RAG' }, result: '命中 3 篇', latency_ms: 120 }
]

describe('会话搜索（P2-6）', () => {
  it('行为1 · 关键词按标题过滤，大小写不敏感、空白规范化', () => {
    expect(filterSessions(sessions, '周报').map((s) => s.id)).toEqual(['s1', 's3'])
    expect(filterSessions(sessions, '  rag  ').map((s) => s.id)).toEqual(['s2'])
  })

  it('行为2 · 空关键词返回全部；无匹配返回空', () => {
    expect(filterSessions(sessions, '')).toEqual(sessions)
    expect(filterSessions(sessions, '不存在的会话')).toEqual([])
  })

  it('行为3 · 标题为空的会话在未过滤时保留、过滤时排除', () => {
    const withEmpty: AgentSession[] = [{ id: 's0', title: '' }, ...sessions]
    expect(filterSessions(withEmpty, '')).toHaveLength(4)
    expect(filterSessions(withEmpty, '周报').map((s) => s.id)).toEqual(['s1', 's3'])
  })
})

describe('工具轨迹导出（P2-6）', () => {
  it('行为4 · 导出对象含会话元信息、事件数组与元数据', () => {
    const exported = buildTraceExport(sessions[0], timeline)
    expect(exported.session.id).toBe('s1')
    expect(exported.session.title).toBe('周报生成讨论')
    expect(exported.events).toEqual(timeline)
    expect(exported.meta.event_count).toBe(2)
    expect(exported.meta.exported_at).toBeTruthy()
  })

  it('行为5 · 导出对象可被 JSON.stringify 无损序列化', () => {
    const exported = buildTraceExport(sessions[1], timeline)
    const round = JSON.parse(JSON.stringify(exported))
    expect(round.events[1].tool_name).toBe('search')
    expect(round.events[1].args).toEqual({ q: 'RAG' })
  })

  it('行为6 · 空会话用占位标题，不抛错', () => {
    const exported = buildTraceExport(null, [])
    expect(exported.session.title).toBe('未命名会话')
    expect(exported.events).toEqual([])
    expect(exported.meta.event_count).toBe(0)
  })
})
