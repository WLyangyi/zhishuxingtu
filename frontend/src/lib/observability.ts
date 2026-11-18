/**
 * 可观测面板的读数与分布计算。
 * 纯函数，便于在不启动组件的情况下验证格式化与状态映射。
 */

export type StatusTone = 'success' | 'warning' | 'error' | 'idle'

export interface StatusMeta {
  label: string
  tone: StatusTone
}

const STATUS_MAP: Record<string, StatusMeta> = {
  success: { label: '成功', tone: 'success' },
  pending: { label: '待审批', tone: 'warning' },
  rejected: { label: '已拒绝', tone: 'error' },
  error: { label: '异常', tone: 'error' }
}

export function statusMeta(status?: string): StatusMeta {
  if (!status) return { label: '未知', tone: 'idle' }
  return STATUS_MAP[status] ?? { label: status, tone: 'idle' }
}

export interface ToolShare {
  name: string
  count: number
  pct: number
}

/**
 * 以最大值为 100% 计算条形宽度；最小保留 4%，避免出现看不见的条。
 * 输入保持稳定排序（按次数降序，同次数按名称），不做原地修改。
 */
export function toolShares(items: Array<{ name: string; count: number }>): ToolShare[] {
  if (items.length === 0) return []
  const sorted = [...items].sort((a, b) => b.count - a.count || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
  const max = Math.max(...sorted.map((item) => item.count), 1)
  return sorted.map((item) => ({
    name: item.name,
    count: item.count,
    pct: Math.max(4, Math.round((item.count / max) * 100))
  }))
}

export function formatLatency(value?: number | null): string {
  if (value === null || value === undefined) return '—'
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`
  return `${Math.round(value)} ms`
}

export function formatTokens(value?: number | null): string {
  if (value === null || value === undefined) return '—'
  if (value >= 100000) return `${(value / 1000).toFixed(0)}k`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return String(value)
}

export function formatCost(value?: number | null): string {
  if (value === null || value === undefined) return '—'
  return `$${value.toFixed(4)}`
}
