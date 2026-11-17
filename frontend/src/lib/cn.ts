/** 轻量 className 组合，避免为一个小工具引入额外依赖 */
export type ClassValue = string | number | false | null | undefined

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
