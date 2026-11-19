<template>
  <div class="shell">
    <AppRail />

    <div class="shell__body">
      <TopBar @open-menu="mobileOpen = true" />

      <main class="shell__content">
        <div class="shell__atmosphere" aria-hidden="true">
          <div class="shell__grid" />
          <StarField :density="26" static />
        </div>

        <div class="shell__view">
          <ErrorBoundary>
            <RouterView v-slot="{ Component, route: current }">
              <Transition :name="transitionName" mode="out-in">
                <component :is="Component" :key="current.path" />
              </Transition>
            </RouterView>
          </ErrorBoundary>
        </div>
      </main>
    </div>

    <AppDrawer
      v-model:open="mobileOpen"
      side="left"
      title="导航"
      kicker="STAR ATLAS"
      :width="300"
    >
      <MobileNav @navigate="mobileOpen = false" />
    </AppDrawer>

    <CommandHost />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppRail from './AppRail.vue'
import TopBar from './TopBar.vue'
import MobileNav from './MobileNav.vue'
import CommandHost from './CommandHost.vue'
import AppDrawer from '@/components/ui/AppDrawer.vue'
import ErrorBoundary from '@/components/ui/ErrorBoundary.vue'
import StarField from '@/components/domain/StarField.vue'
import { useAuthStore } from '@/stores/auth'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import { useNotesStore } from '@/stores/notes'
import { pageMetaOf } from '@/config/nav'
import { installShellShortcuts } from '@/lib/command'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()
const notesStore = useNotesStore()

const mobileOpen = ref(false)
const transitionName = ref('page-rise')
let previousGroup: string | null = null
let disposeShortcuts: (() => void) | null = null

watch(
  () => route.fullPath,
  () => {
    const group = pageMetaOf(route.name).group
    transitionName.value = previousGroup !== null && previousGroup === group ? 'page-fade' : 'page-rise'
    previousGroup = group
  },
  { immediate: true }
)

onMounted(async () => {
  disposeShortcuts = installShellShortcuts((path) => router.push(path))
  await authStore.fetchUser()
  await foldersStore.fetchFolders()
  await tagsStore.fetchTags()
  await notesStore.fetchNotes()
})

onBeforeUnmount(() => {
  disposeShortcuts?.()
})
</script>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  background: var(--bg);
  color: var(--text);
  overflow: hidden;
}

.shell__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.shell__content {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.shell__atmosphere {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.shell__grid {
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(to right, var(--grid-line) 0 1px, transparent 1px 140px),
    repeating-linear-gradient(to bottom, var(--grid-line) 0 1px, transparent 1px 140px);
}

.shell__view {
  position: relative;
  z-index: 1;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>

<style>
.page-rise-enter-active,
.page-rise-leave-active,
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 240ms var(--ease-out), transform 240ms var(--ease-out);
}

.page-rise-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-rise-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
  transform: none;
}
</style>
