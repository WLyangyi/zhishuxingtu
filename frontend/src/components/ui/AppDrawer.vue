<template>
  <DialogRoot :open="open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay class="zs-overlay" />
      <DialogContent class="zs-drawer" :class="`zs-drawer--${side}`" :style="{ width: `${width}px` }">
        <VisuallyHidden v-if="!title">
          <DialogTitle>{{ ariaLabel }}</DialogTitle>
        </VisuallyHidden>
        <VisuallyHidden>
          <DialogDescription>{{ title || ariaLabel }}</DialogDescription>
        </VisuallyHidden>

        <header class="zs-drawer__header">
          <div class="zs-drawer__heading">
            <span v-if="kicker" class="readout">{{ kicker }}</span>
            <DialogTitle v-if="title" class="zs-drawer__title">{{ title }}</DialogTitle>
          </div>
          <DialogClose class="zs-drawer__close" aria-label="关闭">
            <X :size="16" :stroke-width="1.8" />
          </DialogClose>
        </header>

        <div class="zs-drawer__body"><slot /></div>

        <footer v-if="$slots.footer" class="zs-drawer__footer"><slot name="footer" /></footer>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<script setup lang="ts">
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  VisuallyHidden
} from 'reka-ui'
import { X } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    open?: boolean
    title?: string
    kicker?: string
    ariaLabel?: string
    side?: 'right' | 'left'
    width?: number
  }>(),
  {
    open: false,
    title: '',
    kicker: '',
    ariaLabel: '侧边抽屉',
    side: 'right',
    width: 380
  }
)

const emit = defineEmits<{ 'update:open': [value: boolean] }>()
</script>

<style>
.zs-drawer {
  position: fixed;
  top: 0;
  bottom: 0;
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  max-width: 94vw;
  background: var(--panel);
  box-shadow: var(--shadow-float);
}

.zs-drawer--right {
  right: 0;
  border-left: 1px solid var(--line-strong);
  animation: zs-drawer-in-right 260ms var(--ease-out);
}

.zs-drawer--left {
  left: 0;
  border-right: 1px solid var(--line-strong);
  animation: zs-drawer-in-left 260ms var(--ease-out);
}

.zs-drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--line);
}

.zs-drawer__heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zs-drawer__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.zs-drawer__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--r-sm);
  color: var(--t3);
}

.zs-drawer__close:hover {
  color: var(--text);
  background: var(--panel-2);
}

.zs-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.zs-drawer__footer {
  padding: 12px 20px;
  border-top: 1px solid var(--line);
}

@keyframes zs-drawer-in-right {
  from { transform: translateX(24px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes zs-drawer-in-left {
  from { transform: translateX(-24px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
</style>
