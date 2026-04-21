<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click="$emit('cancel')">
      <div class="modal-content" @click.stop>
        <h3 class="modal-title">新建标签</h3>
        <input
          v-model="tagName"
          type="text"
          class="modal-input"
          placeholder="输入标签名称"
          @keyup.enter="handleConfirm"
          ref="inputRef"
        />
        <div class="color-picker">
          <span
            v-for="color in tagColors"
            :key="color"
            class="color-option"
            :class="{ active: selectedColor === color }"
            :style="{ backgroundColor: color }"
            @click="selectedColor = color"
          />
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="$emit('cancel')">取消</button>
          <button class="btn-confirm" @click="handleConfirm">创建</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  confirm: [name: string, color: string]
  cancel: []
}>()

const tagColors = [
  '#f59e0b', '#3b82f6', '#10b981', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#6366f1'
]

const tagName = ref('')
const selectedColor = ref('#f59e0b')
const inputRef = ref<HTMLInputElement | null>(null)

watch(() => props.visible, (val) => {
  if (val) {
    tagName.value = ''
    selectedColor.value = '#f59e0b'
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

function handleConfirm() {
  const name = tagName.value.trim()
  if (name) {
    emit('confirm', name, selectedColor.value)
  }
}
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 300px;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.modal-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
  margin-bottom: 12px;

  &:focus {
    outline: none;
    border-color: var(--primary-color);
  }

  &::placeholder {
    color: var(--text-muted);
  }
}

.color-picker {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
}

.color-option {
  display: inline-block;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 2px solid transparent;

  &:hover {
    transform: scale(1.1);
  }

  &.active {
    border-color: var(--text-primary);
  }
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-cancel, .btn-confirm {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);

  &:hover {
    border-color: var(--border-strong);
    color: var(--text-primary);
  }
}

.btn-confirm {
  background: var(--primary-color);
  border: none;
  color: #000;

  &:hover {
    background: var(--primary-hover);
  }
}
</style>
