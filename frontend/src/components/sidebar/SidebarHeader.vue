<template>
  <div class="sidebar-header">
    <div class="logo">
      <span class="logo-icon">✦</span>
      <span class="logo-text">知枢星图</span>
    </div>
    <div class="header-actions">
      <button class="create-btn" @click="toggleCreateMenu">
        <span class="btn-icon">+</span>
        新建
      </button>
      <div v-if="showCreateDropdown" class="create-dropdown" @click.stop>
        <div class="dropdown-item" @click="createNewNote">
          <FileText :size="16" />
          新建内容
        </div>
        <div class="dropdown-item" @click="$emit('openNewFolderDialog')">
          <Folder :size="16" />
          新建文件夹
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { FileText, Folder } from 'lucide-vue-next'

defineEmits<{
  openNewFolderDialog: []
}>()

const router = useRouter()
const categoryStore = useCategoryStore()
const showCreateDropdown = ref(false)

function toggleCreateMenu() {
  showCreateDropdown.value = !showCreateDropdown.value
}

function hideCreateDropdown() {
  showCreateDropdown.value = false
}

function createNewNote() {
  showCreateDropdown.value = false
  const currentCategoryId = categoryStore.currentCategory?.id
  router.push({ name: 'NewNote', query: { category_id: currentCategoryId } })
}

onMounted(() => {
  document.addEventListener('click', hideCreateDropdown)
})

onUnmounted(() => {
  document.removeEventListener('click', hideCreateDropdown)
})
</script>

<style scoped lang="scss">
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  position: relative;
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-sm);
  color: #000;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--primary-hover);
  }

  .btn-icon {
    font-size: 14px;
  }
}

.create-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 4px 0;
  min-width: 140px;
  z-index: 100;

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
  }
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;

  .logo-icon {
    font-size: 20px;
    color: var(--primary-color);
  }

  .logo-text {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }
}
</style>
