<template>
  <DialogRoot :open="open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay class="zs-overlay" />
      <DialogContent class="zs-modal" :class="`zs-modal--${size}`">
        <VisuallyHidden v-if="!title">
          <DialogTitle>{{ ariaLabel }}</DialogTitle>
        </VisuallyHidden>
        <VisuallyHidden v-if="!description">
          <DialogDescription>{{ title || ariaLabel }}</DialogDescription>
        </VisuallyHidden>

        <header class="zs-modal__header">
          <div class="zs-modal__heading">
            <DialogTitle v-if="title" class="zs-modal__title">{{ title }}</DialogTitle>
            <DialogDescription v-if="description" class="zs-modal__description">
              {{ description }}
            </DialogDescription>
          </div>
          <DialogClose v-if="!hideClose" class="zs-modal__close" aria-label="关闭">
            <X :size="16" :stroke-width="1.8" />
          </DialogClose>
        </header>

        <div class="zs-modal__body"><slot /></div>

        <footer v-if="$slots.footer" class="zs-modal__footer"><slot name="footer" /></footer>
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
    description?: string
    ariaLabel?: string
    size?: 'sm' | 'md' | 'lg'
    hideClose?: boolean
  }>(),
  { open: false, title: '', description: '', ariaLabel: '对话框', size: 'md', hideClose: false }
)

const emit = defineEmits<{ 'update:open': [value: boolean] }>()
</script>

<style>
.zs-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  background: var(--overlay);
  animation: zs-fade-in 200ms var(--ease-out);
}

.zs-modal {
  position: fixed;
  top: 50%;
  left: 50%;
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  width: min(92vw, 560px);
  max-height: 86vh;
  transform: translate(-50%, -50%);
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-float);
  animation: zs-modal-in 240ms var(--ease-out);
}

.zs-modal--sm { width: min(92vw, 420px); }
.zs-modal--md { width: min(92vw, 560px); }
.zs-modal--lg { width: min(94vw, 760px); }

.zs-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 12px;
}

.zs-modal__heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.zs-modal__title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
}

.zs-modal__description {
  font-size: 12px;
  line-height: 1.6;
  color: var(--t2);
}

.zs-modal__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--r-sm);
  color: var(--t3);
  flex: none;
}

.zs-modal__close:hover {
  color: var(--text);
  background: var(--panel-2);
}

.zs-modal__body {
  padding: 4px 20px 18px;
  overflow-y: auto;
}

.zs-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--line);
}

@keyframes zs-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes zs-modal-in {
  from { opacity: 0; transform: translate(-50%, -48%) scale(0.985); }
  to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}
</style>
