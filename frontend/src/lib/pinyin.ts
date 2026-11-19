/**
 * 命令面板拼音匹配（P2-5 补充）：全拼 / 首字母 / 原样子串。
 * 基于 tiny-pinyin（~42KB，无多音字支持但对命令/标题词足够）。
 */
import pinyin from 'tiny-pinyin'

const HANZI = /[\u4e00-\u9fff]/

function isSupported(): boolean {
  try {
    return pinyin.isSupported()
  } catch {
    return false
  }
}

function convertChar(char: string): string {
  if (!HANZI.test(char)) return char
  try {
    return pinyin.convertToPinyin(char, '', true) || char
  } catch {
    return char
  }
}

/** 把文本转成匹配用的两种形式：full=全拼连写（非中文原样），initials=每段首字符串。 */
export function toPinyinForms(text: string): { full: string; initials: string } {
  let full = ''
  let initials = ''

  for (const char of text) {
    if (HANZI.test(char)) {
      const py = convertChar(char)
      full += py
      if (py) initials += py[0] // 中文取拼音首字母
    } else if (/[a-zA-Z0-9]/.test(char)) {
      full += char
      initials += char.toLowerCase() // 英文/数字取自身，便于 "agent" 连续匹配
    } else {
      full += char // 空白/标点在 full 中保留原样，initials 中跳过
    }
  }

  return { full: full.toLowerCase(), initials: initials.toLowerCase() }
}

/** 命令匹配：原样子串（大小写不敏感）或拼音全拼/首字母命中。 */
export function matchesCommand(label: string, hint: string | undefined, keyword: string): boolean {
  const kw = keyword.trim().toLowerCase()
  if (!kw) return true

  for (const field of [label, hint ?? '']) {
    if (!field) continue
    const lower = field.toLowerCase()
    if (lower.includes(kw)) return true
    if (!isSupported()) continue
    const { full, initials } = toPinyinForms(field)
    if (full.includes(kw) || initials.includes(kw)) return true
  }
  return false
}
