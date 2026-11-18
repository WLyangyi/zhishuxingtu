<template>
  <div class="library">
    <div v-if="treeOpen" class="library__overlay" @click="treeOpen = false" />

    <aside :class="['library__tree', treeOpen && 'library__tree--open']">
      <header class="tree__head">
        <span class="readout">LIBRARY · 我的笔记</span>
        <span class="tree__head-actions">
          <button type="button" class="tree__add" aria-label="新建分类" @click="openCategoryCreate">
            <Plus :size="14" :stroke-width="1.8" />
          </button>
          <button type="button" class="tree__close" aria-label="关闭目录" @click="treeOpen = false">
            <X :size="14" />
          </button>
        </span>
      </header>

      <button
        type="button"
        :class="['tree__item', isAllActive && 'tree__item--active']"
        @click="resetSelection"
      >
        <Inbox :size="15" :stroke-width="1.8" />
        <span class="tree__label">全部笔记</span>
        <span class="num tree__count">{{ notes.length }}</span>
      </button>

      <div v-for="category in categories" :key="category.id" class="tree__group">
        <button
          type="button"
          :class="[
            'tree__item',
            'tree__item--category',
            filter.categoryId === category.id && !filter.folderId && 'tree__item--active'
          ]"
          @click="selectCategory(category.id)"
        >
          <FolderOpen :size="15" :stroke-width="1.8" />
          <span class="tree__label">{{ category.name }}</span>
          <span class="num tree__count">{{ categoryCounts.get(category.id) ?? 0 }}</span>
          <span
            class="tree__more"
            role="button"
            aria-label="管理分类"
            @click.stop="openTreeMenu($event, { type: 'category', id: category.id, name: category.name })"
          >
            <MoreHorizontal :size="13" :stroke-width="1.8" />
          </span>
        </button>

        <button
          v-for="folder in foldersByCategory.get(category.id) ?? []"
          :key="folder.id"
          type="button"
          :class="['tree__item', 'tree__item--folder', filter.folderId === folder.id && 'tree__item--active']"
          :style="{ paddingLeft: `${10 + folder.level * 14}px` }"
          @click="selectFolder(folder)"
        >
          <Folder :size="13" :stroke-width="1.8" />
          <span class="tree__label">{{ folder.name }}</span>
          <span class="num tree__count">{{ folderCounts.get(folder.id) ?? 0 }}</span>
          <span
            class="tree__more"
            role="button"
            aria-label="管理文件夹"
            @click.stop="openTreeMenu($event, { type: 'folder', id: folder.id, name: folder.name, categoryId: folder.category_id, parentId: folder.parent_id })"
          >
            <MoreHorizontal :size="13" :stroke-width="1.8" />
          </span>
        </button>
      </div>

      <div v-if="tags.length" class="tree__tags">
        <span class="readout tree__section-label">TAGS</span>
        <button
          v-for="tag in tags.slice(0, 10)"
          :key="tag.id"
          type="button"
          :class="['tree__tag', filter.tagId === tag.id && 'tree__tag--active']"
          @click="selectTag(tag.id)"
        >
          <span class="tree__tag-name">#{{ tag.name }}</span>
          <span class="num tree__count">{{ tag.count }}</span>
        </button>
      </div>

      <RouterLink to="/import-history" class="tree__import">导入历史 →</RouterLink>
    </aside>

    <div
      v-if="treeMenu.open"
      class="tree-menu"
      :style="{ left: `${treeMenu.x}px`, top: `${treeMenu.y}px` }"
    >
      <button type="button" class="tree-menu__item" @click="menuAction('folder-create')">
        <FolderPlus :size="13" :stroke-width="1.8" />
        新建文件夹
      </button>
      <button type="button" class="tree-menu__item" @click="menuAction('rename')">
        <Pencil :size="13" :stroke-width="1.8" />
        重命名
      </button>
      <span class="tree-menu__separator" />
      <button type="button" class="tree-menu__item tree-menu__item--danger" @click="menuAction('delete')">
        <Trash2 :size="13" :stroke-width="1.8" />
        删除
      </button>
    </div>

    <AppModal :open="formModal.open" :title="formTitle" size="sm" @update:open="formModal.open = $event">
      <AppInput v-model="formModal.name" label="名称" placeholder="输入名称" class="tree-form__input" />
      <template #footer>
        <AppButton variant="secondary" size="sm" @click="formModal.open = false">取消</AppButton>
        <AppButton size="sm" :disabled="!formModal.name.trim()" @click="submitForm">
          {{ formActionLabel }}
        </AppButton>
      </template>
    </AppModal>

    <AppModal
      :open="deleteConfirm.open"
      :title="deleteConfirm.kind === 'category' ? '删除分类？' : '删除文件夹？'"
      size="sm"
      @update:open="deleteConfirm.open = $event"
    >
      <p class="tree-delete__text">「{{ deleteConfirm.name }}」将被删除，此操作无法撤销。</p>
      <template #footer>
        <AppButton variant="secondary" size="sm" @click="deleteConfirm.open = false">取消</AppButton>
        <AppButton variant="danger" size="sm" @click="confirmDelete">删除</AppButton>
      </template>
    </AppModal>

    <main class="library__main">
      <div class="library__bar">
        <button type="button" class="library__menu" aria-label="打开目录" @click="treeOpen = true">
          <ListTree :size="16" />
        </button>
        <Breadcrumb :items="breadcrumb" class="library__breadcrumb" />
        <div class="library__tools">
          <SearchInput v-model="filter.keyword" placeholder="搜索标题或正文…" class="library__search" />
          <SegmentedControl
            :model-value="view"
            :items="viewItems"
            size="sm"
            aria-label="视图切换"
            @update:model-value="setView"
          />
        </div>
      </div>

      <header class="library__title-row">
        <div class="library__title-group">
          <span class="readout">{{ kicker }}</span>
          <h1 class="library__title">{{ title }}</h1>
        </div>
        <span class="readout library__count">{{ filteredNotes.length }} NOTES</span>
        <button v-if="hasFilter" type="button" class="library__clear" @click="resetSelection">
          清除筛选
        </button>
      </header>

      <div v-if="loading" class="library__skeleton">
        <Skeleton v-for="index in 6" :key="index" :height="16" />
      </div>

      <div v-else-if="loadError" class="library__state">
        <EmptyState title="笔记加载失败" :description="loadError">
          <AppButton size="sm" variant="secondary" @click="loadNotes">重试</AppButton>
        </EmptyState>
      </div>

      <div v-else-if="!notes.length" class="library__state">
        <EmptyState title="还没有笔记" description="写下第一条思考，星图会从这里开始生长。">
          <AppButton size="sm" @click="router.push('/notes/new')">新建笔记</AppButton>
        </EmptyState>
      </div>

      <div v-else-if="!filteredNotes.length" class="library__state">
        <EmptyState title="没有匹配的笔记" description="换个关键词，或清除当前筛选条件。">
          <AppButton size="sm" variant="secondary" @click="resetSelection">清除筛选</AppButton>
        </EmptyState>
      </div>

      <div v-else-if="view === 'list'" class="library__list">
        <RouterLink
          v-for="note in filteredNotes"
          :key="note.id"
          :to="`/notes/${note.id}`"
          class="note-row"
        >
          <div class="note-row__main">
            <h2 class="note-row__title">{{ note.title }}</h2>
            <p class="note-row__excerpt">{{ excerptOf(note) }}</p>
          </div>

          <div class="note-row__tags">
            <span v-for="tag in note.tags.slice(0, 2)" :key="tag.id" class="note-row__tag">
              #{{ tag.name }}
            </span>
            <span v-if="note.tags.length > 2" class="note-row__tag">+{{ note.tags.length - 2 }}</span>
          </div>

          <span class="note-row__meta">
            {{ relativeTime(note.updated_at) }}
            <span v-if="note.linked_note_ids.length"> · {{ note.linked_note_ids.length }} LINKS</span>
          </span>
        </RouterLink>
      </div>

      <div v-else class="library__grid">
        <RouterLink
          v-for="note in filteredNotes"
          :key="note.id"
          :to="`/notes/${note.id}`"
          class="note-card"
        >
          <div class="note-card__top">
            <FileText :size="14" :stroke-width="1.8" class="note-card__icon" />
            <span class="note-card__meta">{{ relativeTime(note.updated_at) }}</span>
          </div>
          <h2 class="note-card__title">{{ note.title }}</h2>
          <p class="note-card__excerpt">{{ excerptOf(note) }}</p>
          <div class="note-card__foot">
            <span v-for="tag in note.tags.slice(0, 3)" :key="tag.id" class="note-row__tag">
              #{{ tag.name }}
            </span>
            <span v-if="note.linked_note_ids.length" class="num note-card__links">
              {{ note.linked_note_ids.length }} LINKS
            </span>
          </div>
        </RouterLink>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileText, Folder, FolderOpen, FolderPlus, Inbox, ListTree, MoreHorizontal, Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppModal from '@/components/ui/AppModal.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { notesApi } from '@/api/notes'
import { useCategoryStore } from '@/stores/category'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import {
  countNotesForCategory,
  countNotesForFolder,
  filterLibraryNotes,
  flattenFolders,
  folderPath,
  tagCounts,
  type LibrarySelection
} from '@/lib/library'
import { relativeTime } from '@/lib/time'
import type { FolderTree } from '@/types/folder'
import type { Note } from '@/types/note'

const router = useRouter()
const route = useRoute()
const categoryStore = useCategoryStore()
const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()

const notes = ref<Note[]>([])
const loading = ref(true)
const loadError = ref('')
const treeOpen = ref(false)
const view = ref<'list' | 'grid'>((localStorage.getItem('library:view') as 'list' | 'grid') || 'list')

const filter = reactive<LibrarySelection>({
  categoryId: null,
  folderId: null,
  tagId: null,
  keyword: ''
})

const viewItems = [
  { label: '列表', value: 'list' },
  { label: '网格', value: 'grid' }
]

const categories = computed(() => categoryStore.categories)
const flatFolders = computed(() => flattenFolders(foldersStore.folders))

const foldersByCategory = computed(() => {
  const map = new Map<string, FolderTree[]>()
  for (const folder of flatFolders.value) {
    if (!folder.category_id) continue
    const list = map.get(folder.category_id) ?? []
    list.push(folder)
    map.set(folder.category_id, list)
  }
  return map
})

const categoryCounts = computed(() => {
  const map = new Map<string, number>()
  for (const category of categories.value) {
    map.set(category.id, countNotesForCategory(notes.value, category.id, flatFolders.value))
  }
  return map
})

const folderCounts = computed(() => {
  const map = new Map<string, number>()
  for (const folder of flatFolders.value) {
    map.set(folder.id, countNotesForFolder(notes.value, folder.id, flatFolders.value))
  }
  return map
})

const tags = computed(() => tagCounts(notes.value))
const filteredNotes = computed(() => filterLibraryNotes(notes.value, filter, flatFolders.value))
const isAllActive = computed(
  () => !filter.categoryId && !filter.folderId && !filter.tagId && !filter.keyword
)
const hasFilter = computed(
  () => Boolean(filter.categoryId || filter.folderId || filter.tagId || filter.keyword)
)

const selectedCategory = computed(
  () => categories.value.find((category) => category.id === filter.categoryId) ?? null
)
const selectedTag = computed(() => tags.value.find((tag) => tag.id === filter.tagId) ?? null)
const path = computed(() =>
  filter.folderId ? folderPath(flatFolders.value, filter.folderId) : []
)

const title = computed(() => {
  if (path.value.length) return path.value[path.value.length - 1].name
  if (selectedCategory.value) return selectedCategory.value.name
  if (selectedTag.value) return `#${selectedTag.value.name}`
  return '我的笔记'
})

const kicker = computed(() => {
  if (path.value.length) return 'FOLDER · 文件夹'
  if (selectedCategory.value) return 'AREA · 分区'
  if (selectedTag.value) return 'TAG · 标签'
  return 'LIBRARY · 全部笔记'
})

const breadcrumb = computed(() => {
  const items: Array<{ label: string; to?: string }> = [
    { label: '我的笔记', to: hasFilter.value ? '/library' : undefined }
  ]

  if (selectedCategory.value) {
    items.push({
      label: selectedCategory.value.name,
      to: filter.folderId ? `/library/${selectedCategory.value.id}` : undefined
    })
  }

  path.value.forEach((folder, index) => {
    const isLast = index === path.value.length - 1
    items.push({
      label: folder.name,
      to:
        isLast || !selectedCategory.value
          ? undefined
          : `/library/${selectedCategory.value.id}?folder=${folder.id}`
    })
  })

  if (selectedTag.value) items.push({ label: `#${selectedTag.value.name}` })

  return items
})

function excerptOf(note: Note) {
  const text = (note.content || '')
    .replace(/[#*`>[\]()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text ? text.slice(0, 110) : '还没有正文'
}

function setView(next: string) {
  view.value = next === 'grid' ? 'grid' : 'list'
  localStorage.setItem('library:view', view.value)
}

function selectCategory(categoryId: string) {
  filter.categoryId = categoryId
  filter.folderId = null
  filter.tagId = null
  treeOpen.value = false
}

function selectFolder(folder: FolderTree) {
  filter.categoryId = folder.category_id ?? null
  filter.folderId = folder.id
  filter.tagId = null
  treeOpen.value = false
}

function selectTag(tagId: string) {
  filter.tagId = filter.tagId === tagId ? null : tagId
  filter.categoryId = null
  filter.folderId = null
  treeOpen.value = false
}

function resetSelection() {
  filter.categoryId = null
  filter.folderId = null
  filter.tagId = null
  filter.keyword = ''
  treeOpen.value = false
}

/* ---- 分类/文件夹 CRUD（P6-③） ---- */
type FormKind = 'category-create' | 'category-rename' | 'folder-create' | 'folder-rename'

const formModal = reactive({
  open: false,
  kind: 'category-create' as FormKind,
  name: '',
  categoryId: null as string | null,
  folderId: null as string | null
})

const formTitle = computed(() => {
  switch (formModal.kind) {
    case 'category-create':
      return '新建分类'
    case 'category-rename':
      return '重命名分类'
    case 'folder-create':
      return '新建文件夹'
    case 'folder-rename':
      return '重命名文件夹'
  }
})

const formActionLabel = computed(() =>
  formModal.kind === 'category-create' || formModal.kind === 'folder-create' ? '创建' : '保存'
)

function openCategoryCreate() {
  formModal.kind = 'category-create'
  formModal.name = ''
  formModal.categoryId = null
  formModal.folderId = null
  formModal.open = true
}

/* 树行「⋯」菜单 */
type TreeMenuTarget = {
  type: 'category' | 'folder'
  id: string
  name: string
  categoryId?: string | null
  parentId?: string | null
}

const treeMenu = reactive({
  open: false,
  x: 0,
  y: 0,
  target: null as TreeMenuTarget | null
})

function openTreeMenu(event: MouseEvent, target: TreeMenuTarget) {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  treeMenu.open = true
  treeMenu.x = rect.right + 6
  treeMenu.y = rect.top
  treeMenu.target = target
}

function closeTreeMenu() {
  treeMenu.open = false
  treeMenu.target = null
}

function menuAction(action: 'folder-create' | 'rename' | 'delete') {
  const target = treeMenu.target
  closeTreeMenu()
  if (!target) return

  if (action === 'delete') {
    deleteConfirm.kind = target.type
    deleteConfirm.id = target.id
    deleteConfirm.name = target.name
    deleteConfirm.open = true
    return
  }

  if (action === 'folder-create') {
    formModal.kind = 'folder-create'
    formModal.name = ''
    formModal.categoryId = target.type === 'category' ? target.id : (target.categoryId ?? null)
    formModal.folderId = target.type === 'folder' ? (target.id as string) : null
    formModal.open = true
    return
  }

  formModal.kind = target.type === 'category' ? 'category-rename' : 'folder-rename'
  formModal.name = target.name
  formModal.categoryId = target.type === 'category' ? target.id : null
  formModal.folderId = target.type === 'folder' ? target.id : null
  formModal.open = true
}

async function submitForm() {
  const name = formModal.name.trim()
  if (!name) return

  try {
    if (formModal.kind === 'category-create') {
      await categoryStore.createCategory({ name })
    } else if (formModal.kind === 'category-rename') {
      await categoryStore.updateCategory(formModal.categoryId as string, { name })
    } else if (formModal.kind === 'folder-rename') {
      await foldersStore.updateFolder(formModal.folderId as string, { name })
    } else if (formModal.kind === 'folder-create') {
      await foldersStore.createFolder({
        name,
        category_id: formModal.categoryId ?? undefined,
        parent_id: formModal.folderId ?? undefined
      })
    }
    formModal.open = false
  } catch {
    /* store 已发错误通知，弹窗保持打开便于修正 */
  }
}

/* 删除确认 */
const deleteConfirm = reactive({
  open: false,
  kind: 'category' as 'category' | 'folder',
  id: '',
  name: ''
})

async function confirmDelete() {
  const { kind, id } = deleteConfirm
  deleteConfirm.open = false
  try {
    if (kind === 'category') {
      await categoryStore.deleteCategory(id)
    } else {
      await foldersStore.deleteFolder(id)
    }
    if (filter.categoryId === id || filter.folderId === id) resetSelection()
  } catch {
    /* store 已发错误通知 */
  }
}

function syncFromRoute() {
  filter.categoryId = (route.params.categoryId as string) || null
  filter.folderId = (route.query.folder as string) || null
  filter.tagId = (route.query.tag as string) || null
  filter.keyword = (route.query.q as string) || ''
}

async function loadNotes() {
  loading.value = true
  loadError.value = ''
  try {
    const first = await notesApi.list({ page_size: 100, page: 1 })
    const items = [...first.data.items]
    const total = first.data.total
    let page = 1

    while (items.length < total && page < 5) {
      page += 1
      const next = await notesApi.list({ page_size: 100, page })
      items.push(...next.data.items)
    }

    notes.value = items
  } catch {
    loadError.value = '网络异常，请稍后重试。'
  } finally {
    loading.value = false
  }
}

watch(() => route.fullPath, syncFromRoute)

onMounted(async () => {
  syncFromRoute()
  await Promise.allSettled([
    categoryStore.fetchCategories(),
    foldersStore.fetchFolders(),
    tagsStore.fetchTags(),
    loadNotes()
  ])
  window.addEventListener('click', closeTreeMenu)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeTreeMenu)
})
</script>

<style scoped>
.library {
  position: relative;
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.library__overlay {
  display: none;
}

.library__tree {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 260px;
  flex: none;
  padding: 18px 12px 24px;
  border-right: 1px solid var(--line);
  overflow-y: auto;
  background: color-mix(in srgb, var(--panel) 35%, transparent);
}

.tree__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 8px 12px;
}

.tree__head-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tree__add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--t3);
  cursor: pointer;
  transition: color var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out);
}

.tree__add:hover {
  color: var(--gold);
  border-color: var(--gold-line);
}

.tree-form__input {
  width: 100%;
}

.tree__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: 2px;
  border-radius: var(--r-sm);
  color: var(--t3);
  opacity: 0;
  cursor: pointer;
  transition: opacity var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out),
    background var(--d-fast) var(--ease-out);
}

.tree__item:hover .tree__more,
.tree__more:focus-visible {
  opacity: 1;
}

.tree__more:hover {
  color: var(--gold);
  background: var(--panel-2);
}

.tree-menu {
  position: fixed;
  z-index: var(--z-overlay);
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 132px;
  padding: 4px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  background: var(--panel);
  box-shadow: var(--shadow-float);
}

.tree-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  font-size: 12px;
  color: var(--t2);
  text-align: left;
  cursor: pointer;
  transition: background var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out);
}

.tree-menu__item:hover {
  background: var(--panel-2);
  color: var(--text);
}

.tree-menu__item--danger {
  color: var(--danger);
}

.tree-menu__item--danger:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

.tree-menu__separator {
  height: 1px;
  margin: 2px 4px;
  background: var(--line);
}

.tree-delete__text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--t2);
}

.tree__close {
  display: none;
  color: var(--t3);
}

.tree__item {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 30px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  color: var(--t3);
  text-align: left;
  transition: color var(--d-fast) var(--ease-out), background-color var(--d-fast) var(--ease-out);
}

.tree__item:hover {
  color: var(--t2);
  background: var(--panel-2);
}

.tree__item--active {
  color: var(--gold);
  background: var(--gold-soft);
}

.tree__item--category {
  margin-top: 10px;
  color: var(--t2);
  font-weight: 500;
}

.tree__item--folder {
  min-height: 27px;
  font-size: 12px;
}

.tree__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree__count {
  font-size: 9.5px;
  color: var(--t3);
}

.tree__item--active .tree__count {
  color: var(--gold);
}

.tree__tags {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.tree__section-label {
  padding: 0 8px 6px;
}

.tree__tag {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 26px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  color: var(--t3);
  font-size: 12px;
  transition: color var(--d-fast) var(--ease-out), background-color var(--d-fast) var(--ease-out);
}

.tree__tag:hover {
  color: var(--t2);
  background: var(--panel-2);
}

.tree__tag--active {
  color: var(--gold);
  background: var(--gold-soft);
}

.tree__tag-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree__import {
  margin-top: auto;
  padding: 18px 8px 0;
  font-size: 11px;
  color: var(--t3);
}

.tree__import:hover {
  color: var(--gold);
}

.library__main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 22px 32px 56px;
}

.library__bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.library__menu {
  display: none;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--r-sm);
  color: var(--t2);
}

.library__menu:hover {
  background: var(--panel-2);
}

.library__breadcrumb {
  min-width: 0;
}

.library__tools {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.library__search {
  width: 220px;
}

.library__title-row {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  padding: 26px 0 20px;
}

.library__title-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.library__title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.035em;
}

.library__count {
  padding-bottom: 4px;
  color: var(--t3);
}

.library__clear {
  margin-left: auto;
  margin-bottom: 3px;
  font-size: 11px;
  color: var(--t3);
}

.library__clear:hover {
  color: var(--gold);
}

.library__skeleton {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 8px;
}

.library__state {
  padding-top: 24px;
}

.library__list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--line);
}

.note-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 150px;
  align-items: center;
  gap: 24px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--line);
  transition: transform var(--d-base) var(--ease-out),
    background-color var(--d-base) var(--ease-out);
}

.note-row:hover {
  transform: translateX(5px);
  background: color-mix(in srgb, var(--panel) 45%, transparent);
}

.note-row__main {
  min-width: 0;
}

.note-row__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.01em;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--d-fast) var(--ease-out);
}

.note-row:hover .note-row__title {
  color: var(--gold);
}

.note-row__excerpt {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.note-row__tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.note-row__tag {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.02em;
  color: var(--steel);
  white-space: nowrap;
}

.note-row__meta {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.04em;
  color: var(--t3);
  text-align: right;
  white-space: nowrap;
}

.library__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(238px, 1fr));
  gap: 14px;
}

.note-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 150px;
  padding: 15px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: color-mix(in srgb, var(--panel) 30%, transparent);
  transition: border-color var(--d-fast) var(--ease-out),
    transform var(--d-fast) var(--ease-out);
}

.note-card:hover {
  border-color: var(--line-strong);
  transform: translateY(-2px);
}

.note-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.note-card__icon {
  color: var(--gold);
}

.note-card__meta {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--t3);
}

.note-card__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  letter-spacing: -0.01em;
  color: var(--text);
  transition: color var(--d-fast) var(--ease-out);
}

.note-card:hover .note-card__title {
  color: var(--gold);
}

.note-card__excerpt {
  flex: 1;
  font-size: 11px;
  line-height: 1.7;
  color: var(--t3);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.note-card__foot {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--line);
}

.note-card__links {
  margin-left: auto;
  font-size: 9px;
  color: var(--t3);
}

@media (max-width: 1023px) {
  .library__main {
    padding: 20px 24px 48px;
  }

  .library__search {
    width: 180px;
  }

  .note-row {
    grid-template-columns: minmax(0, 1fr) 130px;
    gap: 16px;
  }

  .note-row__tags {
    display: none;
  }
}

@media (max-width: 767px) {
  .library__tree {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 4;
    width: 280px;
    background: var(--panel);
    border-right: 1px solid var(--line-strong);
    transform: translateX(-100%);
    transition: transform var(--d-panel) var(--ease-out);
  }

  .library__tree--open {
    transform: translateX(0);
  }

  .tree__close {
    display: inline-flex;
  }

  .library__overlay {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 3;
    background: var(--overlay);
  }

  .library__main {
    padding: 16px 16px 40px;
  }

  .library__bar {
    flex-wrap: wrap;
    gap: 10px;
  }

  .library__menu {
    display: inline-flex;
  }

  .library__tools {
    width: 100%;
    margin-left: 0;
  }

  .library__search {
    flex: 1;
    width: auto;
  }

  .library__title {
    font-size: 26px;
  }

  .note-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
  }

  .note-row__meta {
    font-size: 9px;
  }

  .library__grid {
    grid-template-columns: 1fr;
  }
}
</style>
