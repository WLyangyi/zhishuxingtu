import type { AgentSession, TimelineEvent } from '@/api/agent'

/** 会话标题关键词过滤（P2-6）：大小写不敏感、空白规范化。 */
export function filterSessions(sessions: AgentSession[], query: string): AgentSession[] {
  const keyword = query.trim().toLowerCase()
  if (!keyword) return sessions
  return sessions.filter((session) => (session.title || '').toLowerCase().includes(keyword))
}

export interface TraceExport {
  session: { id: string; title: string }
  events: TimelineEvent[]
  meta: { event_count: number; exported_at: string }
}

/** 构造工具轨迹导出对象（P2-6），返回值可直接 JSON.stringify。 */
export function buildTraceExport(
  session: AgentSession | null,
  events: TimelineEvent[]
): TraceExport {
  return {
    session: {
      id: session?.id ?? '',
      title: session?.title || '未命名会话'
    },
    events,
    meta: {
      event_count: events.length,
      exported_at: new Date().toISOString()
    }
  }
}
