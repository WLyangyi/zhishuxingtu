import { reactive } from 'vue'

export type ToastTone = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  title: string
  description?: string
  tone: ToastTone
}

const state = reactive<{ items: ToastItem[] }>({ items: [] })
let seed = 0
const timers = new Map<number, ReturnType<typeof setTimeout>>()

export function dismissToast(id: number) {
  const index = state.items.findIndex((item) => item.id === id)
  if (index >= 0) state.items.splice(index, 1)
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
}

export function showToast(input: {
  title: string
  description?: string
  tone?: ToastTone
  duration?: number
}): number {
  const id = ++seed
  const tone = input.tone ?? 'info'
  state.items.push({ id, title: input.title, description: input.description, tone })

  // 成功/提示 3.5s 自动消隐；错误常驻，需手动关闭
  const duration = input.duration ?? (tone === 'error' ? null : 3500)
  if (duration !== null) {
    timers.set(
      id,
      setTimeout(() => dismissToast(id), duration)
    )
  }
  return id
}

export function useToast() {
  return {
    toasts: state.items,
    show: showToast,
    dismiss: dismissToast,
    success: (title: string, description?: string) =>
      showToast({ title, description, tone: 'success' }),
    error: (title: string, description?: string) =>
      showToast({ title, description, tone: 'error' }),
    info: (title: string, description?: string) =>
      showToast({ title, description, tone: 'info' })
  }
}
