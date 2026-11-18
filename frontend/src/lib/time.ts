/** 后端返回的是无时区的 UTC 字符串，浏览器会按本地时间解析，这里统一补 Z。 */
export function parseServerTime(value: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`)
}

export function relativeTime(value: string, now = Date.now()): string {
  const time = parseServerTime(value).getTime()
  if (Number.isNaN(time)) return ''

  const diff = now - time
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`

  const date = parseServerTime(value)
  const sameYear = date.getFullYear() === new Date(now).getFullYear()
  return date.toLocaleDateString('zh-CN', {
    year: sameYear ? undefined : 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
