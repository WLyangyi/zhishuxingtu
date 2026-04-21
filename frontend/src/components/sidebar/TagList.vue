<template>
  <div class="sidebar-section">
    <div class="section-header">
      <h3>标签</h3>
      <button @click="showCreateDialog = true" class="add-btn">+</button>
    </div>
    <div class="tag-list">
      <span
        v-for="tag in tagsStore.tags"
        :key="tag.id"
        class="tag-item"
        :class="{ active: sidebarStore.selectedTagId === tag.id }"
        :style="tagStyle(tag)"
        @click="handleTagClick(tag.id)"
        @contextmenu.prevent="showTagMenu($event, tag)"
      >
        {{ tag.name }}
        <span class="tag-count">{{ tag.note_count || 0 }}</span>
        <button
          class="tag-menu-btn"
          @click.stop="showTagMenu($event, tag)"
        >
          ⋮
        </button>
      </span>
    </div>

    <TagContextMenu
      :visible="contextMenu.visible"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @edit="startEditTag"
      @delete="deleteTag"
    />

    <CreateTagDialog
      :visible="showCreateDialog"
      @confirm="handleCreateTag"
      @cancel="showCreateDialog = false"
    />

    <EditTagDialog
      :visible="showEditDialog"
      :tag="editingTag"
      @confirm="handleEditTag"
      @cancel="showEditDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useSidebarStore } from '@/stores/sidebar'
import { useTagsStore } from '@/stores/tags'
import { useNotificationStore } from '@/stores/notification'
import type { Tag } from '@/types'
import TagContextMenu from './TagContextMenu.vue'
import CreateTagDialog from './CreateTagDialog.vue'
import EditTagDialog from './EditTagDialog.vue'

const sidebarStore = useSidebarStore()
const tagsStore = useTagsStore()
const notification = useNotificationStore()

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingTag = ref<Tag | null>(null)

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  tag: null as Tag | null
})

function tagStyle(tag: Tag) {
  const isActive = sidebarStore.selectedTagId === tag.id
  return {
    backgroundColor: isActive ? tag.color + '40' : tag.color + '15',
    borderColor: tag.color,
    color: tag.color
  }
}

function handleTagClick(tagId: string) {
  sidebarStore.selectTag(tagId)
}

function showTagMenu(event: MouseEvent, tag: Tag) {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    tag
  }
}

function hideTagContextMenu() {
  contextMenu.value.visible = false
}

function startEditTag() {
  if (!contextMenu.value.tag) return
  editingTag.value = contextMenu.value.tag
  showEditDialog.value = true
  hideTagContextMenu()
}

async function handleCreateTag(name: string, color: string) {
  if (!name) {
    notification.warning('请输入标签名称')
    return
  }
  try {
    await tagsStore.createTag({ name, color })
    notification.success('创建成功', `标签「${name}」已创建`)
    showCreateDialog.value = false
  } catch (error: any) {
    notification.error('创建失败', error.response?.data?.detail || '操作失败')
  }
}

async function handleEditTag(tagId: string, name: string, color: string) {
  if (!name) {
    notification.warning('请输入标签名称')
    return
  }
  try {
    await tagsStore.updateTag(tagId, { name, color })
    notification.success('编辑成功', `标签已更新为「${name}」`)
    showEditDialog.value = false
    editingTag.value = null
  } catch (error: any) {
    notification.error('编辑失败', error.response?.data?.detail || '操作失败')
  }
}

async function deleteTag() {
  if (!contextMenu.value.tag) return
  const tag = contextMenu.value.tag
  hideTagContextMenu()
  if (!confirm(`确定要删除标签「${tag.name}」吗？`)) {
    return
  }
  try {
    await tagsStore.deleteTag(tag.id)
    notification.success('删除成功', `标签「${tag.name}」已删除`)
    if (sidebarStore.selectedTagId === tag.id) {
      sidebarStore.clearFilter()
    }
  } catch (error: any) {
    notification.error('删除失败', error.response?.data?.detail || '操作失败')
  }
}

onMounted(() => {
  document.addEventListener('click', hideTagContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', hideTagContextMenu)
})
</script>

<style scoped lang="scss">
.sidebar-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  h3 {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .add-btn {
    width: 20px;
    height: 20px;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-tertiary);
    cursor: pointer;
    font-size: 12px;
    line-height: 1;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      border-color: var(--border-strong);
      color: var(--text-primary);
    }
  }
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-item {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;

  &:hover {
    transform: translateY(-1px);
  }

  &.active {
    box-shadow: 0 0 0 1px currentColor;
  }

  .tag-count {
    font-size: 10px;
    opacity: 0.7;
  }

  .tag-menu-btn {
    position: absolute;
    right: 2px;
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: inherit;
    cursor: pointer;
    opacity: 0;
    transition: all var(--transition-fast);
    font-size: 10px;
    border-radius: 4px;

    &:hover {
      opacity: 1;
    }
  }
}
</style>
