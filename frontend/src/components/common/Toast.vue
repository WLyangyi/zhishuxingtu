<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          :class="['toast', `toast-${notification.type}`]"
          @click="closeNotification(notification.id)"
        >
          <div class="toast-icon">
            <span v-if="notification.type === 'success'">✓</span>
            <span v-else-if="notification.type === 'error'">✕</span>
            <span v-else-if="notification.type === 'warning'">⚠</span>
            <span v-else>ℹ</span>
          </div>
          <div class="toast-content">
            <div class="toast-title">{{ notification.title }}</div>
            <div v-if="notification.message" class="toast-message">
              {{ notification.message }}
            </div>
          </div>
          <button class="toast-close" @click.stop="closeNotification(notification.id)">
            ✕
          </button>
          <div class="toast-progress" :style="{ animationDuration: `${notification.duration}ms` }"></div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useNotificationStore } from '@/stores/notification'

const notificationStore = useNotificationStore()
const notifications = computed(() => notificationStore.notifications)

function closeNotification(id: string) {
  notificationStore.removeNotification(id)
}
</script>

<style scoped lang="scss">
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background-color: var(--card-bg, #1e1e2e);
  border: 1px solid var(--border-color, #313244);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  pointer-events: auto;
  position: relative;
  overflow: hidden;
  min-width: 300px;
  
  &:hover {
    transform: translateX(-4px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  }
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: bold;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: var(--text-color, #cdd6f4);
}

.toast-message {
  font-size: 13px;
  color: var(--text-secondary, #a6adc8);
  line-height: 1.4;
  word-break: break-word;
}

.toast-close {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-secondary, #a6adc8);
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
  
  &:hover {
    color: var(--text-color, #cdd6f4);
  }
}

.toast:hover .toast-close {
  opacity: 1;
}

.toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: currentColor;
  opacity: 0.5;
  animation: progress linear forwards;
}

@keyframes progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

.toast-success {
  border-left: 4px solid #22c55e;
  
  .toast-icon {
    background-color: rgba(34, 197, 94, 0.2);
    color: #22c55e;
  }
  
  .toast-progress {
    background-color: #22c55e;
  }
}

.toast-error {
  border-left: 4px solid #ef4444;
  
  .toast-icon {
    background-color: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }
  
  .toast-progress {
    background-color: #ef4444;
  }
}

.toast-warning {
  border-left: 4px solid #f59e0b;
  
  .toast-icon {
    background-color: rgba(245, 158, 11, 0.2);
    color: #f59e0b;
  }
  
  .toast-progress {
    background-color: #f59e0b;
  }
}

.toast-info {
  border-left: 4px solid #3b82f6;
  
  .toast-icon {
    background-color: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
  }
  
  .toast-progress {
    background-color: #3b82f6;
  }
}

.toast-enter-active {
  animation: toast-in 0.3s ease-out;
}

.toast-leave-active {
  animation: toast-out 0.3s ease-in;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes toast-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}
</style>
