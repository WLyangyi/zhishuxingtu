<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="context-menu"
      :style="{ left: x + 'px', top: y + 'px' }"
      @click.stop
    >
      <div class="menu-item" @click="$emit('edit')">
        <Edit2 :size="14" />
        编辑标签
      </div>
      <div class="menu-item danger" @click="$emit('delete')">
        <Trash2 :size="14" />
        删除标签
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { Edit2, Trash2 } from 'lucide-vue-next'

defineProps<{
  visible: boolean
  x: number
  y: number
}>()

defineEmits<{
  edit: []
  delete: []
}>()
</script>

<style scoped lang="scss">
.context-menu {
  position: fixed;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 4px 0;
  min-width: 150px;
  z-index: 1000;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.danger {
    color: var(--accent-red);

    &:hover {
      background: rgba(239, 68, 68, 0.1);
    }
  }
}
</style>
