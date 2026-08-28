import api from './index'

export interface AgentSession {
  id: string
  title: string
  created_at?: string
  updated_at?: string
}

export interface AgentMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface PendingApproval {
  type: 'approval_required'
  session_id?: string
  tool_call_id?: string
  tool_name?: string
  title?: string
  description?: string
  args?: Record<string, unknown>
  preview?: { title?: string; content?: string; folder_id?: string | null }
}

export interface SessionMessages {
  messages: AgentMessage[]
  pending_approval: PendingApproval | null
}

export interface TimelineEvent {
  id?: string
  type: 'thought' | 'action' | 'observation' | 'check' | 'tool'
  content?: string
  node?: string
  tool_name?: string
  args?: unknown
  result?: unknown
  latency_ms?: number
  status?: string
  created_at?: string
}

export interface AgentTrace {
  id: string
  session_id?: string
  name: string
  timestamp?: string
  latency_ms: number
  total_cost?: number | null
  total_tokens?: number | null
  tool_calls: number
  status: string
  source: 'local' | 'langfuse'
  url?: string | null
}

export interface ObservabilitySummary {
  sessions: number
  tool_calls: number
  avg_tool_latency_ms: number
  success_rate: number
  pending_approvals: number
  rejected_calls: number
  preferences: number
  tool_distribution: Array<{ name: string; count: number }>
  langfuse_configured: boolean
}

export const agentApi = {
  listSessions: async (): Promise<AgentSession[]> => {
    const response = await api.get('/agent/sessions')
    return response.data.data
  },

  createSession: async (title = '新会话'): Promise<AgentSession> => {
    const response = await api.post('/agent/sessions', null, { params: { title } })
    return response.data.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/agent/sessions/${sessionId}`)
  },

  clearSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/agent/sessions/${sessionId}/messages`)
  },

  getMessages: async (sessionId: string): Promise<SessionMessages> => {
    const response = await api.get(`/agent/sessions/${sessionId}/messages`)
    return response.data.data
  },

  getTimeline: async (sessionId: string): Promise<TimelineEvent[]> => {
    const response = await api.get(`/agent/sessions/${sessionId}/timeline`)
    return response.data.data
  },

  getPreferences: async (): Promise<Record<string, string>> => {
    const response = await api.get('/agent/preferences')
    return response.data.data
  },

  putPreference: async (key: string, value: string): Promise<void> => {
    await api.put(`/agent/preferences/${encodeURIComponent(key)}`, { value })
  },

  deletePreference: async (key: string): Promise<void> => {
    await api.delete(`/agent/preferences/${encodeURIComponent(key)}`)
  },

  getTraces: async (source = 'auto', page = 1, limit = 20) => {
    const response = await api.get('/agent/traces', { params: { source, page, limit } })
    return response.data.data as {
      source: 'local' | 'langfuse'
      data: AgentTrace[]
      meta: { page: number; limit: number; total_items: number; total_pages: number }
      fallback_reason?: string
    }
  },

  getObservabilitySummary: async (): Promise<ObservabilitySummary> => {
    const response = await api.get('/agent/observability/summary')
    return response.data.data
  }
}
