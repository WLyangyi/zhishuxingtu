<template>
  <Teleport to="body">
    <Transition name="palette">
      <div v-if="open" class="palette-root">
        <div class="palette-backdrop" @click="close" />
        <section
          class="palette"
          role="dialog"
          aria-modal="true"
          aria-label="命令面板"
          @keydown.esc.stop="close"
        >
          <div class="palette__search">
            <Search :size="15" :stroke-width="1.8" class="palette__search-icon" />
            <input
              ref="inputRef"
              v-model="query"
              class="palette__input"
              type="text"
              :placeholder="placeholder"
              aria-label="搜索页面、笔记或动作"
              @keydown="onKeydown"
            />
            <Kbd keys="ESC" />
          </div>

          <div ref="listRef" class="palette__list">
            <div v-for="group in visibleGroups" :key="group.key" class="palette__group">
              <template v-if="group.items.length">
                <div class="palette__group-label readout">{{ group.label }}</div>
                <button
                  v-for="item in group.items"
                  :key="item.id"
                  type="button"
                  :class="['palette__item', item.id === activeItem?.id && 'palette__item--active']"
                  @mousemove="setActive(item)"
                  @click="choose(item)"
                >
                  <component :is="item.icon" v-if="item.icon" class="palette__icon" />
                  <span class="palette__label">{{ item.label }}</span>
                  <span v-if="item.hint" class="palette__hint">{{ item.hint }}</span>
                  <Kbd v-if="item.shortcut" :keys="item.shortcut" />
                </button>
              </template>
            </div>

            <EmptyState
              v-if="!flatItems.length"
              title="没有匹配结果"
              description="换个关键词，或直接向 AI 提问"
            />
          </div>

          <footer class="palette__foot">
            <span>↑↓ 选择</span>
            <span>Enter 执行</span>
            <span>Esc 关闭</span>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { matchesCommand } from '@/lib/pinyin'
import Kbd from './Kbd.vue'
import EmptyState from './EmptyState.vue'

export interface CommandItem {
  id: string
  label: string
  hint?: string
  shortcut?: string
  icon?: Component
  to?: string
  action?: () => void
}

interface CommandGroup {
  key: string
  label: string
  items: CommandItem[]
}

const DEFAULT_PAGES: CommandItem[] = [
  { id: 'page-home', label: '观测台', hint: '/', to: '/' },
  { id: 'page-library', label: '我的笔记', hint: '/library', to: '/library' },
  { id: 'page-graph', label: '关系图谱', hint: '/graph', to: '/graph' },
  { id: 'page-ai', label: 'AI 助手', hint: '/ai', to: '/ai' },
  { id: 'page-lab', label: '提示词实验室', hint: '/lab', to: '/lab' },
  { id: 'page-skills', label: 'Skills', hint: '/skills', to: '/skills' },
  { id: 'page-prompts', label: 'Prompts', hint: '/prompts', to: '/prompts' },
  { id: 'page-observability', label: '可观测面板', hint: '/ai/observability', to: '/ai/observability' }
]

const props = withDefaults(
  defineProps<{
    open?: boolean
    pages?: CommandItem[]
    notes?: CommandItem[]
    actions?: CommandItem[]
    placeholder?: string
    emptyNoteLimit?: number
  }>(),
  {
    open: false,
    notes: () => [],
    actions: () => [],
    placeholder: '搜索页面、笔记或执行动作…',
    emptyNoteLimit: 5
  }
)

const emit = defineEmits<{
  'update:open': [value: boolean]
  select: [item: CommandItem]
}>()

const router = useRouter()
const query = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)
const listRef = ref<HTMLElement | null>(null)

function matches(item: CommandItem, keyword: string) {
  return matchesCommand(item.label, item.hint, keyword)
}

const visibleGroups = computed<CommandGroup[]>(() => {
  const keyword = query.value.trim().toLowerCase()
  const notes = keyword ? props.notes : props.notes.slice(0, props.emptyNoteLimit)

  return [
    { key: 'pages', label: 'PAGES', items: (props.pages ?? DEFAULT_PAGES).filter((item) => matches(item, keyword)) },
    { key: 'notes', label: 'NOTES', items: notes.filter((item) => matches(item, keyword)) },
    { key: 'actions', label: 'ACTIONS', items: props.actions.filter((item) => matches(item, keyword)) }
  ]
})

const flatItems = computed(() => visibleGroups.value.flatMap((group) => group.items))
const activeItem = computed(() => flatItems.value[activeIndex.value])

watch(query, () => {
  activeIndex.value = 0
})

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    query.value = ''
    activeIndex.value = 0
    await nextTick()
    inputRef.value?.focus()
  }
)

function setActive(item: CommandItem) {
  const index = flatItems.value.findIndex((entry) => entry.id === item.id)
  if (index >= 0) activeIndex.value = index
}

function move(delta: number) {
  const total = flatItems.value.length
  if (!total) return
  activeIndex.value = (activeIndex.value + delta + total) % total
  nextTick(() => {
    listRef.value
      ?.querySelector<HTMLElement>('.palette__item--active')
      ?.scrollIntoView?.({ block: 'nearest' })
  })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    move(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    move(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    if (activeItem.value) choose(activeItem.value)
  } else if (event.key === 'Escape') {
    close()
  }
}

function choose(item: CommandItem) {
  emit('select', item)
  emit('update:open', false)
  item.action?.()
  if (item.to) router.push(item.to)
}

function close() {
  emit('update:open', false)
}
</script>

<style scoped>
.palette-root {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  justify-content: center;
  padding-top: 12vh;
}

.palette-backdrop {
  position: absolute;
  inset: 0;
  background: var(--overlay);
}

.palette {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(92vw, 620px);
  max-height: 68vh;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-float);
  overflow: hidden;
}

.palette__search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
}

.palette__search-icon {
  color: var(--t3);
  flex: none;
}

.palette__input {
  flex: 1;
  min-width: 0;
  height: 24px;
  background: transparent;
  border: 0;
  outline: none;
  font-size: 14px;
  color: var(--text);
}

.palette__input::placeholder {
  color: var(--t3);
}

.palette__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.palette__group + .palette__group {
  margin-top: 6px;
}

.palette__group-label {
  padding: 6px 8px 4px;
}

.palette__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 34px;
  padding: 0 8px 0 10px;
  border-left: 2px solid transparent;
  border-radius: var(--r-sm);
  text-align: left;
  color: var(--t2);
  transition: background-color var(--d-fast) var(--ease-out),
    color var(--d-fast) var(--ease-out);
}

.palette__item--active {
  background: var(--panel-2);
  border-left-color: var(--gold);
  color: var(--text);
}

.palette__icon {
  width: 14px;
  height: 14px;
  color: var(--t3);
}

.palette__label {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.palette__hint {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--t3);
}

.palette__foot {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 14px;
  border-top: 1px solid var(--line);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

.palette-enter-active,
.palette-leave-active {
  transition: opacity 180ms var(--ease-out);
}

.palette-enter-active .palette,
.palette-leave-active .palette {
  transition: transform 180ms var(--ease-out);
}

.palette-enter-from,
.palette-leave-to {
  opacity: 0;
}

.palette-enter-from .palette,
.palette-leave-to .palette {
  transform: translateY(-6px) scale(0.995);
}
</style>
