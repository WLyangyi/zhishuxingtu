import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'
import { installGlobalErrorHandler } from '@/lib/errorHandler'

// v2「精密星图」样式入口：令牌 → 基础 → 纹理 → 工具类
import '@/styles/tokens.css'
import '@/styles/base.css'
import '@/styles/textures.css'
import '@/styles/utilities.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

// 兜底组件树之外的渲染错误（Reka UI 的 Teleport 内容等）
installGlobalErrorHandler(app, import.meta.env.PROD)

// 挂载前先落地主题，避免首帧闪烁
useThemeStore(pinia).init()

app.use(router)
app.mount('#app')
