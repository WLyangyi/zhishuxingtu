import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration: number
  createdAt: number
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])
  const maxNotifications = 5

  function generateId(): string {
    return `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  function addNotification(
    type: Notification['type'],
    title: string,
    message?: string,
    duration: number = 3000
  ): string {
    const id = generateId()
    const notification: Notification = {
      id,
      type,
      title,
      message,
      duration,
      createdAt: Date.now()
    }

    notifications.value.push(notification)

    if (notifications.value.length > maxNotifications) {
      notifications.value.shift()
    }

    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, duration)
    }

    return id
  }

  function removeNotification(id: string) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function clearAll() {
    notifications.value = []
  }

  function success(title: string, message?: string, duration?: number): string {
    return addNotification('success', title, message, duration)
  }

  function error(title: string, message?: string, duration?: number): string {
    return addNotification('error', title, message, duration ?? 5000)
  }

  function warning(title: string, message?: string, duration?: number): string {
    return addNotification('warning', title, message, duration)
  }

  function info(title: string, message?: string, duration?: number): string {
    return addNotification('info', title, message, duration)
  }

  return {
    notifications,
    addNotification,
    removeNotification,
    clearAll,
    success,
    error,
    warning,
    info
  }
})
