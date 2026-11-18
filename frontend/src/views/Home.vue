<template>
  <div class="home">
    <div class="outline-word home__outline" aria-hidden="true">OBSERVATORY</div>

    <div class="home__inner">
      <section class="hero">
        <div class="hero__text">
          <h1 class="hero__title">
            {{ greeting }}，{{ displayName }}。<br />
            <span class="hero__title-muted">{{ greetingLine }}</span>
          </h1>

          <p class="hero__lede">
            你的知识库并不沉默。{{ stats.notes }} 篇笔记正在等待下一次连接、一次提问，或一条被重新看见的线索。
          </p>

          <div class="hero__actions">
            <AppButton size="md" @click="router.push('/notes/new')">
              <template #icon><Plus :size="14" /></template>
              新建一条思考
            </AppButton>
            <RouterLink to="/ai" class="hero__link">向知识库提问 →</RouterLink>
          </div>
        </div>

        <ConstellationArt variant="hero" :width="380" :height="210" class="hero__art" />
      </section>

      <section class="continue">
        <header class="section-head">
          <span class="readout">CONTINUE · 继续阅读</span>
          <RouterLink to="/library" class="section-head__link">全部笔记 →</RouterLink>
        </header>

        <Skeleton v-if="loading" :lines="2" :height="18" />

        <RouterLink
          v-else-if="continueItem"
          :to="`/notes/${continueItem.id}`"
          class="continue__item"
        >
          <span class="readout continue__index">01</span>
          <div class="continue__body">
            <h2 class="continue__title">{{ continueItem.title }}</h2>
            <p class="continue__meta">{{ continueItem.meta }}</p>
            <p v-if="continueItem.excerpt" class="continue__excerpt">{{ continueItem.excerpt }}</p>
          </div>
          <ArrowRight :size="18" class="continue__arrow" />
        </RouterLink>

        <EmptyState
          v-else
          title="还没有航行记录"
          description="写下第一条思考，或从最近笔记里挑一篇开始。"
        >
          <AppButton size="sm" @click="router.push('/notes/new')">新建笔记</AppButton>
        </EmptyState>
      </section>

      <section class="recent">
        <header class="section-head">
          <span class="readout">RECENT · 最近编辑</span>
          <RouterLink to="/library" class="section-head__link">查看全部 →</RouterLink>
        </header>

        <div v-if="loading" class="recent__list">
          <Skeleton v-for="index in 5" :key="index" :height="16" />
        </div>

        <p v-else-if="!recentNotes.length" class="recent__empty">还没有笔记。新建一条，让星图开始生长。</p>

        <div v-else class="recent__list">
          <RouterLink
            v-for="note in recentNotes"
            :key="note.id"
            :to="`/notes/${note.id}`"
            class="recent__row"
          >
            <span class="recent__title">{{ note.title }}</span>
            <span class="recent__meta">
              {{ relativeTime(note.updated_at) }}
              <span v-if="note.link_count"> · {{ note.link_count }} LINKS</span>
            </span>
          </RouterLink>
        </div>

        <div class="stats">
          <span class="stats__item"><b class="num">{{ stats.notes }}</b> 篇笔记</span>
          <span class="stats__item"><b class="num">{{ stats.tags }}</b> 个标签</span>
          <span class="stats__item"><b class="num">{{ stats.links }}</b> 条连接</span>
        </div>
      </section>

      <aside class="side">
        <section class="side__block">
          <span class="readout">STAR CHART · 星图总览</span>
          <svg class="side__chart" viewBox="0 0 240 150" aria-hidden="true">
            <g class="side__orbit-group">
              <ellipse cx="120" cy="76" rx="88" ry="34" />
              <ellipse cx="120" cy="76" rx="62" ry="24" transform="rotate(-18 120 76)" />
              <ellipse cx="120" cy="76" rx="42" ry="16" transform="rotate(24 120 76)" />
            </g>
            <circle cx="120" cy="76" r="2.6" class="side__core" />
            <circle cx="196" cy="66" r="2.2" class="side__star side__star--gold" />
            <circle cx="74" cy="96" r="1.8" class="side__star" />
            <circle cx="148" cy="52" r="1.6" class="side__star" />
            <circle cx="46" cy="62" r="1.4" class="side__star" />
            <text x="202" y="60" class="side__code">ZS·044</text>
            <text x="150" y="46" class="side__code">ZS·118</text>
          </svg>
          <RouterLink to="/graph" class="side__link">进入图谱 →</RouterLink>
        </section>

        <section class="side__block">
          <span class="readout">AGENT · AI 助手</span>
          <h3 class="side__title">向你的知识库提问</h3>
          <p class="side__desc">多轮记忆 · 工具调用 · 三查反思 · 人工审批</p>
          <RouterLink to="/ai" class="side__link">开始对话 →</RouterLink>
        </section>

        <section class="side__block side__block--areas">
          <span class="readout">AREAS · 分区</span>
          <RouterLink
            v-for="area in areas"
            :key="area.id"
            :to="`/library/${area.id}`"
            class="side__area"
          >
            <span class="side__area-name">{{ area.name }}</span>
            <span class="readout side__area-label">{{ areaLabel(area.name) }}</span>
            <span class="num side__area-count">{{ area.note_count }}</span>
          </RouterLink>
          <p v-if="!areas.length && !loading" class="side__desc">还没有分区。</p>
        </section>

        <p v-if="degraded" class="side__degraded">首页聚合暂不可用，已降级显示最近笔记。</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Plus } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import ConstellationArt from '@/components/domain/ConstellationArt.vue'
import { homeApi } from '@/api/home'
import { notesApi } from '@/api/notes'
import { useAuthStore } from '@/stores/auth'
import { relativeTime } from '@/lib/time'
import type { HomeArea, HomeOverview, HomeRecentNote } from '@/types/home'

const router = useRouter()
const authStore = useAuthStore()

const overview = ref<HomeOverview | null>(null)
const loading = ref(true)
const degraded = ref(false)

const stats = computed(
  () =>
    overview.value?.stats ?? {
      notes: 0,
      tags: 0,
      folders: 0,
      categories: 0,
      words: 0,
      links: 0
    }
)

const displayName = computed(() => authStore.user?.username || '观测员')
const areas = computed<HomeArea[]>(() => overview.value?.areas ?? [])
const recentNotes = computed<HomeRecentNote[]>(() => overview.value?.recent_notes ?? [])

const hour = new Date().getHours()
const greeting = computed(() => {
  if (hour < 5) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '午间好'
  if (hour < 18) return '下午好'
  return '晚上好'
})
const greetingLine = computed(() => {
  if (hour < 5) return '星空仍然亮着。'
  if (hour < 11) return '开始今天的观测。'
  if (hour < 14) return '整理上午的坐标。'
  return '继续你的巡夜。'
})

const continueItem = computed(() => {
  const read = overview.value?.recent_reads?.[0]
  if (read) {
    return {
      id: read.note_id,
      title: read.title,
      meta: `上次阅读 · ${relativeTime(read.viewed_at)}`,
      excerpt: read.excerpt
    }
  }
  const first = recentNotes.value[0]
  if (first) {
    return {
      id: first.id,
      title: first.title,
      meta: `最近编辑 · ${relativeTime(first.updated_at)}`,
      excerpt: first.excerpt
    }
  }
  return null
})

const AREA_LABELS: Record<string, string> = {
  个人: 'PERSONAL',
  工作: 'WORK',
  素材: 'ASSETS'
}

function areaLabel(name: string) {
  return AREA_LABELS[name] ?? 'AREA'
}

async function load() {
  loading.value = true
  try {
    const response = await homeApi.overview()
    if (response.data) overview.value = response.data
  } catch {
    degraded.value = true
    await fallback()
  } finally {
    loading.value = false
  }
}

async function fallback() {
  try {
    const response = await notesApi.list({ page_size: 5 })
    const items = response.data?.items ?? []
    overview.value = {
      stats: {
        notes: response.data?.total ?? items.length,
        tags: 0,
        folders: 0,
        categories: 0,
        words: 0,
        links: 0
      },
      recent_notes: items.map((note) => ({
        id: note.id,
        title: note.title,
        excerpt: (note.content ?? '').replace(/\s+/g, ' ').slice(0, 80),
        updated_at: note.updated_at,
        folder_id: note.folder_id ?? null,
        category_id: null,
        link_count: note.linked_note_ids?.length ?? 0
      })),
      recent_reads: [],
      top_tags: [],
      areas: []
    }
  } catch {
    overview.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.home {
  position: relative;
  min-height: 100%;
}

.home__outline {
  top: 52px;
  right: -40px;
  font-size: clamp(110px, 14vw, 220px);
  opacity: 0.35;
  z-index: 0;
}

.home__inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  padding: 44px 40px 64px;
}

.hero {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 40px;
  padding-bottom: 40px;
}

.hero__text {
  max-width: 640px;
}

.hero__title {
  font-family: var(--font-display);
  font-size: clamp(36px, 4.2vw, 56px);
  font-weight: 500;
  line-height: 1.12;
  letter-spacing: -0.04em;
}

.hero__title-muted {
  color: var(--t3);
}

.hero__lede {
  margin-top: 18px;
  max-width: 420px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--t2);
}

.hero__actions {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 24px;
}

.hero__link {
  font-size: 12px;
  color: var(--t2);
  transition: color var(--d-fast) var(--ease-out), transform var(--d-fast) var(--ease-out);
}

.hero__link:hover {
  color: var(--gold);
  transform: translateX(4px);
}

.hero__art {
  flex: none;
  margin-top: 6px;
  opacity: 0.9;
}

.continue {
  padding: 22px 0 26px;
  border-top: 1px solid var(--line);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.section-head__link {
  font-size: 11px;
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.section-head__link:hover {
  color: var(--gold);
}

.continue__item {
  display: grid;
  grid-template-columns: 52px 1fr 32px;
  align-items: center;
  gap: 16px;
  padding: 10px 0;
  transition: transform var(--d-base) var(--ease-out);
}

.continue__item:hover {
  transform: translateX(6px);
}

.continue__index {
  color: var(--gold);
}

.continue__title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 500;
  letter-spacing: -0.03em;
  color: var(--text);
  transition: color var(--d-fast) var(--ease-out);
}

.continue__item:hover .continue__title {
  color: var(--gold);
}

.continue__meta {
  margin-top: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.continue__excerpt {
  margin-top: 4px;
  max-width: 560px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--t3);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.continue__arrow {
  color: var(--t3);
  transition: transform var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out);
}

.continue__item:hover .continue__arrow {
  color: var(--gold);
  transform: translateX(4px);
}

.recent {
  padding-top: 8px;
}

.recent__list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--line);
}

.recent__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  height: 42px;
  border-bottom: 1px solid var(--line);
  transition: transform var(--d-base) var(--ease-out);
}

.recent__row:hover {
  transform: translateX(5px);
}

.recent__title {
  font-size: 13px;
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--d-fast) var(--ease-out);
}

.recent__row:hover .recent__title {
  color: var(--gold);
}

.recent__meta {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
  flex: none;
}

.recent__empty {
  padding: 18px 0;
  font-size: 12px;
  color: var(--t3);
}

.stats {
  display: flex;
  align-items: baseline;
  gap: 28px;
  margin-top: 22px;
}

.stats__item {
  font-size: 11px;
  color: var(--t3);
}

.stats__item b {
  margin-right: 4px;
  font-size: 15px;
  font-weight: 500;
  color: var(--gold);
}

.side {
  border-left: 1px solid var(--line);
  padding-left: 28px;
}

.side__block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--line);
}

.side__block + .side__block {
  padding-top: 22px;
}

.side__block--areas {
  border-bottom: 0;
}

.side__chart {
  width: 100%;
  height: auto;
  max-width: 240px;
}

.side__orbit-group {
  fill: none;
  stroke: var(--line-strong);
  stroke-width: 0.8;
  transform-origin: 120px 76px;
  animation: orbit-spin 80s linear infinite;
  transform-box: view-box;
}

.side__core {
  fill: var(--text);
}

.side__star {
  fill: var(--t2);
}

.side__star--gold {
  fill: var(--gold);
}

.side__code {
  font-family: var(--font-mono);
  font-size: 6px;
  letter-spacing: 0.1em;
  fill: var(--t3);
}

.side__link {
  font-size: 11px;
  color: var(--gold);
  transition: transform var(--d-fast) var(--ease-out);
  align-self: flex-start;
}

.side__link:hover {
  transform: translateX(4px);
}

.side__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.side__desc {
  font-size: 11px;
  line-height: 1.6;
  color: var(--t3);
}

.side__area {
  display: grid;
  grid-template-columns: 1fr auto 34px;
  align-items: baseline;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
  transition: transform var(--d-base) var(--ease-out);
}

.side__area:hover {
  transform: translateX(4px);
}

.side__area-name {
  font-size: 13px;
  color: var(--t2);
}

.side__area-label {
  font-size: 8px;
}

.side__area-count {
  text-align: right;
  font-size: 12px;
  color: var(--gold);
}

.side__degraded {
  margin-top: 12px;
  font-size: 10px;
  line-height: 1.6;
  color: var(--danger);
}

@keyframes orbit-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (min-width: 1024px) {
  .home__inner {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    grid-template-areas:
      'hero hero'
      'main side';
    column-gap: 36px;
  }

  .hero {
    grid-area: hero;
  }

  .continue,
  .recent {
    grid-column: 1;
  }

  .side {
    grid-area: side;
    grid-row: 2 / span 2;
  }
}

@media (max-width: 1023px) {
  .home__inner {
    padding: 32px 24px 48px;
  }

  .hero__art {
    display: none;
  }

  .side {
    margin-top: 32px;
    padding-left: 0;
    border-left: 0;
    border-top: 1px solid var(--line);
    padding-top: 24px;
  }
}

@media (max-width: 767px) {
  .home__inner {
    padding: 24px 16px 40px;
  }

  .continue__title {
    font-size: 20px;
  }

  .continue__meta {
    white-space: normal;
  }

  .continue__excerpt {
    -webkit-line-clamp: 2;
  }

  .stats {
    gap: 16px;
    flex-wrap: wrap;
  }
}
</style>
