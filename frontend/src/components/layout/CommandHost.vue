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
import {
  FileText,
  FolderClosed,
  History,
  LogOut,
  Moon,
  Play,
  Plus,
  Sun,
  Upload,
  WandSparkles
} from 'lucide-vue-next'
import CommandPalette, { type CommandItem } from '@/components/ui/CommandPalette.vue'
import { LAB_NAV, PRIMARY_NAV } from '@/config/nav'
import { buildResourceCommands, useCommandPalette } from '@/lib/command'
import { flattenFolders } from '@/lib/library'
import { notesApi } from '@/api/notes'
import { foldersApi } from '@/api/folders'
import { skillsApi } from '@/api/skills'
import { promptsApi } from '@/api/prompts'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useImportStore } from '@/stores/import'

const { state } = useCommandPalette()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const importStore = useImportStore()

const notes = ref<CommandItem[]>([])
const resourceCommands = ref<CommandItem[]>([])

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

function iconForCommand(id: string) {
  if (id.startsWith('new-note-')) return FolderClosed
  if (id.startsWith('exec-skill-')) return Play
  if (id.startsWith('open-prompt-')) return WandSparkles
  return undefined
}

const actions = computed<CommandItem[]>(() => {
  const staticActions: CommandItem[] = [
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
  ]
  const dynamic: CommandItem[] = resourceCommands.value.map((cmd) => ({
    ...cmd,
    icon: iconForCommand(cmd.id)
  }))
  return [...staticActions, ...dynamic]
})

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

async function loadResources() {
  const [folders, skills, prompts] = await Promise.all([
    foldersApi.list().then((res) => res.data ?? []).catch(() => []),
    skillsApi.getSkills({ page_size: 50 }).then((res) => res.items ?? []).catch(() => []),
    promptsApi.getPrompts({ page_size: 50 }).then((res) => res.data?.items ?? []).catch(() => [])
  ])

  resourceCommands.value = buildResourceCommands({
    folders: flattenFolders(folders).map((folder) => ({ id: folder.id, name: folder.name })),
    skills: skills.map((skill) => ({ id: skill.id, name: skill.name })),
    prompts: prompts.map((prompt) => ({ id: prompt.id, name: prompt.name }))
  })
}

watch(
  () => state.open,
  (open) => {
    if (open) {
      void loadNotes()
      void loadResources()
    }
  }
)
</script>
