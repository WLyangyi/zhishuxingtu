<template>
  <div class="editor">
    <div class="editor__outline outline-word" aria-hidden="true">READ · OBSERVE</div>

    <div class="editor__bar">
      <Breadcrumb :items="breadcrumb" class="editor__breadcrumb" />

      <div class="editor__status">
        <span :class="['editor__dot', `editor__dot--${saveState}`]" aria-hidden="true" />
        <span class="editor__save-text">{{ saveText }}</span>
      </div>

      <span v-if="!isNew" class="readout editor__readout">{{ words.toLocaleString('zh-CN') }} 字</span>
      <span v-if="!isNew" class="readout editor__readout">{{ readTime }} MIN READ</span>

      <SegmentedControl
        :model-value="mode"
        :items="modeItems"
        size="sm"
        aria-label="编辑或预览"
        @update:model-value="setMode"
      />

      <button type="button" class="editor__props" @click="propsOpen = true">
        <SlidersHorizontal :size="14" :stroke-width="1.8" />
        属性
      </button>

      <AppButton v-if="isNew || saveState === 'error'" size="sm" @click="save(false)">保存</AppButton>
    </div>

    <div class="editor__layout">
      <main class="editor__main">
        <div ref="bodyRef" class="editor__body">
          <div v-if="loading" class="editor__loading">
            <Skeleton :lines="3" :height="18" />
            <Skeleton :lines="6" :height="12" />
          </div>

          <EmptyState v-else-if="notFound" title="笔记不存在" description="它可能已被删除，或链接失效。">
            <AppButton size="sm" @click="router.push('/library')">返回笔记库</AppButton>
          </EmptyState>

          <template v-else>
            <textarea
              ref="titleRef"
              v-model="title"
              class="editor__title"
              rows="1"
              placeholder="无标题"
              aria-label="笔记标题"
              @input="resizeTitle"
              @keydown="onTitleKeydown"
            />

            <div class="editor__meta">
              <span>NOTE</span>
              <span>·</span>
              <span>{{ outgoing.length }} LINKS</span>
              <span>·</span>
              <span>创建 {{ createdLabel }}</span>
              <span>·</span>
              <span>{{ readTime }} MIN READ</span>
            </div>

            <div class="editor__divider" />

            <div v-if="mode === 'edit'" class="editor__input-wrap">
              <div ref="mirrorRef" class="editor__mirror" aria-hidden="true"><span
                  v-for="(segment, index) in highlightSegments"
                  :key="index"
                  :class="segment.kind !== 'plain' && `editor__hl--${segment.kind}`"
                >{{ segment.text }}</span></div>
              <textarea
                ref="inputRef"
                v-model="content"
                class="editor__input"
                placeholder="开始编写…  输入 [[ 链接另一篇笔记"
                aria-label="笔记正文"
                @input="onInput"
                @click="onCaretMove"
                @keyup="onCaretMove"
                @keydown="onKeydown"
                @blur="onBlur"
              />
            </div>

            <article
              v-else
              class="prose"
              @click="onPreviewClick"
              v-html="renderedContent"
            />

            <div
              v-if="suggestion.open"
              class="wiki-pop"
              :style="{ left: `${suggestion.left}px`, top: `${suggestion.top}px` }"
            >
              <div class="wiki-pop__head readout">链接到笔记 · LINK TO NOTE</div>
              <button
                v-for="(item, index) in suggestion.items"
                :key="item.id"
                type="button"
                :class="['wiki-pop__item', index === suggestion.index && 'wiki-pop__item--active']"
                @mousedown.prevent="insertSuggestion(item)"
              >
                <FileText :size="12" :stroke-width="1.8" />
                <span class="wiki-pop__label">{{ item.title }}</span>
                <span class="readout">NOTE</span>
              </button>
              <div v-if="!suggestion.items.length" class="wiki-pop__empty">
                没有匹配的笔记，继续输入或 Esc 关闭。
              </div>
              <div class="wiki-pop__foot">↑↓ 选择 · Enter 插入 · Esc 关闭</div>
            </div>
          </template>
        </div>
      </main>

      <aside class="editor__rail">
        <section class="rail__block">
          <header class="rail__head">
            <span class="readout">出链 · OUTGOING</span>
            <span class="num">{{ outgoing.length }}</span>
          </header>
          <button
            v-for="link in outgoing"
            :key="link.title"
            type="button"
            :class="['rail__row', !link.note && 'rail__row--broken']"
            @click="link.note && router.push(`/notes/${link.note.id}`)"
          >
            <span class="rail__label">{{ link.title }}</span>
            <span class="readout">{{ link.note ? 'NOTE' : 'BROKEN' }}</span>
          </button>
          <p v-if="!outgoing.length" class="rail__empty">还没有双链。正文输入 [[ 开始。</p>
        </section>

        <section class="rail__block">
          <header class="rail__head">
            <span class="readout">入链 · BACKLINKS</span>
            <span class="num">{{ backlinks.length }}</span>
          </header>
          <button
            v-for="link in backlinks"
            :key="link.id"
            type="button"
            class="rail__row"
            @click="router.push(`/notes/${link.id}`)"
          >
            <span class="rail__label">{{ link.title }}</span>
            <span class="readout">NOTE</span>
          </button>
          <p v-if="!backlinks.length" class="rail__empty">还没有其他笔记引用它。</p>
        </section>
      </aside>
    </div>

    <AppModal v-model:open="propsOpen" title="笔记属性" size="sm">
      <div class="props">
        <AppSelect
          :model-value="folderId ?? ''"
          label="文件夹"
          placeholder="未归档"
          :options="folderOptions"
          @update:model-value="folderId = $event || null"
        />

        <div class="props__tags">
          <span class="readout">TAGS · 标签</span>
          <div class="props__tag-list">
            <button
              v-for="tag in allTags"
              :key="tag.id"
              type="button"
              :class="['props__tag', selectedTagIds.includes(tag.id) && 'props__tag--on']"
              @click="toggleTag(tag.id)"
            >
              #{{ tag.name }}
            </button>
            <span v-if="!allTags.length" class="props__empty">还没有标签。</span>
          </div>
        </div>
      </div>
      <template #footer>
        <AppButton size="sm" @click="propsOpen = false">完成</AppButton>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { FileText, SlidersHorizontal } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { notesApi } from '@/api/notes'
import { useCategoryStore } from '@/stores/category'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import { flattenFolders, folderPath } from '@/lib/library'
import {
  buildWikiHighlightSegments,
  detectWikiQuery,
  parseWikiLinks,
  readMinutes,
  renderWikiMarkup,
  suggestNotes,
  wordCount
} from '@/lib/editor'
import { reportNoteView } from '@/lib/readTracker'
import { parseServerTime } from '@/lib/time'
import type { Note } from '@/types/note'

interface Backlink {
  id: string
  title: string
  created_at: string
}

const route = useRoute()
const router = useRouter()
const categoryStore = useCategoryStore()
const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()

const titleRef = ref<HTMLTextAreaElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const mirrorRef = ref<HTMLElement | null>(null)
const highlightSegments = computed(() => buildWikiHighlightSegments(content.value))
const bodyRef = ref<HTMLDivElement | null>(null)

const title = ref('')
const content = ref('')
const folderId = ref<string | null>(null)
const selectedTagIds = ref<string[]>([])
const createdAt = ref('')
const backlinks = ref<Backlink[]>([])
const allNotes = ref<Note[]>([])

const loading = ref(true)
const notFound = ref(false)
const propsOpen = ref(false)
const mode = ref<'edit' | 'preview'>('edit')
const saveState = ref<'saved' | 'dirty' | 'saving' | 'unsaved' | 'error'>('saved')
const lastSaved = ref('')
const saveError = ref('')

const modeItems = [
  { label: '编辑', value: 'edit' },
  { label: '预览', value: 'preview' }
]

const suggestion = reactive({
  open: false,
  items: [] as Note[],
  index: 0,
  left: 0,
  top: 0,
  queryStart: 0,
  caret: 0
})

const md = new MarkdownIt({ html: true, linkify: true, typographer: true })

let saveTimer: ReturnType<typeof setTimeout> | undefined
let hydrating = false
let skipNextLoad = false

const noteId = computed(() => (route.params.id as string) || '')
const isNew = computed(() => route.name === 'NewNote' || noteId.value === 'new')
const words = computed(() => wordCount(content.value))
const readTime = computed(() => readMinutes(words.value))
const allTags = computed(() => tagsStore.tags)
const flatFolders = computed(() => flattenFolders(foldersStore.folders))

const notesByTitle = computed(() => new Map(allNotes.value.map((note) => [note.title.trim(), note])))

const outgoing = computed(() =>
  parseWikiLinks(content.value).map((titleText) => ({
    title: titleText,
    note: notesByTitle.value.get(titleText) ?? null
  }))
)

const folderOptions = computed(() => [
  { label: '未归档', value: '' },
  ...flatFolders.value.map((folder) => ({
    label: `${'　'.repeat(folder.level)}${folder.name}`,
    value: folder.id
  }))
])

const currentFolder = computed(() =>
  folderId.value ? flatFolders.value.find((folder) => folder.id === folderId.value) ?? null : null
)

const path = computed(() => (folderId.value ? folderPath(flatFolders.value, folderId.value) : []))

const breadcrumb = computed(() => {
  const items: Array<{ label: string; to?: string }> = [{ label: '我的笔记', to: '/library' }]

  if (currentFolder.value?.category_id) {
    const category = categoryStore.categories.find(
      (item) => item.id === currentFolder.value?.category_id
    )
    if (category) {
      items.push({ label: category.name, to: `/library/${category.id}` })
    }
  }

  path.value.forEach((folder) => {
    items.push({ label: folder.name })
  })

  items.push({ label: title.value.trim() || '未命名' })
  return items
})

const createdLabel = computed(() => {
  if (!createdAt.value) return '—'
  const date = parseServerTime(createdAt.value)
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
})

const saveText = computed(() => {
  if (saveState.value === 'saving') return '保存中…'
  if (saveState.value === 'dirty') return '未保存…'
  if (saveState.value === 'unsaved') return '未保存'
  if (saveState.value === 'error') return saveError.value || '保存失败'
  return lastSaved.value ? `已保存 ${lastSaved.value}` : '已保存'
})

const renderedContent = computed(() => {
  const markup = renderWikiMarkup(content.value || '', allNotes.value)
  return DOMPurify.sanitize(md.render(markup), { ADD_ATTR: ['target'] })
})

function resizeTitle() {
  const element = titleRef.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${element.scrollHeight}px`
}

function resizeInput() {
  const element = inputRef.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.max(element.scrollHeight, window.innerHeight * 0.5)}px`
}

function setMode(next: string) {
  mode.value = next === 'preview' ? 'preview' : 'edit'
  closeSuggestion()

  if (mode.value === 'preview' && saveState.value === 'dirty') {
    void save(true)
  }
  if (mode.value === 'edit') {
    nextTick(() => {
      resizeInput()
      inputRef.value?.focus()
    })
  }
}

function toggleTag(tagId: string) {
  if (selectedTagIds.value.includes(tagId)) {
    selectedTagIds.value = selectedTagIds.value.filter((id) => id !== tagId)
  } else {
    selectedTagIds.value = [...selectedTagIds.value, tagId]
  }
}

function nowLabel() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  if (isNew.value) return
  saveTimer = setTimeout(() => {
    void save(true)
  }, 900)
}

function markDirty() {
  if (hydrating) return
  saveState.value = isNew.value ? 'unsaved' : 'dirty'
  scheduleSave()
}

watch([title, content, folderId, selectedTagIds], markDirty, { deep: true })

async function save(auto: boolean) {
  if (saveState.value === 'saving') return

  if (!title.value.trim()) {
    if (!auto) {
      saveError.value = '请先填写标题'
      saveState.value = 'error'
    }
    return
  }

  const payload = {
    title: title.value.trim(),
    content: content.value,
    folder_id: folderId.value,
    tag_ids: selectedTagIds.value
  }

  saveState.value = 'saving'
  saveError.value = ''

  try {
    if (isNew.value) {
      const response = await notesApi.create(payload)
      skipNextLoad = true
      await router.replace(`/notes/${response.data.id}`)
      createdAt.value = response.data.created_at
    } else {
      await notesApi.update(noteId.value, payload)
    }

    saveState.value = 'saved'
    lastSaved.value = nowLabel()
  } catch {
    saveState.value = 'error'
    saveError.value = '保存失败，请重试'
  }
}

function onKeydown(event: KeyboardEvent) {
  if (!suggestion.open) return

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    suggestion.index = (suggestion.index + 1) % Math.max(1, suggestion.items.length)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    suggestion.index =
      (suggestion.index - 1 + suggestion.items.length) %
      Math.max(1, suggestion.items.length)
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    const item = suggestion.items[suggestion.index]
    if (item) insertSuggestion(item)
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    closeSuggestion()
  }
}

function onTitleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    inputRef.value?.focus()
  }
}

function updateSuggestions() {
  const element = inputRef.value
  if (!element || mode.value !== 'edit') {
    closeSuggestion()
    return
  }

  const caret = element.selectionStart
  const before = element.value.slice(0, caret)
  const found = detectWikiQuery(before)

  if (!found) {
    closeSuggestion()
    return
  }

  const items = suggestNotes(allNotes.value, found.query, isNew.value ? null : noteId.value)
  const coords = caretCoordinates(element, before)

  suggestion.open = true
  suggestion.items = items
  suggestion.index = 0
  suggestion.queryStart = found.start
  suggestion.caret = caret
  suggestion.left = coords.left
  suggestion.top = coords.top
}

function caretCoordinates(element: HTMLTextAreaElement, before: string) {
  const style = getComputedStyle(element)
  const lineHeight = parseFloat(style.lineHeight) || 26
  const paddingLeft = parseFloat(style.paddingLeft) || 0
  const paddingTop = parseFloat(style.paddingTop) || 0
  const bodyRect = bodyRef.value?.getBoundingClientRect()
  const rect = element.getBoundingClientRect()

  const lines = before.split('\n')
  const line = lines.length - 1
  const column = lines[line].length
  const charWidth = 7.8

  const rawLeft = paddingLeft + column * charWidth
  const maxLeft = Math.max(8, element.clientWidth - 280)
  const left = Math.min(rawLeft, maxLeft)
  const top = paddingTop + (line + 1) * lineHeight - element.scrollTop

  return {
    left: Math.max(8, left),
    top: Math.max(8, top + (bodyRect ? rect.top - bodyRect.top : 0))
  }
}

function insertSuggestion(item: Note) {
  const element = inputRef.value
  if (!element) return

  const caret = element.selectionStart
  const current = element.value
  const before = current.slice(0, suggestion.queryStart)
  const after = current.slice(caret)
  const inserted = `[[${item.title}]]`

  content.value = `${before}${inserted}${after}`
  closeSuggestion()

  nextTick(() => {
    element.focus()
    const position = before.length + inserted.length
    element.setSelectionRange(position, position)
    resizeInput()
  })
}

function closeSuggestion() {
  suggestion.open = false
  suggestion.items = []
  suggestion.index = 0
}

function onCaretMove() {
  updateSuggestions()
}

function onBlur() {
  setTimeout(closeSuggestion, 120)
}

function onInput() {
  resizeInput()
  updateSuggestions()
}

function onPreviewClick(event: MouseEvent) {
  const target = (event.target as HTMLElement).closest('a.wiki-link') as HTMLAnchorElement | null
  const targetId = target?.dataset.noteId
  if (targetId) {
    event.preventDefault()
    router.push(`/notes/${targetId}`)
  }
}

async function loadAllNotes() {
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

    allNotes.value = items
  } catch {
    allNotes.value = []
  }
}

async function loadNote() {
  hydrating = true
  loading.value = true
  notFound.value = false

  try {
    if (isNew.value) {
      title.value = ''
      content.value = ''
      folderId.value = (route.query.folder as string) || null
      selectedTagIds.value = []
      createdAt.value = ''
      backlinks.value = []
      mode.value = 'edit'
      saveState.value = 'unsaved'
      lastSaved.value = ''
      return
    }

    const response = await notesApi.get(noteId.value)
    const note = response.data
    title.value = note.title
    content.value = note.content || ''
    folderId.value = note.folder_id
    selectedTagIds.value = note.tags.map((tag) => tag.id)
    createdAt.value = note.created_at
    mode.value = 'preview'
    saveState.value = 'saved'
    lastSaved.value = parseServerTime(note.updated_at).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })

    const links = await notesApi.getBacklinks(noteId.value)
    backlinks.value = links.data

    reportNoteView(noteId.value)
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
    hydrating = false
    nextTick(() => {
      resizeTitle()
      resizeInput()
    })
  }
}

function onGlobalKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void save(false)
  }
}

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (['dirty', 'unsaved', 'saving'].includes(saveState.value)) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onBeforeRouteLeave(async () => {
  if (saveTimer) clearTimeout(saveTimer)
  if (!isNew.value && ['dirty', 'unsaved'].includes(saveState.value) && title.value.trim()) {
    await save(false)
  }
})

watch(
  () => route.params.id,
  async (next, previous) => {
    if (skipNextLoad) {
      skipNextLoad = false
      return
    }
    if (next !== previous) await loadNote()
  }
)

watch(
  () => route.name,
  async (next, previous) => {
    if (next === 'NewNote' && previous !== 'NewNote') await loadNote()
  }
)

onMounted(async () => {
  await Promise.allSettled([
    foldersStore.fetchFolders(),
    tagsStore.fetchTags(),
    categoryStore.fetchCategories(),
    loadAllNotes()
  ])
  await loadNote()
  window.addEventListener('keydown', onGlobalKeydown)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  if (saveTimer) clearTimeout(saveTimer)
  window.removeEventListener('keydown', onGlobalKeydown)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<style scoped>
.editor {
  position: relative;
  min-height: 100%;
}

.editor__outline {
  right: -30px;
  bottom: -40px;
  font-size: clamp(100px, 13vw, 200px);
  opacity: 0.28;
  pointer-events: none;
}

.editor__bar {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 46px;
  padding: 8px 28px;
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 92%, transparent);
  backdrop-filter: blur(8px);
}

.editor__breadcrumb {
  min-width: 0;
  flex: 1;
}

.editor__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.editor__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--t3);
}

.editor__dot--saved {
  background: var(--success);
}

.editor__dot--dirty,
.editor__dot--saving {
  background: var(--gold);
  animation: save-pulse 1.2s ease-in-out infinite;
}

.editor__dot--error {
  background: var(--danger);
}

.editor__save-text {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

.editor__readout {
  color: var(--t3);
  flex: none;
}

.editor__props {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  font-size: 11px;
  color: var(--t3);
  flex: none;
}

.editor__props:hover {
  color: var(--gold);
  background: var(--panel-2);
}

.editor__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 286px;
}

.editor__main {
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 34px 32px 90px;
}

.editor__body {
  position: relative;
  width: 100%;
  max-width: 660px;
}

.editor__loading {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding-top: 10px;
}

.editor__title {
  display: block;
  width: 100%;
  min-height: 44px;
  padding: 0;
  background: transparent;
  border: 0;
  outline: none;
  resize: none;
  overflow: hidden;
  font-family: var(--font-display);
  font-size: 38px;
  font-weight: 500;
  line-height: 1.18;
  letter-spacing: -0.035em;
  color: var(--text);
}

.editor__title::placeholder {
  color: var(--t3);
}

.editor__meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 14px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--t3);
}

.editor__divider {
  height: 1px;
  margin: 18px 0 24px;
  background: var(--line);
}

.editor__input-wrap {
  position: relative;
}

/* 镜像层：与正文 textarea 完全一致的排版度量，仅绘制高亮底色 */
.editor__mirror {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.95;
  color: transparent;
}

.editor__hl--wiki {
  background: var(--gold-soft);
  box-shadow: inset 0 -1px 0 var(--gold-line);
  border-radius: 2px;
}

.editor__hl--pending {
  background: var(--gold-soft);
  border-radius: 2px;
  opacity: 0.6;
}

.editor__input {
  position: relative;
  z-index: 1;
  display: block;
  width: 100%;
  min-height: 52vh;
  padding: 0;
  background: transparent;
  border: 0;
  outline: none;
  resize: none;
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.95;
  color: var(--t2);
  caret-color: var(--gold);
}

.editor__input::placeholder {
  color: var(--t3);
}

.editor__rail {
  align-self: start;
  position: sticky;
  top: 46px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 28px 20px 40px;
  border-left: 1px solid var(--line);
  max-height: calc(100vh - 46px);
  overflow-y: auto;
}

.rail__block {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.rail__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-bottom: 6px;
}

.rail__head .num {
  font-size: 9px;
  color: var(--t3);
}

.rail__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 28px;
  padding: 0 4px;
  border-radius: var(--r-sm);
  color: var(--t2);
  text-align: left;
}

.rail__row:hover {
  background: var(--panel-2);
  color: var(--gold);
}

.rail__row--broken {
  color: var(--danger);
}

.rail__label {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rail__empty {
  padding: 4px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--t3);
}

.wiki-pop {
  position: absolute;
  z-index: 5;
  width: 272px;
  padding: 4px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-float);
}

.wiki-pop__head {
  padding: 6px 8px;
  font-size: 8.5px;
  color: var(--t3);
}

.wiki-pop__item {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 30px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  color: var(--t2);
  text-align: left;
}

.wiki-pop__item:hover,
.wiki-pop__item--active {
  background: var(--panel-2);
  color: var(--gold);
}

.wiki-pop__label {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wiki-pop__empty {
  padding: 8px;
  font-size: 11px;
  color: var(--t3);
}

.wiki-pop__foot {
  padding: 7px 8px 3px;
  margin-top: 4px;
  border-top: 1px solid var(--line);
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.03em;
  color: var(--t3);
}

.props {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 4px 0 8px;
}

.props__tags {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.props__tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.props__tag {
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--t3);
}

.props__tag:hover {
  border-color: var(--line-strong);
  color: var(--t2);
}

.props__tag--on {
  border-color: var(--gold);
  color: var(--gold);
  background: var(--gold-soft);
}

.props__empty {
  font-size: 11px;
  color: var(--t3);
}

.prose {
  font-size: 15px;
  line-height: 1.9;
  color: var(--t2);
}

.prose :deep(h1),
.prose :deep(h2),
.prose :deep(h3) {
  margin: 1.6em 0 0.7em;
  font-family: var(--font-display);
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--gold);
}

.prose :deep(h1)::before {
  content: '# ';
  font-family: var(--font-mono);
  font-size: 0.72em;
  opacity: 0.7;
}

.prose :deep(h2)::before {
  content: '## ';
  font-family: var(--font-mono);
  font-size: 0.72em;
  opacity: 0.7;
}

.prose :deep(h2) {
  font-size: 22px;
}

.prose :deep(h3) {
  font-size: 17px;
  color: var(--text);
}

.prose :deep(p) {
  margin: 0 0 1.05em;
}

.prose :deep(strong) {
  color: var(--text);
}

.prose :deep(a) {
  color: var(--gold);
  text-decoration: none;
}

.prose :deep(a.wiki-link) {
  border-bottom: 1px dashed color-mix(in srgb, var(--gold) 60%, transparent);
}

.prose :deep(.wiki-link--broken) {
  color: var(--danger);
  border-bottom: 1px dashed color-mix(in srgb, var(--danger) 55%, transparent);
  cursor: help;
}

.prose :deep(ul),
.prose :deep(ol) {
  margin: 0 0 1.1em;
  padding-left: 1.4em;
}

.prose :deep(li::marker) {
  color: var(--gold);
}

.prose :deep(blockquote) {
  margin: 1.3em 0;
  padding: 6px 0 6px 16px;
  border-left: 2px solid var(--gold);
  color: var(--t2);
}

.prose :deep(code) {
  padding: 1px 5px;
  background: var(--panel-2);
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: 0.86em;
  color: var(--gold);
}

.prose :deep(pre) {
  margin: 1.2em 0;
  padding: 14px 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow-x: auto;
}

.prose :deep(pre code) {
  padding: 0;
  background: transparent;
  color: var(--t2);
  font-size: 12px;
  line-height: 1.8;
}

.prose :deep(hr) {
  height: 1px;
  margin: 2em 0;
  background: var(--line);
  border: 0;
}

.prose :deep(img) {
  max-width: 100%;
  border-radius: var(--r-md);
}

@keyframes save-pulse {
  50% {
    opacity: 0.35;
  }
}

@media (max-width: 1100px) {
  .editor__layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .editor__rail {
    position: static;
    max-height: none;
    padding: 20px 28px 32px;
    border-left: 0;
    border-top: 1px solid var(--line);
  }
}

@media (max-width: 767px) {
  .editor__bar {
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 16px;
  }

  .editor__breadcrumb {
    flex-basis: 100%;
  }

  .editor__readout {
    display: none;
  }

  .editor__main {
    padding: 24px 16px 56px;
  }

  .editor__title {
    font-size: 30px;
  }

  .editor__meta {
    flex-wrap: wrap;
    gap: 5px;
  }

  .editor__input {
    font-size: 13px;
  }

  .wiki-pop {
    width: min(272px, calc(100vw - 48px));
  }
}
</style>
