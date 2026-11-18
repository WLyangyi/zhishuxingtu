import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'

// v2「精密星图」样式入口：令牌 → 基础 → 纹理 → 工具类
import '@/styles/tokens.css'
import '@/styles/base.css'
import '@/styles/textures.css'
import '@/styles/utilities.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

// 挂载前先落地主题，避免首帧闪烁
useThemeStore(pinia).init()

app.use(router)
app.mount('#app')
