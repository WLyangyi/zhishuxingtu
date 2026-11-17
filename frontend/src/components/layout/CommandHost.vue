<template>
  <CommandPalette
    :open="state.open"
    :pages="pages"
    :notes="notes"
    :actions="actions"
    @update:open="state.open = $event"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FileText, History, LogOut, Moon, Plus, Sun, Upload } from 'lucide-vue-next'
import CommandPalette, { type CommandItem } from '@/components/ui/CommandPalette.vue'
import { LAB_NAV, PRIMARY_NAV } from '@/config/nav'
import { useCommandPalette } from '@/lib/command'
import { notesApi } from '@/api/notes'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useImportStore } from '@/stores/import'

const { state } = useCommandPalette()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const importStore = useImportStore()

const notes = ref<CommandItem[]>([])

const pages = computed<CommandItem[]>(() =>
  [...PRIMARY_NAV, ...LAB_NAV].map((item) => ({
    id: `page-${item.id}`,
    label: item.label,
    hint: item.to,
    shortcut: item.shortcut,
    icon: item.icon,
    to: item.to
  }))
)

const actions = computed<CommandItem[]>(() => [
  { id: 'action-new-note', label: '新建笔记', icon: Plus, action: () => router.push('/notes/new') },
  {
    id: 'action-theme',
    label: themeStore.isDark ? '切换浅色主题' : '切换深色主题',
    icon: themeStore.isDark ? Sun : Moon,
    action: () => themeStore.toggle()
  },
  { id: 'action-import', label: '打开导入', icon: Upload, action: () => importStore.openImportModal() },
  {
    id: 'action-history',
    label: '导入历史',
    icon: History,
    action: () => router.push('/import-history')
  },
  {
    id: 'action-logout',
    label: '退出登录',
    icon: LogOut,
    action: () => {
      authStore.logout()
      router.push('/login')
    }
  }
])

async function loadNotes() {
  try {
    const response = await notesApi.list({ page_size: 8 })
    const items = response.data?.items ?? []
    notes.value = items.map((note) => ({
      id: `note-${note.id}`,
      label: note.title || '无标题笔记',
      hint: '笔记',
      icon: FileText,
      to: `/notes/${note.id}`
    }))
  } catch {
    notes.value = []
  }
}

watch(
  () => state.open,
  (open) => {
    if (open) void loadNotes()
  }
)
</script>
