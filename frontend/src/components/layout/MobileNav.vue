<template>
  <nav class="mobile-nav" aria-label="移动端导航">
    <RouterLink
      v-for="item in PRIMARY_NAV"
      :key="item.id"
      :to="item.to"
      :class="['mobile-nav__item', isActive(item) && 'mobile-nav__item--active']"
      @click="emit('navigate')"
    >
      <component :is="item.icon" :size="17" :stroke-width="1.8" />
      <span>{{ item.label }}</span>
      <Kbd v-if="item.shortcut" :keys="item.shortcut" />
    </RouterLink>

    <span class="readout mobile-nav__label">LAB</span>

    <RouterLink
      v-for="item in LAB_NAV"
      :key="item.id"
      :to="item.to"
      :class="['mobile-nav__item', isActive(item) && 'mobile-nav__item--active']"
      @click="emit('navigate')"
    >
      <component :is="item.icon" :size="17" :stroke-width="1.8" />
      <span>{{ item.label }}</span>
    </RouterLink>

    <div class="mobile-nav__sep" />

    <button type="button" class="mobile-nav__item" @click="openImport">
      <Upload :size="17" :stroke-width="1.8" />
      <span>导入</span>
    </button>
    <button type="button" class="mobile-nav__item" @click="themeStore.toggle()">
      <Sun v-if="themeStore.isDark" :size="17" :stroke-width="1.8" />
      <Moon v-else :size="17" :stroke-width="1.8" />
      <span>{{ themeStore.isDark ? '切换浅色' : '切换深色' }}</span>
    </button>
    <button type="button" class="mobile-nav__item mobile-nav__item--danger" @click="logout">
      <LogOut :size="17" :stroke-width="1.8" />
      <span>退出登录</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { LogOut, Moon, Sun, Upload } from 'lucide-vue-next'
import Kbd from '@/components/ui/Kbd.vue'
import { LAB_NAV, PRIMARY_NAV, type NavItem } from '@/config/nav'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useImportStore } from '@/stores/import'

const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const importStore = useImportStore()

const ACTIVE_NAMES: Record<string, string[]> = {
  '/': ['Home'],
  '/library': ['Library', 'LibraryDetail', 'NewNote', 'NoteEditor', 'NewContent', 'ContentEditor'],
  '/graph': ['Graph'],
  '/ai': ['AIAssistant'],
  '/lab': ['PromptLab'],
  '/skills': ['Skills'],
  '/prompts': ['Prompts'],
  '/ai/observability': ['AgentObservability']
}

function isActive(item: NavItem) {
  return (ACTIVE_NAMES[item.to] ?? []).includes(String(route.name))
}

function openImport() {
  importStore.openImportModal()
  emit('navigate')
}

function logout() {
  authStore.logout()
  emit('navigate')
  router.push('/login')
}
</script>

<style scoped>
.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mobile-nav__item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 8px;
  border-radius: var(--r-md);
  font-size: 13px;
  color: var(--t2);
  text-align: left;
}

.mobile-nav__item span {
  flex: 1;
}

.mobile-nav__item:hover {
  background: var(--panel-2);
  color: var(--text);
}

.mobile-nav__item--active {
  color: var(--gold);
  background: var(--gold-soft);
}

.mobile-nav__item--danger {
  color: var(--danger);
}

.mobile-nav__label {
  margin: 14px 0 4px;
  padding-left: 8px;
  font-size: 9px;
}

.mobile-nav__sep {
  height: 1px;
  margin: 12px 8px;
  background: var(--line);
}
</style>
