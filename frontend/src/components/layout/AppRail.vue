<template>
  <aside class="rail">
    <RouterLink to="/" class="rail__logo" aria-label="回到观测台">
      <BrandMark />
    </RouterLink>

    <AppTooltip content="搜索与命令" shortcut="⌘ K" side="right">
      <button type="button" class="rail__action" aria-label="搜索与命令" @click="command.open()">
        <Search :size="17" :stroke-width="1.8" />
      </button>
    </AppTooltip>

    <div class="rail__divider" />

    <nav class="rail__nav" aria-label="主导航">
      <AppTooltip
        v-for="item in PRIMARY_NAV"
        :key="item.id"
        :content="item.label"
        :shortcut="item.shortcut"
        side="right"
      >
        <RouterLink
          :to="item.to"
          :class="['rail__item', isActive(item) && 'rail__item--active']"
          :aria-current="isActive(item) ? 'page' : undefined"
          :aria-label="item.label"
        >
          <span class="rail__dot" aria-hidden="true" />
          <component :is="item.icon" :size="18" :stroke-width="1.8" />
        </RouterLink>
      </AppTooltip>
    </nav>

    <span class="readout rail__label">LAB</span>

    <nav class="rail__nav" aria-label="实验室">
      <AppTooltip
        v-for="item in LAB_NAV"
        :key="item.id"
        :content="item.label"
        :shortcut="item.shortcut"
        side="right"
      >
        <RouterLink
          :to="item.to"
          :class="['rail__item', isActive(item) && 'rail__item--active']"
          :aria-current="isActive(item) ? 'page' : undefined"
          :aria-label="item.label"
        >
          <span class="rail__dot" aria-hidden="true" />
          <component :is="item.icon" :size="17" :stroke-width="1.8" />
        </RouterLink>
      </AppTooltip>
    </nav>

    <div class="rail__spacer" />

    <div class="rail__divider" />

    <AppTooltip content="导入" shortcut="⌘ I" side="right">
      <button type="button" class="rail__action" aria-label="导入" @click="importStore.openImportModal()">
        <Upload :size="17" :stroke-width="1.8" />
      </button>
    </AppTooltip>

    <AppTooltip :content="themeStore.isDark ? '切换浅色' : '切换深色'" side="right">
      <button type="button" class="rail__action" :aria-label="themeStore.isDark ? '切换浅色' : '切换深色'" @click="themeStore.toggle()">
        <Sun v-if="themeStore.isDark" :size="17" :stroke-width="1.8" />
        <Moon v-else :size="17" :stroke-width="1.8" />
      </button>
    </AppTooltip>

    <DropdownMenuRoot>
      <DropdownMenuTrigger class="rail__avatar" aria-label="用户菜单">
        <AppAvatar :name="authStore.user?.username || 'ZS'" size="sm" />
      </DropdownMenuTrigger>
      <DropdownMenuPortal>
        <DropdownMenuContent class="zs-menu" side="right" :side-offset="8" align="end">
          <DropdownMenuLabel class="zs-menu__label">
            {{ authStore.user?.username || '未登录' }}
          </DropdownMenuLabel>
          <DropdownMenuSeparator class="zs-menu__sep" />
          <DropdownMenuItem class="zs-menu__item" @select="router.push('/import-history')">
            <History :size="14" /> 导入历史
          </DropdownMenuItem>
          <DropdownMenuItem class="zs-menu__item" @select="themeStore.toggle()">
            <Sun v-if="themeStore.isDark" :size="14" /><Moon v-else :size="14" />
            切换主题
          </DropdownMenuItem>
          <DropdownMenuSeparator class="zs-menu__sep" />
          <DropdownMenuItem class="zs-menu__item zs-menu__item--danger" @select="logout">
            <LogOut :size="14" /> 退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenuRoot>
  </aside>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from 'reka-ui'
import { History, LogOut, Moon, Search, Sun, Upload } from 'lucide-vue-next'
import BrandMark from './BrandMark.vue'
import AppTooltip from '@/components/ui/AppTooltip.vue'
import AppAvatar from '@/components/ui/AppAvatar.vue'
import { LAB_NAV, PRIMARY_NAV, type NavItem } from '@/config/nav'
import { useCommandPalette } from '@/lib/command'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useImportStore } from '@/stores/import'

const route = useRoute()
const router = useRouter()
const command = useCommandPalette()
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

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: var(--rail-w);
  padding: 14px 0 16px;
  background: var(--bg);
  border-right: 1px solid var(--line);
  flex: none;
  z-index: var(--z-rail);
}

.rail__logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-bottom: 10px;
  color: var(--gold);
  transition: transform 500ms var(--ease-out);
}

.rail__logo:hover {
  transform: rotate(90deg);
}

.rail__action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--r-md);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background-color var(--d-fast) var(--ease-out);
}

.rail__action:hover {
  color: var(--text);
  background: var(--panel-2);
}

.rail__divider {
  width: 20px;
  height: 1px;
  margin: 8px 0;
  background: var(--line);
}

.rail__nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.rail__label {
  margin: 12px 0 4px;
  font-size: 8px;
  letter-spacing: 0.18em;
  color: var(--t3);
}

.rail__item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--r-md);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background-color var(--d-fast) var(--ease-out);
}

.rail__item:hover {
  color: var(--t2);
  background: var(--panel-2);
}

.rail__item--active {
  color: var(--gold);
  background: var(--gold-soft);
}

.rail__dot {
  position: absolute;
  left: -17px;
  top: 50%;
  width: 4px;
  height: 4px;
  margin-top: -2px;
  border-radius: 50%;
  background: transparent;
  transition: background-color var(--d-fast) var(--ease-out);
}

.rail__item--active .rail__dot {
  background: var(--gold);
}

.rail__spacer {
  flex: 1;
}

.rail__avatar {
  margin-top: 6px;
  border-radius: 50%;
  transition: transform var(--d-fast) var(--ease-out);
}

.rail__avatar:hover {
  transform: translateY(-1px);
}

@media (max-width: 767px) {
  .rail {
    display: none;
  }
}
</style>

<style>
.zs-menu {
  z-index: var(--z-toast);
  min-width: 170px;
  padding: 4px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-float);
}

.zs-menu__label {
  padding: 6px 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--t3);
}

.zs-menu__sep {
  height: 1px;
  margin: 4px 6px;
  background: var(--line);
}

.zs-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  font-size: 12px;
  color: var(--t2);
  cursor: pointer;
  outline: none;
}

.zs-menu__item[data-highlighted] {
  background: var(--panel-2);
  color: var(--gold);
}

.zs-menu__item--danger {
  color: var(--danger);
}

.zs-menu__item--danger[data-highlighted] {
  background: var(--danger-soft);
  color: var(--danger);
}
</style>
