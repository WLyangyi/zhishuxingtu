<template>
  <aside class="sidebar">
    <SidebarHeader @openNewFolderDialog="handleOpenNewFolderDialog" />

    <div class="sidebar-content">
      <CategorySection
        v-for="cat in categories"
        :key="cat.id"
        :category="cat"
        :is-active="currentCategoryId === cat.id"
        @switch="switchCategory"
        @openNewFolderDialog="handleCategoryNewFolder"
      >
        <FolderList
          v-if="currentCategoryId === cat.id"
          ref="folderListRefs"
          :category-id="cat.id"
          :is-active-category="currentCategoryId === cat.id"
        />
      </CategorySection>
    </div>

    <ToolSection />
    <TagList />
    <RecentNotes />
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, watch, ref } from 'vue'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import { useNotesStore } from '@/stores/notes'
import { useCategoryStore } from '@/stores/category'
import SidebarHeader from '@/components/sidebar/SidebarHeader.vue'
import CategorySection from '@/components/sidebar/CategorySection.vue'
import FolderList from '@/components/sidebar/FolderList.vue'
import ToolSection from '@/components/sidebar/ToolSection.vue'
import TagList from '@/components/sidebar/TagList.vue'
import RecentNotes from '@/components/sidebar/RecentNotes.vue'

const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()
const notesStore = useNotesStore()
const categoryStore = useCategoryStore()

const folderListRefs = ref<InstanceType<typeof FolderList>[]>([])

const categories = computed(() => categoryStore.categories)
const currentCategoryId = computed(() => categoryStore.currentCategory?.id)

async function switchCategory(categoryId: string) {
  const category = categories.value.find(c => c.id === categoryId)
  if (category) {
    categoryStore.currentCategory = category
    await foldersStore.fetchFolders(categoryId)
    await notesStore.fetchNotes({ folder_id: undefined })
  }
}

function handleOpenNewFolderDialog() {
  const activeFolderList = folderListRefs.value[0]
  if (activeFolderList) {
    activeFolderList.openCreateDialog(currentCategoryId.value || undefined)
  }
}

function handleCategoryNewFolder(categoryId: string) {
  const activeFolderList = folderListRefs.value[0]
  if (activeFolderList) {
    activeFolderList.openCreateDialog(categoryId)
  }
}

onMounted(async () => {
  await categoryStore.fetchCategories()
  await tagsStore.fetchTags()
  if (categoryStore.categories.length > 0 && !categoryStore.currentCategory) {
    categoryStore.currentCategory = categoryStore.categories[0]
    await foldersStore.fetchFolders(categoryStore.currentCategory.id)
    await notesStore.fetchNotes({ category_id: categoryStore.currentCategory.id })
  } else {
    await foldersStore.fetchFolders()
    await notesStore.fetchNotes()
  }
})

watch(() => categoryStore.currentCategory, async (newCat) => {
  if (newCat) {
    await foldersStore.fetchFolders(newCat.id)
  }
})
</script>

<style scoped lang="scss">
.sidebar {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: 0;
  position: relative;
  flex-shrink: 0;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}
</style>
