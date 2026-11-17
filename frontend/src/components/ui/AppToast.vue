<template>
  <Teleport to="body">
    <div class="toast-viewport" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast">
        <article
          v-for="item in toasts"
          :key="item.id"
          class="toast"
          :class="`toast--${item.tone}`"
          role="status"
        >
          <div class="toast__content">
            <p class="toast__title">{{ item.title }}</p>
            <p v-if="item.description" class="toast__description">{{ item.description }}</p>
          </div>
          <button class="toast__close" type="button" aria-label="关闭提示" @click="dismiss(item.id)">
            ×
          </button>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/lib/toast'

const { toasts, dismiss } = useToast()
</script>

<style scoped>
.toast-viewport {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: min(360px, calc(100vw - 32px));
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 12px 12px 14px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-left: 2px solid var(--gold);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-float);
  pointer-events: auto;
}

.toast--error {
  border-left-color: var(--danger);
}

.toast__content {
  flex: 1;
  min-width: 0;
}

.toast__title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.4;
}

.toast__description {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--t2);
  word-break: break-word;
}

.toast__close {
  width: 18px;
  height: 18px;
  border-radius: var(--r-sm);
  color: var(--t3);
  font-size: 15px;
  line-height: 1;
  flex: none;
}

.toast__close:hover {
  color: var(--text);
  background: var(--panel-2);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity var(--d-panel) var(--ease-out),
    transform var(--d-panel) var(--ease-out);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}

.toast-move {
  transition: transform var(--d-panel) var(--ease-out);
}
</style>
