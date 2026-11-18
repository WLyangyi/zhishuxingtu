<template>
  <div class="search">
    <div class="search__inner">
      <header class="search__head">
        <span class="readout">SEARCH · 全局搜索</span>

        <div class="search__input-wrap">
          <Search :size="18" :stroke-width="1.8" class="search__icon" />
          <input
            ref="inputRef"
            v-model="query"
            class="search__input"
            type="text"
            placeholder="搜索标题、正文、标签或 [[双链]]…"
            aria-label="全局搜索"
            @keydown.esc="query = ''"
          />
          <Kbd keys="ESC" />
        </div>
      </header>

      <nav v-if="query.trim()" class="search__tabs" aria-label="结果类型">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          :class="['search__tab', filter === tab.value && 'search__tab--active']"
          @click="filter = tab.value"
        >
          {{ tab.label }}
          <span class="num search__tab-count">{{ tab.count }}</span>
        </button>
      </nav>

      <div v-if="loading" class="search__skeleton">
        <Skeleton v-for="index in 5" :key="index" :height="16" />
      </div>

      <div v-else-if="!query.trim()" class="search__start">
        <Search :size="30" :stroke-width="1.4" class="search__start-icon" />
        <h1 class="search__start-title">搜索你的知识库</h1>
        <p class="search__start-desc">标题、正文、标签与双链，一次搜完。输入关键词开始。</p>
        <div class="search__tips">
          <span><code>#标签</code> 定位标签</span>
          <span><code>[[标题]]</code> 查双链</span>
          <span><Kbd keys="ESC" /> 清空</span>
        </div>
      </div>

      <div v-else-if="!total" class="search__state">
        <EmptyState
          title="没有找到结果"
          :description="`没有与「${query.trim()}」匹配的笔记、标签或链接。`"
        >
          <AppButton size="sm" variant="secondary" @click="askAi">向 AI 提问</AppButton>
        </EmptyState>
      </div>

      <div v-else class="search__results">
        <section v-if="showNotes && noteHits.length" class="search__group">
          <header class="search__group-head">
            <span class="readout">NOTES · 笔记</span>
            <span class="num">{{ noteHits.length }}</span>
          </header>

          <RouterLink
            v-for="note in noteHits"
            :key="note.id"
            :to="`/notes/${note.id}`"
            class="hit"
          >
            <div class="hit__main">
              <h2 class="hit__title" v-html="highlightHtml(note.title, query)" />
              <p class="hit__excerpt" v-html="highlightHtml(excerptOf(note), query)" />
            </div>
            <span class="readout hit__meta">
              {{ folderName(note) }} · {{ relativeTime(note.updated_at) }}
            </span>
          </RouterLink>
        </section>

        <section v-if="showTags && tagHits.length" class="search__group">
          <header class="search__group-head">
            <span class="readout">TAGS · 标签</span>
            <span class="num">{{ tagHits.length }}</span>
          </header>

          <button
            v-for="tag in tagHits"
            :key="tag.id"
            type="button"
            class="hit"
            @click="router.push({ path: '/library', query: { tag: tag.id } })"
          >
            <div class="hit__main">
              <h2 class="hit__title" v-html="highlightHtml(`#${tag.name}`, query)" />
              <p class="hit__excerpt">{{ tag.count }} 篇笔记使用</p>
            </div>
            <span class="readout hit__meta">TAG</span>
          </button>
        </section>

        <section v-if="showLinks && linkHits.length" class="search__group">
          <header class="search__group-head">
            <span class="readout">LINKS · 双链</span>
            <span class="num">{{ linkHits.length }}</span>
          </header>

          <button
            v-for="hit in linkHits"
            :key="hit.title"
            type="button"
            class="hit"
            @click="openLink(hit)"
          >
            <div class="hit__main">
              <h2 class="hit__title" v-html="highlightHtml(`[[${hit.title}]]`, query)" />
              <p class="hit__excerpt">来自「{{ hit.sourceTitle }}」{{ hit.targetId ? ' · 目标笔记存在' : ' · 断链' }}</p>
            </div>
            <span class="readout hit__meta">{{ hit.targetId ? 'NOTE' : 'BROKEN' }}</span>
          </button>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Kbd from '@/components/ui/Kbd.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { notesApi } from '@/api/notes'
import { useFoldersStore } from '@/stores/folders'
import { flattenFolders, tagCounts } from '@/lib/library'
import {
  collectLinkHits,
  excerptAround,
  highlightHtml,
  matchNotes,
  type LinkHit
} from '@/lib/search'
import { relativeTime } from '@/lib/time'
import type { Note } from '@/types/note'

const route = useRoute()
const router = useRouter()
const foldersStore = useFoldersStore()

const inputRef = ref<HTMLInputElement | null>(null)
const allNotes = ref<Note[]>([])
const loading = ref(true)
const query = ref('')
const filter = ref<'all' | 'notes' | 'tags' | 'links'>('all')

const noteHits = computed(() => matchNotes(allNotes.value, query.value))
const tagHits = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return []
  return tagCounts(allNotes.value).filter((tag) => tag.name.toLowerCase().includes(keyword))
})
const linkHits = computed(() => collectLinkHits(allNotes.value, query.value))

const total = computed(() => noteHits.value.length + tagHits.value.length + linkHits.value.length)

const tabs = computed(() => [
  { label: '全部', value: 'all' as const, count: total.value },
  { label: '笔记', value: 'notes' as const, count: noteHits.value.length },
  { label: '标签', value: 'tags' as const, count: tagHits.value.length },
  { label: '链接', value: 'links' as const, count: linkHits.value.length }
])

const showNotes = computed(() => filter.value === 'all' || filter.value === 'notes')
const showTags = computed(() => filter.value === 'all' || filter.value === 'tags')
const showLinks = computed(() => filter.value === 'all' || filter.value === 'links')

const folderNames = computed(() => {
  const map = new Map<string, string>()
  for (const folder of flattenFolders(foldersStore.folders)) {
    map.set(folder.id, folder.name)
  }
  return map
})

function folderName(note: Note) {
  return (note.folder_id && folderNames.value.get(note.folder_id)) || '未归档'
}

function excerptOf(note: Note) {
  return excerptAround(note.content, query.value)
}

function openLink(hit: LinkHit) {
  router.push(`/notes/${hit.targetId ?? hit.sourceId}`)
}

function askAi() {
  router.push({ path: '/ai', query: { q: query.value.trim() } })
}

async function loadAllNotes() {
  loading.value = true
  try {
    const first = await notesApi.list({ page_size: 100, page: 1 })
    const items = [...first.data.items]
    const totalCount = first.data.total
    let page = 1

    while (items.length < totalCount && page < 5) {
      page += 1
      const next = await notesApi.list({ page_size: 100, page })
      items.push(...next.data.items)
    }

    allNotes.value = items
  } catch {
    allNotes.value = []
  } finally {
    loading.value = false
  }
}

function syncQuery() {
  const value = route.query.q
  query.value = typeof value === 'string' ? value : ''
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') query.value = ''
}

watch(() => route.query.q, syncQuery)

watch(query, (value) => {
  if (value.trim()) {
    router.replace({ path: '/search', query: { q: value.trim() } })
  } else {
    router.replace({ path: '/search' })
  }
})

onMounted(async () => {
  syncQuery()
  await Promise.allSettled([loadAllNotes(), foldersStore.fetchFolders()])
  inputRef.value?.focus()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.search {
  min-height: 100%;
  padding: 44px 32px 80px;
}

.search__inner {
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
}

.search__head {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.search__input-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0 12px;
  border-bottom: 1px solid var(--line-strong);
  transition: border-color var(--d-fast) var(--ease-out);
}

.search__input-wrap:focus-within {
  border-color: var(--gold);
}

.search__icon {
  color: var(--t3);
  flex: none;
}

.search__input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: 0;
  outline: none;
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 500;
  letter-spacing: -0.025em;
  color: var(--text);
}

.search__input::placeholder {
  font-size: 20px;
  color: var(--t3);
}

.search__tabs {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 26px;
  border-bottom: 1px solid var(--line);
}

.search__tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 0 10px;
  font-size: 12px;
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.search__tab:hover {
  color: var(--t2);
}

.search__tab--active {
  color: var(--gold);
}

.search__tab--active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: var(--gold);
}

.search__tab-count {
  font-size: 9px;
}

.search__skeleton {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 28px;
}

.search__start {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 90px 20px 40px;
  text-align: center;
}

.search__start-icon {
  color: var(--gold);
  margin-bottom: 16px;
}

.search__start-title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 500;
  letter-spacing: -0.03em;
}

.search__start-desc {
  margin-top: 8px;
  max-width: 380px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--t3);
}

.search__tips {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 24px;
  font-size: 11px;
  color: var(--t3);
}

.search__tips code {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--gold);
}

.search__state {
  padding-top: 30px;
}

.search__group {
  margin-top: 30px;
}

.search__group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

.search__group-head .num {
  font-size: 9px;
  color: var(--t3);
}

.hit {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 24px;
  width: 100%;
  padding: 14px 4px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  transition: transform var(--d-base) var(--ease-out),
    background-color var(--d-base) var(--ease-out);
}

.hit:hover {
  transform: translateX(5px);
  background: color-mix(in srgb, var(--panel) 45%, transparent);
}

.hit__main {
  min-width: 0;
}

.hit__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: -0.015em;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hit:hover .hit__title {
  color: var(--gold);
}

.hit__title :deep(mark),
.hit__excerpt :deep(mark) {
  background: transparent;
  color: var(--gold);
  border-bottom: 1px solid color-mix(in srgb, var(--gold) 65%, transparent);
}

.hit__excerpt {
  margin-top: 5px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hit__meta {
  font-size: 9px;
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.hit:hover .hit__meta {
  color: var(--t2);
}

@media (max-width: 767px) {
  .search {
    padding: 24px 16px 56px;
  }

  .search__input {
    font-size: 20px;
  }

  .search__input::placeholder {
    font-size: 15px;
  }

  .search__tabs {
    gap: 16px;
    overflow-x: auto;
  }

  .hit {
    grid-template-columns: minmax(0, 1fr);
    gap: 6px;
  }

  .hit__meta {
    text-align: left;
  }
}
</style>
