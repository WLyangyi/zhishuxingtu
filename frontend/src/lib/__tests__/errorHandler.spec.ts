import { createApp, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installGlobalErrorHandler } from '../errorHandler'
import { useNotificationStore } from '@/stores/notification'

function makeApp() {
  return createApp({ render: () => h('div') })
}

describe('全局错误兜底 errorHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('生产环境结构化记录错误并通知用户', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const app = makeApp()
    installGlobalErrorHandler(app, true)

    const instance = { $options: { name: 'PromptLab' } }
    app.config.errorHandler!(new Error('boom'), instance as never, 'render')

    expect(consoleSpy).toHaveBeenCalledOnce()
    expect(consoleSpy.mock.calls[0][1]).toMatchObject({
      message: 'boom',
      component: 'PromptLab',
      lifecycle: 'render'
    })
    expect(useNotificationStore().notifications[0]).toMatchObject({
      type: 'error',
      title: '页面异常',
      message: '已自动恢复，操作未保存的内容请重试'
    })
  })

  it('开发环境重抛原始错误以便调试', () => {
    const app = makeApp()
    installGlobalErrorHandler(app, false)

    expect(() => app.config.errorHandler!(new Error('dev boom'), null, 'updated')).toThrow('dev boom')
  })
})
