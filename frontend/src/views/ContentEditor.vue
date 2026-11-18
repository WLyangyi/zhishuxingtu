<template>
  <div class="ce">
    <div class="ce__outline outline-word" aria-hidden="true">COMPOSE</div>

    <div class="ce__bar">
      <Breadcrumb :items="breadcrumb" class="ce__breadcrumb" />

      <span class="ce__status">
        <span :class="['ce__dot', `ce__dot--${saveState}`]" aria-hidden="true" />
        <span class="ce__save-text">{{ saveText }}</span>
      </span>

      <AppButton v-if="!notFound" size="sm" :disabled="saving" @click="save">保存</AppButton>
      <AppButton v-if="!isNew && !notFound" size="sm" variant="secondary" @click="confirmOpen = true">
        删除
      </AppButton>
    </div>

    <AppModal v-model:open="confirmOpen" title="删除这条内容？" size="sm">
      <p class="ce__confirm-text">「{{ title || '未命名' }}」将被删除，此操作无法撤销。</p>
      <template #footer>
        <AppButton variant="secondary" size="sm" @click="confirmOpen = false">取消</AppButton>
        <AppButton variant="danger" size="sm" @click="doDelete">删除</AppButton>
      </template>
    </AppModal>

    <div class="ce__layout">
      <main class="ce__main">
        <div ref="bodyRef" class="ce__body">
          <div v-if="loading" class="ce__loading">
            <Skeleton :lines="2" :height="22" />
            <Skeleton :lines="6" :height="13" />
          </div>

          <EmptyState
            v-else-if="notFound"
            title="内容不存在"
            description="它可能已被删除，或链接失效。"
          >
            <AppButton size="sm" @click="goBack">返回</AppButton>
          </EmptyState>

          <template v-else>
            <textarea
              ref="titleRef"
              v-model="title"
              class="ce__title"
              rows="1"
              placeholder="无标题"
              aria-label="内容标题"
              @input="resizeTitle"
              @keydown="onTitleKeydown"
            />

            <div class="ce__meta">
              <span>CONTENT</span>
              <span>·</span>
              <span>{{ typeName || 'UNSORTED' }}</span>
              <span>·</span>
              <span>{{ words }} 字</span>
            </div>

            <div class="ce__divider" />

            <textarea
              v-model="content"
              class="ce__input"
              placeholder="开始编写内容…"
              aria-label="内容正文"
            />
          </template>
        </div>
      </main>

      <aside class="ce__rail">
        <section class="ce__block">
          <header class="ce__block-head">
            <span class="readout">分类 · CATEGORY</span>
          </header>
          <AppSelect
            v-model="categoryId"
            :options="categoryOptions"
            placeholder="选择分类"
            aria-label="分类"
          />
        </section>

        <section class="ce__block">
          <header class="ce__block-head">
            <span class="readout">类型 · TYPE</span>
          </header>
          <AppSelect
            v-model="typeId"
            :options="typeOptions"
            placeholder="选择类型"
            aria-label="内容类型"
          />
        </section>

        <section class="ce__block">
          <header class="ce__block-head">
            <span class="readout">标签 · TAGS</span>
            <button type="button" class="ce__tag-add" aria-label="新建标签" @click="openTagInput">
              <Plus :size="12" :stroke-width="1.8" />
            </button>
          </header>
          <div class="ce__tags">
            <button
              v-for="tag in tagsStore.tags"
              :key="tag.id"
              type="button"
              :class="['ce__tag', tagIds.includes(tag.id) && 'ce__tag--on']"
              :aria-pressed="tagIds.includes(tag.id)"
              @click="toggleTag(tag.id)"
            >
              #{{ tag.name }}
            </button>
            <span v-if="!tagsStore.tags.length" class="ce__empty-tip">暂无标签</span>
          </div>
          <input
            v-if="tagInputOpen"
            ref="tagInputRef"
            v-model="newTagName"
            class="ce__tag-new-input"
            placeholder="标签名称，回车创建"
            aria-label="新建标签名称"
            @keydown.enter.prevent="submitNewTag"
            @keydown.escape.prevent="closeTagInput"
          />
        </section>

        <section class="ce__block">
          <header class="ce__block-head">
            <span class="readout">反向链接 · BACKLINKS</span>
            <span class="num">{{ backlinks.length }}</span>
          </header>
          <div v-if="backlinks.length" class="ce__backlinks">
            <button
              v-for="link in backlinks"
              :key="link.id"
              type="button"
              class="ce__backlink"
              @click="openBacklink(link.id)"
            >
              <ArrowRight :size="12" :stroke-width="1.8" />
              <span>{{ link.title }}</span>
            </button>
          </div>
          <span v-else class="ce__empty-tip">暂无反向链接</span>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Plus } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { contentsApi } from '@/api/categories'
import { useCategoryStore } from '@/stores/category'
import { useTagsStore } from '@/stores/tags'
import { useNotificationStore } from '@/stores/notification'
import { wordCount } from '@/lib/editor'
import type { Category } from '@/types/category'

const route = useRoute()
const router = useRouter()
const categoryStore = useCategoryStore()
const tagsStore = useTagsStore()
const notification = useNotificationStore()

const contentId = computed(() => route.params.id as string)
const isNew = computed(() => route.name === 'NewContent')

const loading = ref(true)
const notFound = ref(false)
const saving = ref(false)
const saveState = ref<'idle' | 'dirty' | 'saving' | 'saved' | 'error'>('idle')

const title = ref('')
const content = ref('')
const categoryId = ref('')
const typeId = ref('')
const tagIds = ref<string[]>([])
const backlinks = ref<{ id: string; title: string }[]>([])

/* 表单任一字段变化即进入脏状态；加载灌值期间不追踪 */
let hydrating = false
watch([title, content, categoryId, typeId, tagIds], () => {
  if (hydrating || saving.value) return
  saveState.value = 'dirty'
})

const titleRef = ref<HTMLTextAreaElement | null>(null)
const bodyRef = ref<HTMLElement | null>(null)
const confirmOpen = ref(false)
const tagInputOpen = ref(false)
const newTagName = ref('')
const tagInputRef = ref<HTMLInputElement | null>(null)

const saveText = computed(
  () =>
    ({ idle: '—', dirty: 'DIRTY', saving: 'SAVING', saved: 'SAVED', error: 'ERROR' })[
      saveState.value
    ]
)
const words = computed(() => wordCount(content.value))

const categories = computed<Category[]>(() => categoryStore.categories)
const currentCategory = computed(() => categories.value.find((c) => c.id === categoryId.value))
const typeName = computed(
  () =>
    currentCategory.value?.content_types.find((t) => t.id === typeId.value)?.name ??
    (isNew.value ? '' : '—')
)

const categoryOptions = computed(() =>
  categories.value.map((c) => ({ label: c.name, value: c.id }))
)
const typeOptions = computed(() =>
  (currentCategory.value?.content_types ?? []).map((t) => ({ label: t.name, value: t.id }))
)

const breadcrumb = computed(() => [
  { label: '我的笔记', to: '/library' },
  ...(currentCategory.value ? [{ label: currentCategory.value.name, to: `/library/${currentCategory.value.id}` }] : []),
  { label: isNew.value ? '新内容' : title.value || '未命名' }
])

function resizeTitle() {
  const element = titleRef.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${element.scrollHeight}px`
}

function onTitleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    ;(bodyRef.value?.querySelector('.ce__input') as HTMLTextAreaElement | null)?.focus()
  }
}

async function save() {
  if (saving.value) return

  if (!title.value.trim()) {
    notification.warning('请输入标题', '标题不能为空')
    titleRef.value?.focus()
    return
  }

  if (!categoryId.value || !typeId.value) {
    notification.warning('请选择分类和内容类型')
    return
  }

  saving.value = true
  saveState.value = 'saving'
  try {
    const payload = {
      title: title.value.trim(),
      content: content.value,
      type_id: typeId.value,
      category_id: categoryId.value,
      tag_ids: tagIds.value
    }

    if (isNew.value) {
      const created = await contentsApi.createContent(payload)
      await router.replace({
        name: 'ContentEditor',
        params: { categoryId: created.data.category_id, id: created.data.id }
      })
    } else {
      await contentsApi.updateContent(contentId.value, payload)
    }
    saveState.value = 'saved'
  } catch {
    saveState.value = 'error'
    notification.error('保存失败', '内容未能保存，请稍后重试')
  } finally {
    saving.value = false
  }
}

/* 切换分类后，类型与新分类对齐：有类型落到第一个，无类型清空 */
watch(categoryId, () => {
  const types = currentCategory.value?.content_types ?? []
  if (!types.length) {
    typeId.value = ''
    return
  }
  if (!types.some((t) => t.id === typeId.value)) {
    typeId.value = types[0].id
  }
})

function toggleTag(id: string) {
  tagIds.value = tagIds.value.includes(id)
    ? tagIds.value.filter((t) => t !== id)
    : [...tagIds.value, id]
}

function openBacklink(id: string) {
  router.push({ name: 'ContentEditor', params: { categoryId: categoryId.value, id } })
}

function openTagInput() {
  tagInputOpen.value = true
  nextTick(() => tagInputRef.value?.focus())
}

function closeTagInput() {
  tagInputOpen.value = false
  newTagName.value = ''
}

async function submitNewTag() {
  const name = newTagName.value.trim()
  if (!name) return
  try {
    const tag = await tagsStore.createTag({ name })
    tagIds.value = [...tagIds.value, tag.id]
    notification.success('标签已创建', `「${name}」已添加并勾选`)
    closeTagInput()
  } catch (error: any) {
    notification.error('创建失败', error?.message || '请稍后重试')
  }
}

function goBack() {
  router.push(categoryId.value ? `/library/${categoryId.value}` : '/library')
}

async function doDelete() {
  if (!contentId.value) return
  confirmOpen.value = false
  try {
    await contentsApi.deleteContent(contentId.value)
    notification.success('内容已删除')
    goBack()
  } catch {
    notification.error('删除失败', '内容未能删除，请稍后重试')
  }
}

async function loadContent() {
  if (isNew.value) {
    hydrating = true
    loading.value = false
    saveState.value = 'idle'
    title.value = ''
    content.value = ''
    tagIds.value = []
    backlinks.value = []
    const routeCategory = route.params.categoryId as string
    if (routeCategory) categoryId.value = routeCategory
    const queryType = route.query.type_id as string | undefined
    if (queryType) typeId.value = queryType
    notFound.value = false
    nextTick(() => {
      resizeTitle()
      titleRef.value?.focus()
      hydrating = false
    })
    return
  }

  loading.value = true
  notFound.value = false
  hydrating = true
  try {
    const response = await contentsApi.getContent(contentId.value)
    const data = response.data
    title.value = data.title
    content.value = data.content || ''
    categoryId.value = data.category_id
    typeId.value = data.type_id
    tagIds.value = data.tags.map((t) => t.id)
    saveState.value = 'idle'

    try {
      const links = await contentsApi.getBacklinks(contentId.value)
      backlinks.value = links.data.items
    } catch {
      backlinks.value = []
    }

    await nextTick()
    resizeTitle()
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
    hydrating = false
  }
}

onMounted(async () => {
  await Promise.allSettled([categoryStore.fetchCategories(), tagsStore.fetchTags()])
  await loadContent()
})
</script>

<style scoped>
.ce {
  position: relative;
  min-height: 100%;
}

.ce__outline {
  right: -30px;
  bottom: -40px;
  font-size: clamp(100px, 13vw, 200px);
  opacity: 0.28;
  pointer-events: none;
}

.ce__bar {
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

.ce__breadcrumb {
  min-width: 0;
  flex: 1;
}

.ce__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.ce__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--t3);
}

.ce__dot--saving {
  background: var(--gold);
  animation: ce-save-pulse 1.2s ease-in-out infinite;
}

.ce__dot--saved {
  background: var(--success);
}

.ce__dot--error {
  background: var(--danger);
}

.ce__save-text {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

@keyframes ce-save-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}

.ce__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 286px;
}

.ce__main {
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 34px 32px 90px;
}

.ce__body {
  position: relative;
  width: 100%;
  max-width: 660px;
}

.ce__loading {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding-top: 10px;
}

.ce__title {
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

.ce__title::placeholder {
  color: var(--t3);
}

.ce__meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 14px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--t3);
}

.ce__divider {
  height: 1px;
  margin: 18px 0 24px;
  background: var(--line);
}

.ce__input {
  display: block;
  width: 100%;
  min-height: 52vh;
  padding: 0;
  background: transparent;
  border: 0;
  outline: none;
  resize: none;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.95;
  color: var(--t2);
  caret-color: var(--gold);
}

.ce__input::placeholder {
  color: var(--t3);
}

.ce__rail {
  align-self: start;
  position: sticky;
  top: 46px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 28px 20px 40px;
  border-left: 1px solid var(--line);
}

.ce__block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ce__block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ce__block-head .num {
  font-size: 10px;
  color: var(--t3);
}

.ce__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ce__tag {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-pill);
  background: transparent;
  font-size: 11px;
  color: var(--t2);
  cursor: pointer;
  transition: border-color var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out),
    background var(--d-fast) var(--ease-out);
}

.ce__tag:hover {
  border-color: var(--gold-line);
  color: var(--text);
}

.ce__tag--on {
  border-color: var(--gold-line);
  background: var(--gold-soft);
  color: var(--gold);
}

.ce__tag-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--t3);
  cursor: pointer;
  transition: color var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out);
}

.ce__tag-add:hover {
  color: var(--gold);
  border-color: var(--gold-line);
}

.ce__tag-new-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  background: var(--panel);
  outline: none;
  font-size: 12px;
  color: var(--text);
  caret-color: var(--gold);
}

.ce__tag-new-input:focus {
  border-color: var(--gold-line);
}

.ce__tag-new-input::placeholder {
  color: var(--t3);
}

.ce__backlinks {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ce__backlink {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--r-md);
  background: transparent;
  font-size: 12px;
  color: var(--t2);
  text-align: left;
  cursor: pointer;
  transition: background var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out);
}

.ce__backlink:hover {
  background: var(--panel-2);
  color: var(--text);
}

.ce__empty-tip {
  font-size: 11px;
  color: var(--t3);
}

.ce__confirm-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--t2);
}

@media (max-width: 1024px) {
  .ce__layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .ce__rail {
    position: static;
    border-left: 0;
    border-top: 1px solid var(--line);
  }
}
</style>
