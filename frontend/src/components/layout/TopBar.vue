<template>
  <header class="topbar">
    <button type="button" class="topbar__menu" aria-label="打开导航" @click="emit('open-menu')">
      <Menu :size="18" :stroke-width="1.8" />
    </button>

    <div class="topbar__heading">
      <span class="readout topbar__kicker">{{ meta.kicker }}</span>
      <h1 class="topbar__title">{{ meta.title }}</h1>
    </div>

    <div class="topbar__right">
      <button type="button" class="topbar__search" aria-label="搜索与命令" @click="command.open()">
        <Search :size="15" :stroke-width="1.8" />
        <span class="topbar__search-label">搜索</span>
        <Kbd keys="⌘ K" class="topbar__kbd" />
      </button>

      <template v-if="shellStore.actions.value.length">
        <AppButton
          v-for="action in shellStore.actions.value"
          :key="action.id"
          :variant="action.variant ?? 'secondary'"
          size="sm"
          @click="action.run"
        >
          <template v-if="action.icon" #icon>
            <component :is="action.icon" :size="14" />
          </template>
          {{ action.label }}
        </AppButton>
      </template>

      <AppButton v-else-if="showNewNote" size="sm" @click="router.push('/notes/new')">
        <template #icon><Plus :size="14" /></template>
        新建笔记
      </AppButton>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu, Plus, Search } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import Kbd from '@/components/ui/Kbd.vue'
import { pageMetaOf } from '@/config/nav'
import { useCommandPalette } from '@/lib/command'
import { useShellStore } from '@/stores/shell'

const emit = defineEmits<{ 'open-menu': [] }>()

const route = useRoute()
const router = useRouter()
const command = useCommandPalette()
const shellStore = useShellStore()

const meta = computed(() => pageMetaOf(route.name))
const showNewNote = computed(() =>
  ['Home', 'Library', 'LibraryDetail'].includes(String(route.name))
)
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: var(--topbar-h);
  padding: 0 24px;
  border-bottom: 1px solid var(--line);
  background: var(--bg);
  flex: none;
  z-index: var(--z-sticky);
}

.topbar__menu {
  display: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--r-md);
  color: var(--t2);
}

.topbar__menu:hover {
  background: var(--panel-2);
  color: var(--text);
}

.topbar__heading {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.topbar__kicker {
  font-size: 9px;
  color: var(--t3);
}

.topbar__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--text);
  white-space: nowrap;
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.topbar__search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 8px 0 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  color: var(--t3);
  transition: border-color var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out);
}

.topbar__search:hover {
  border-color: var(--line-strong);
  color: var(--t2);
}

.topbar__search-label {
  font-size: 12px;
}

.topbar__kbd {
  color: var(--t3);
}

@media (max-width: 767px) {
  .topbar {
    padding: 0 14px;
  }

  .topbar__menu {
    display: inline-flex;
  }

  .topbar__kicker {
    display: none;
  }

  .topbar__search-label {
    display: none;
  }
}
</style>
