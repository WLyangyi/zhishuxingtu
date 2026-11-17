import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'dark' | 'light'

/**
 * 主题：暗色优先（设计文档 P1）。
 * 主题真相写入 <html data-theme="dark|light">，CSS 令牌据此切换；
 * body.dark / body.light 仅用于兼容尚未翻新的旧页面样式，P6 删除。
 */
export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(true)

  function init() {
    const savedTheme = localStorage.getItem('theme')
    isDark.value = savedTheme ? savedTheme === 'dark' : true
    applyTheme()
  }

  function applyTheme() {
    const mode: ThemeMode = isDark.value ? 'dark' : 'light'
    document.documentElement.dataset.theme = mode
    document.body.classList.toggle('dark', isDark.value)
    document.body.classList.toggle('light', !isDark.value)
    document.body.style.colorScheme = mode
  }

  function setTheme(dark: boolean) {
    isDark.value = dark
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }

  function toggle() {
    setTheme(!isDark.value)
  }

  watch(isDark, () => {
    applyTheme()
  })

  return {
    isDark,
    init,
    setTheme,
    toggle
  }
})
