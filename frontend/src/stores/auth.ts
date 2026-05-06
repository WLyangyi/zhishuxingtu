import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(username: string, password: string) {
    try {
      const response = await authApi.login(username, password)
      token.value = response.access_token
      localStorage.setItem('token', response.access_token)
      await fetchUser()
    } catch (error: any) {
      const message = error?.response?.data?.detail || '登录失败，请检查用户名和密码'
      throw new Error(message)
    }
  }

  async function register(username: string, password: string) {
    try {
      const response = await authApi.register(username, password)
      return response.data
    } catch (error: any) {
      const message = error?.response?.data?.detail || '注册失败，请稍后重试'
      throw new Error(message)
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const response = await authApi.getMe()
      user.value = response.data
    } catch (error) {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout
  }
})
