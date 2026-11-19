import type { App } from 'vue'
import { useNotificationStore } from '@/stores/notification'

/**
 * 全局错误兜底：拦截 Teleport（portal 内容不在组件树内，ErrorBoundary 捕不到）
 * 等游离于组件树之外的 Vue 渲染错误。
 *
 * - 开发环境直接重抛，保留浏览器控制台的原始调用栈
 * - 生产环境结构化记录（组件名 + 生命周期钩子），并走唯一通知渠道提示用户
 */
export function installGlobalErrorHandler(app: App, isProduction: boolean): void {
  app.config.errorHandler = (err, instance, info) => {
    if (!isProduction) throw err

    const error = err instanceof Error ? err : new Error(String(err))
    const options = instance?.$options as { name?: string } | undefined
    console.error('[app error]', {
      message: error.message,
      component: options?.name ?? 'unknown',
      lifecycle: info,
      stack: error.stack
    })
    useNotificationStore().error('页面异常', '已自动恢复，操作未保存的内容请重试')
  }
}
