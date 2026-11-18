import { describe, expect, it } from 'vitest'
import {
  formatCost,
  formatLatency,
  formatTokens,
  statusMeta,
  toolShares
} from '../observability'

describe('statusMeta', () => {
  it('maps known statuses to label and tone', () => {
    expect(statusMeta('success')).toEqual({ label: '成功', tone: 'success' })
    expect(statusMeta('pending')).toEqual({ label: '待审批', tone: 'warning' })
    expect(statusMeta('rejected')).toEqual({ label: '已拒绝', tone: 'error' })
    expect(statusMeta('error')).toEqual({ label: '异常', tone: 'error' })
  })

  it('falls back to raw label with neutral tone for unknown status', () => {
    expect(statusMeta('running')).toEqual({ label: 'running', tone: 'idle' })
    expect(statusMeta(undefined)).toEqual({ label: '未知', tone: 'idle' })
  })
})

describe('toolShares', () => {
  it('computes percentages against the largest count', () => {
    const shares = toolShares([
      { name: 'search', count: 8 },
      { name: 'create_note', count: 2 }
    ])
    expect(shares[0]).toMatchObject({ name: 'search', count: 8, pct: 100 })
    expect(shares[1].pct).toBe(25)
  })

  it('keeps a visible minimum width and sorts descending', () => {
    const shares = toolShares([
      { name: 'a', count: 1 },
      { name: 'b', count: 40 }
    ])
    expect(shares[0].name).toBe('b')
    expect(shares[1].pct).toBeGreaterThanOrEqual(4)
  })

  it('returns empty array for empty input without dividing by zero', () => {
    expect(toolShares([])).toEqual([])
  })
})

describe('formatters', () => {
  it('formats latency in ms below one second and seconds above', () => {
    expect(formatLatency(820)).toBe('820 ms')
    expect(formatLatency(2450)).toBe('2.45 s')
    expect(formatLatency(0)).toBe('0 ms')
  })

  it('formats small token counts plainly and large ones compactly', () => {
    expect(formatTokens(980)).toBe('980')
    expect(formatTokens(10422)).toBe('10.4k')
    expect(formatTokens(null)).toBe('—')
  })

  it('formats cost with four decimals and dashes for null', () => {
    expect(formatCost(0.0213)).toBe('$0.0213')
    expect(formatCost(null)).toBe('—')
  })
})
