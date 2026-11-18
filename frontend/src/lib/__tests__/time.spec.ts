import { describe, expect, it } from 'vitest'
import { parseServerTime, relativeTime } from '../time'

const NOW = new Date('2026-11-18T04:00:00Z').getTime()

describe('时间格式化', () => {
  it('无时区的后端时间按 UTC 解析', () => {
    expect(parseServerTime('2026-11-18T03:30:00').toISOString()).toBe(
      '2026-11-18T03:30:00.000Z'
    )
  })

  it('带时区的时间不重复补 Z', () => {
    expect(parseServerTime('2026-11-18T03:30:00Z').toISOString()).toBe(
      '2026-11-18T03:30:00.000Z'
    )
  })

  it('按分钟/小时/天分级', () => {
    expect(relativeTime('2026-11-18T03:59:30', NOW)).toBe('刚刚')
    expect(relativeTime('2026-11-18T03:30:00', NOW)).toBe('30 分钟前')
    expect(relativeTime('2026-11-18T01:00:00', NOW)).toBe('3 小时前')
    expect(relativeTime('2026-11-16T04:00:00', NOW)).toBe('2 天前')
  })

  it('超过 7 天回落到日期', () => {
    expect(relativeTime('2026-10-27T09:47:27', NOW)).toContain('10/27')
  })
})
