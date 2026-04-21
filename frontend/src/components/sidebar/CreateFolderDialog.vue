<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click="$emit('cancel')">
      <div class="modal-content" @click.stop>
        <h3 class="modal-title">{{ parentFolder ? '新建子文件夹' : '新建文件夹' }}</h3>
        <div v-if="parentFolder" class="parent-info">
          <span class="parent-label">父文件夹：</span>
          <span class="parent-name">{{ parentFolder.name }}</span>
        </div>
        <input
          v-model="folderName"
          type="text"
          class="modal-input"
          placeholder="输入文件夹名称"
          @keyup.enter="handleConfirm"
          ref="inputRef"
        />
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
import type { FolderTree } from '@/types'

const props = defineProps<{
  visible: boolean
  parentFolder: FolderTree | null
}>()

const emit = defineEmits<{
  confirm: [name: string]
  cancel: []
}>()

const folderName = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

watch(() => props.visible, (val) => {
  if (val) {
    folderName.value = ''
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

function handleConfirm() {
  const name = folderName.value.trim()
  if (name) {
    emit('confirm', name)
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

.parent-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;

  .parent-label {
    font-size: 12px;
    color: var(--text-muted);
  }

  .parent-name {
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 500;
  }
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
