<template>
  <div ref="wrap" class="graph">
    <canvas ref="canvas" class="graph__canvas" role="img" aria-label="知识图谱画布，使用页面内的搜索、类型过滤与布局控件浏览，节点可在画布上拖拽调整" />

    <div class="graph__outline outline-word" aria-hidden="true">STAR ATLAS</div>

    <section class="graph__filters">
      <span class="readout graph__stats">{{ stats.total }} STARS · {{ stats.links }} LINKS</span>
      <button
        v-for="item in typeFilters"
        :key="item.type"
        type="button"
        :class="['graph__filter', activeTypes.has(item.type) && 'graph__filter--on']"
        @click="toggleType(item.type)"
      >
        <span :class="['graph__glyph', `graph__glyph--${item.type}`]" aria-hidden="true" />
        <span class="graph__filter-label">{{ item.label }}</span>
        <span class="num graph__filter-count">{{ item.count }}</span>
      </button>
    </section>

    <div class="graph__search">
      <Search :size="14" :stroke-width="1.8" class="graph__search-icon" />
      <input
        ref="searchRef"
        v-model="query"
        class="graph__search-input"
        type="text"
        placeholder="搜索节点，回车定位…"
        aria-label="搜索图谱节点"
        @keydown.enter="locate"
        @keydown.esc="query = ''"
      />
      <Kbd keys="/" />
    </div>

    <Transition name="panel">
      <aside v-if="selected" class="graph__panel">
        <header class="graph__panel-head">
          <span class="readout">SELECTED NODE · 选中节点</span>
          <button type="button" class="graph__panel-close" aria-label="关闭详情" @click="clearSelection">
            <X :size="14" />
          </button>
        </header>

        <h2 class="graph__panel-title">{{ selected.label }}</h2>
        <div class="graph__panel-meta">
          <Badge :tone="selected.type === 'note' ? 'gold' : selected.type === 'tag' ? 'steel' : 'neutral'">
            {{ typeLabel(selected.type) }}
          </Badge>
          <span class="readout">{{ degreeOf(selected.id) }} LINKS · STAR ATLAS</span>
        </div>

        <div class="graph__panel-body">
          <span class="readout">CONNECTIONS · 连接</span>
          <button
            v-for="connection in connections"
            :key="`${connection.id}-${connection.edgeType}`"
            type="button"
            class="graph__connection"
            @click="selectById(connection.id)"
          >
            <span :class="['graph__glyph', `graph__glyph--${connection.type}`]" aria-hidden="true" />
            <span class="graph__connection-label">{{ connection.label }}</span>
            <span class="readout">{{ typeLabel(connection.type) }}</span>
          </button>
          <p v-if="!connections.length" class="graph__panel-empty">这个节点还没有连接。</p>
        </div>

        <AppButton v-if="selected.type === 'note'" block size="sm" @click="openNote(selected.id)">
          打开笔记 ↗
        </AppButton>
      </aside>
    </Transition>

    <div class="graph__controls">
      <SegmentedControl
        :model-value="layout"
        :items="layoutItems"
        size="sm"
        aria-label="图谱布局"
        @update:model-value="switchLayout($event as 'force' | 'radial')"
      />
      <span class="graph__divider" aria-hidden="true" />
      <button type="button" class="graph__zoom" aria-label="缩小" @click="zoomBy(1 / 1.25)">
        <Minus :size="14" />
      </button>
      <span class="num graph__zoom-value">{{ zoomPercent }}%</span>
      <button type="button" class="graph__zoom" aria-label="放大" @click="zoomBy(1.25)">
        <Plus :size="14" />
      </button>
      <button type="button" class="graph__zoom" aria-label="重置视图" @click="resetZoom">
        <Maximize2 :size="14" />
      </button>
    </div>

    <p class="graph__hint">单击节点 · 拖拽画布 · 滚轮缩放 · 双击背景取消选择</p>

    <div
      v-if="tooltip.show"
      class="graph__tooltip"
      :style="{ left: `${tooltip.x + 12}px`, top: `${tooltip.y + 12}px` }"
    >
      <span class="graph__tooltip-label">{{ tooltip.label }}</span>
      <span class="readout">{{ typeLabel(tooltip.type) }}</span>
    </div>

    <div v-if="loading" class="graph__state">
      <Spinner :size="22" />
      <span class="readout">LOADING STAR ATLAS…</span>
    </div>

    <div v-else-if="error" class="graph__state">
      <p class="graph__state-text">{{ error }}</p>
      <AppButton size="sm" variant="secondary" @click="load">重新加载</AppButton>
    </div>

    <div v-else-if="!allNodes.length" class="graph__state">
      <EmptyState title="星图还是空的" description="写下第一条笔记，节点会在这里出现。">
        <AppButton size="sm" @click="router.push('/notes/new')">新建笔记</AppButton>
      </EmptyState>
    </div>

    <div v-else-if="!stats.total" class="graph__state graph__state--inline">
      <p class="graph__state-text">当前过滤条件下没有可见节点。</p>
      <AppButton size="sm" variant="secondary" @click="resetFilters">显示全部</AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'
import { Maximize2, Minus, Plus, Search, X } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import Badge from '@/components/ui/Badge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Kbd from '@/components/ui/Kbd.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { filterGraph, findNode, graphStats, nodeDegrees, radialPositions } from '@/lib/graph'
import { useGraphStore } from '@/stores/graph'
import { useThemeStore } from '@/stores/theme'
import type { GraphData, GraphEdge, GraphNode } from '@/types/graph'

interface SimNode extends GraphNode, d3.SimulationNodeDatum {
  x: number
  y: number
}

interface SimEdge extends d3.SimulationLinkDatum<SimNode> {
  source: string | SimNode
  target: string | SimNode
  type: string
}

const router = useRouter()
const themeStore = useThemeStore()

const wrap = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const searchRef = ref<HTMLInputElement | null>(null)

const allNodes = ref<GraphNode[]>([])
const allEdges = ref<GraphEdge[]>([])
const visibleNodes = ref<GraphNode[]>([])
const visibleEdges = ref<GraphEdge[]>([])
const loading = ref(true)
const error = ref('')
const selectedId = ref<string | null>(null)
const activeTypes = ref(new Set<string>(['note', 'tag', 'folder']))
const layout = ref<'force' | 'radial'>('force')
const zoomPercent = ref(100)
const query = ref('')
const graphStore = useGraphStore()
let appliedData: GraphData | null = null

const tooltip = reactive({ show: false, x: 0, y: 0, label: '', type: 'note' })

const layoutItems = [
  { label: '力导向', value: 'force' },
  { label: '径向', value: 'radial' }
]

const TYPE_LABELS: Record<string, string> = {
  note: 'NOTE',
  tag: 'TAG',
  folder: 'FOLDER'
}

const layoutState = {
  width: 0,
  height: 0,
  dpr: 1
}

let simulation: d3.Simulation<SimNode, SimEdge> | null = null
let simNodes: SimNode[] = []
let simEdges: SimEdge[] = []
let degrees = new Map<string, number>()
let transform = d3.zoomIdentity
let zoomBehavior: d3.ZoomBehavior<HTMLCanvasElement, unknown> | null = null
let resizeObserver: ResizeObserver | null = null
let ringFrame = 0
let layoutFrame = 0
let dashPhase = 0
let dragNode: SimNode | null = null

// 颜色全部在 mounted 时从 CSS 令牌读取，组件内不保留任何色值字面量
const palette = reactive({
  gold: '',
  steel: '',
  sage: '',
  text: '',
  muted: '',
  line: '',
  bg: ''
})

const stats = computed(() => graphStats(visibleNodes.value, visibleEdges.value))

const selected = computed(
  () => allNodes.value.find((node) => node.id === selectedId.value) ?? null
)

// 边数 × 节点数的 find 换成一次建索引；连接多时完整列出，由 rail 内部滚动承载。
const nodeIndex = computed(() => new Map(allNodes.value.map((node) => [node.id, node])))
const connections = computed(() => {
  const id = selectedId.value
  if (!id) return []
  const items: Array<{ id: string; label: string; type: string; edgeType: string }> = []
  const index = nodeIndex.value
  for (const edge of visibleEdges.value) {
    const source = edge.source
    const target = edge.target
    if (source !== id && target !== id) continue
    const otherId = source === id ? target : source
    const node = index.get(otherId)
    if (!node) continue
    items.push({ id: node.id, label: node.label, type: node.type, edgeType: edge.type })
  }
  return items
})

const typeFilters = computed(() => [
  { type: 'note', label: '笔记', count: stats.value.note },
  { type: 'tag', label: '标签', count: stats.value.tag },
  { type: 'folder', label: '文件夹', count: stats.value.folder }
])

function typeLabel(type: string) {
  return TYPE_LABELS[type] ?? type.toUpperCase()
}

function degreeOf(id: string) {
  return degrees.get(id) ?? 0
}

function refreshPalette() {
  const styles = getComputedStyle(document.documentElement)
  const read = (name: string) => styles.getPropertyValue(name).trim()
  palette.gold = read('--gold') || palette.gold
  palette.steel = read('--steel') || palette.steel
  palette.sage = read('--sage') || palette.sage
  palette.text = read('--text') || palette.text
  palette.muted = read('--t3') || palette.muted
  palette.line = read('--line-strong') || palette.line
  palette.bg = read('--bg') || palette.bg
}

function resizeCanvas() {
  const host = wrap.value
  const element = canvas.value
  if (!host || !element) return

  const rect = host.getBoundingClientRect()
  const width = Math.max(1, rect.width)
  const height = Math.max(1, rect.height)
  const dpr = Math.min(window.devicePixelRatio || 1, 2)

  layoutState.width = width
  layoutState.height = height
  layoutState.dpr = dpr

  element.width = Math.round(width * dpr)
  element.height = Math.round(height * dpr)
  element.style.width = `${width}px`
  element.style.height = `${height}px`

  simulation?.force('center', d3.forceCenter(width / 2, height / 2))
  draw()
}

function nodeRadius(node: SimNode) {
  return 5 + Math.min(6, Math.sqrt(degreeOf(node.id)) * 1.5)
}

function draw() {
  const element = canvas.value
  if (!element) return
  const ctx = element.getContext('2d')
  if (!ctx) return

  const { width, height, dpr } = layoutState
  const k = transform.k
  const selectedNow = selectedId.value
  const neighbors = new Set<string>()

  if (selectedNow) {
    for (const edge of simEdges) {
      const source = edge.source as SimNode
      const target = edge.target as SimNode
      if (typeof source !== 'object' || typeof target !== 'object') continue
      if (source.id === selectedNow) neighbors.add(target.id)
      if (target.id === selectedNow) neighbors.add(source.id)
    }
  }

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)
  ctx.save()
  ctx.translate(transform.x, transform.y)
  ctx.scale(k, k)

  for (const edge of simEdges) {
    const source = edge.source as SimNode
    const target = edge.target as SimNode
    if (typeof source !== 'object' || typeof target !== 'object') continue

    const active = !selectedNow || source.id === selectedNow || target.id === selectedNow
    ctx.globalAlpha = selectedNow ? (active ? 0.9 : 0.12) : 0.4
    ctx.strokeStyle = active && selectedNow ? palette.gold : palette.line
    ctx.lineWidth = (active && selectedNow ? 1.1 : 0.6) / k
    ctx.beginPath()
    ctx.moveTo(source.x, source.y)
    ctx.lineTo(target.x, target.y)
    ctx.stroke()
  }

  for (const node of simNodes) {
    const isSelected = node.id === selectedNow
    const isNeighbor = neighbors.has(node.id)
    const dimmed = Boolean(selectedNow) && !isSelected && !isNeighbor
    const radius = nodeRadius(node)

    ctx.globalAlpha = dimmed ? 0.16 : 1

    if (node.type === 'tag') {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = palette.bg
      ctx.fill()
      ctx.strokeStyle = isSelected ? palette.gold : palette.steel
      ctx.lineWidth = (isSelected ? 1.6 : 1.1) / k
      ctx.stroke()
    } else if (node.type === 'folder') {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius + 2.5, 0, Math.PI * 2)
      ctx.strokeStyle = isSelected ? palette.gold : palette.muted
      ctx.lineWidth = 0.9 / k
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius * 0.45, 0, Math.PI * 2)
      ctx.fillStyle = isSelected ? palette.gold : palette.muted
      ctx.fill()
    } else {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = palette.gold
      ctx.fill()
    }

    const connectedEnough = degreeOf(node.id) >= 3
    const showLabel =
      isSelected ||
      connectedEnough ||
      (node.type === 'note' ? k > 1.2 : node.type === 'folder' ? k > 1.1 : k > 1.35)
    if (showLabel) {
      ctx.globalAlpha = dimmed ? 0.12 : 1
      ctx.fillStyle = isSelected ? palette.gold : palette.muted
      ctx.font = `${9 / k}px "JetBrains Mono", monospace`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      const label = node.label.length > 16 ? `${node.label.slice(0, 16)}…` : node.label
      ctx.fillText(label, node.x, node.y + radius + 5 / k)
    }
  }

  const active = simNodes.find((node) => node.id === selectedNow)
  if (active) {
    ctx.globalAlpha = 1
    ctx.strokeStyle = palette.gold
    ctx.lineWidth = 1.2 / k
    ctx.setLineDash([4 / k, 4 / k])
    ctx.lineDashOffset = -dashPhase / k
    ctx.beginPath()
    ctx.arc(active.x, active.y, nodeRadius(active) + 7, 0, Math.PI * 2)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.globalAlpha = 0.28
    ctx.beginPath()
    ctx.arc(active.x, active.y, nodeRadius(active) + 11, 0, Math.PI * 2)
    ctx.stroke()
  }

  ctx.restore()
  ctx.globalAlpha = 1
}

function animateRing() {
  if (!selectedId.value) {
    ringFrame = 0
    return
  }
  dashPhase = (dashPhase + 0.55) % 1000
  draw()
  ringFrame = requestAnimationFrame(animateRing)
}

function startRing() {
  if (!ringFrame) ringFrame = requestAnimationFrame(animateRing)
}

function stopRing() {
  if (ringFrame) cancelAnimationFrame(ringFrame)
  ringFrame = 0
}

function createSimulation() {
  simulation?.stop()
  if (!simNodes.length) return

  simulation = d3
    .forceSimulation<SimNode>(simNodes)
    .force(
      'link',
      d3
        .forceLink<SimNode, SimEdge>(simEdges)
        .id((node) => node.id)
        .distance((edge) => (edge.type === 'links_to' ? 92 : 68))
        .strength(0.28)
    )
    .force('charge', d3.forceManyBody<SimNode>().strength(-130))
    .force('center', d3.forceCenter(layoutState.width / 2, layoutState.height / 2))
    .force('x', d3.forceX<SimNode>(layoutState.width / 2).strength(0.045))
    .force('y', d3.forceY<SimNode>(layoutState.height / 2).strength(0.06))
    .force(
      'collide',
      d3.forceCollide<SimNode>().radius((node) => nodeRadius(node) + 8)
    )
    .alpha(1)
    .alphaDecay(0.035)
    .on('tick', draw)
}

function rebuild(keepPositions = true) {
  const previous = new Map<string, { x: number; y: number }>()
  if (keepPositions) {
    simNodes.forEach((node) => previous.set(node.id, { x: node.x, y: node.y }))
  }

  const filtered = filterGraph(allNodes.value, allEdges.value, activeTypes.value)
  const centerX = layoutState.width / 2
  const centerY = layoutState.height / 2

  visibleNodes.value = filtered.nodes
  visibleEdges.value = filtered.edges

  simNodes = filtered.nodes.map((node) => {
    const prior = previous.get(node.id)
    return {
      ...node,
      x: prior?.x ?? centerX + (Math.random() - 0.5) * 120,
      y: prior?.y ?? centerY + (Math.random() - 0.5) * 120
    }
  })

  simEdges = filtered.edges.map((edge) => ({ ...edge }))
  degrees = nodeDegrees(filtered.edges)

  if (!simNodes.some((node) => node.id === selectedId.value)) {
    selectedId.value = null
    stopRing()
  }

  createSimulation()
  if (layout.value === 'radial') applyRadial(true)
  draw()
}

function applyGraphData(next: GraphData | null) {
  appliedData = next
  allNodes.value = next?.nodes ?? []
  allEdges.value = next?.edges ?? []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const cached = await graphStore.load()
    applyGraphData(cached)
    await nextTick()
    resizeCanvas()
    if (allNodes.value.length) rebuild(false)
    if (graphStore.error) error.value = graphStore.error
  } catch {
    error.value = '星图加载失败，请检查网络或稍后重试。'
  } finally {
    loading.value = false
  }
}

// 后台静默刷新拿到新数据时才重算布局；304 不替换 data 引用，watch 不会触发。
watch(
  () => graphStore.data,
  (next) => {
    if (!next || next === appliedData) return
    applyGraphData(next)
    resizeCanvas()
    rebuild(false)
  }
)

function pick(event: MouseEvent | TouchEvent | WheelEvent): SimNode | null {
  const element = canvas.value
  if (!element || !simulation) return null
  const [mx, my] = d3.pointer(event as MouseEvent, element)
  const x = (mx - transform.x) / transform.k
  const y = (my - transform.y) / transform.k
  return simulation.find(x, y, 14 / transform.k) ?? null
}

function selectNode(node: SimNode) {
  selectedId.value = node.id
  startRing()
  draw()
}

function selectById(id: string) {
  const node = simNodes.find((item) => item.id === id)
  if (node) selectNode(node)
}

function clearSelection() {
  selectedId.value = null
  stopRing()
  draw()
}

function openNote(id: string) {
  router.push(`/notes/${id}`)
}

function toggleType(type: string) {
  const next = new Set(activeTypes.value)
  if (next.has(type)) next.delete(type)
  else next.add(type)
  activeTypes.value = next
  rebuild()
}

function resetFilters() {
  activeTypes.value = new Set(['note', 'tag', 'folder'])
  rebuild()
}

function locate() {
  const node = findNode(allNodes.value, query.value)
  if (!node) return
  if (!activeTypes.value.has(node.type)) {
    const next = new Set(activeTypes.value)
    next.add(node.type)
    activeTypes.value = next
    rebuild()
  }
  const target = simNodes.find((item) => item.id === node.id)
  if (!target) return
  selectNode(target)
  flyTo(target)
}

function flyTo(node: SimNode) {
  const element = canvas.value
  if (!element || !zoomBehavior) return
  const k = Math.max(1.25, transform.k)
  const x = layoutState.width / 2 - node.x * k
  const y = layoutState.height / 2 - node.y * k
  d3.select(element)
    .transition()
    .duration(700)
    .call(zoomBehavior.transform, d3.zoomIdentity.translate(x, y).scale(k))
}

function switchLayout(next: 'force' | 'radial') {
  layout.value = next
  if (!simulation) return

  if (next === 'radial') {
    applyRadial(false)
    resetZoom()
    return
  }

  cancelAnimationFrame(layoutFrame)
  simNodes.forEach((node) => {
    node.fx = null
    node.fy = null
  })
  simulation.alpha(0.75).restart()
}

function applyRadial(immediate: boolean) {
  if (!simulation) return
  simulation.stop()

  const targets = radialPositions(simNodes, layoutState.width, layoutState.height)
  const starts = new Map(simNodes.map((node) => [node.id, { x: node.x, y: node.y }]))
  const duration = immediate ? 0 : 1000
  const startAt = performance.now()

  cancelAnimationFrame(layoutFrame)

  const step = (now: number) => {
    const progress = duration === 0 ? 1 : Math.min(1, (now - startAt) / duration)
    const eased = 1 - Math.pow(1 - progress, 3)

    simNodes.forEach((node) => {
      const from = starts.get(node.id)
      const target = targets.get(node.id)
      if (!from || !target) return
      node.x = from.x + (target.x - from.x) * eased
      node.y = from.y + (target.y - from.y) * eased
      node.vx = 0
      node.vy = 0
    })
    draw()

    if (progress < 1) {
      layoutFrame = requestAnimationFrame(step)
    } else {
      simNodes.forEach((node) => {
        node.fx = node.x
        node.fy = node.y
      })
    }
  }

  layoutFrame = requestAnimationFrame(step)
}

function zoomBy(factor: number) {
  const element = canvas.value
  if (!element || !zoomBehavior) return
  d3.select(element)
    .transition()
    .duration(220)
    .call(zoomBehavior.scaleBy, factor)
}

function resetZoom() {
  const element = canvas.value
  if (!element || !zoomBehavior) return
  d3.select(element)
    .transition()
    .duration(400)
    .call(zoomBehavior.transform, d3.zoomIdentity)
}

function setupInteractions() {
  const element = canvas.value
  if (!element) return

  zoomBehavior = d3
    .zoom<HTMLCanvasElement, unknown>()
    .scaleExtent([0.35, 3])
    .filter((event: Event) => {
      if (event.type === 'mousedown' || event.type === 'touchstart') {
        return !pick(event as MouseEvent)
      }
      return true
    })
    .on('zoom', (event) => {
      transform = event.transform
      zoomPercent.value = Math.round(transform.k * 100)
      draw()
    })

  d3.select(element).call(zoomBehavior)

  const dragBehavior = d3
    .drag<HTMLCanvasElement, unknown>()
    .filter((event) => Boolean(pick(event as MouseEvent)))
    .on('start', (event) => {
      const node = pick(event as MouseEvent)
      if (!node) return
      dragNode = node
      node.fx = node.x
      node.fy = node.y
      simulation?.alphaTarget(0.18).restart()
    })
    .on('drag', (event) => {
      if (!dragNode) return
      const [mx, my] = d3.pointer(event as MouseEvent, element)
      dragNode.fx = (mx - transform.x) / transform.k
      dragNode.fy = (my - transform.y) / transform.k
      draw()
    })
    .on('end', () => {
      if (!dragNode) return
      dragNode.fx = null
      dragNode.fy = null
      dragNode = null
      simulation?.alphaTarget(0)
    })

  d3.select(element).call(dragBehavior)

  element.addEventListener('pointermove', onPointerMove)
  element.addEventListener('pointerleave', onPointerLeave)
  element.addEventListener('click', onClick)
  element.addEventListener('dblclick', onDoubleClick)
}

function onPointerMove(event: PointerEvent) {
  const element = canvas.value
  if (!element) return
  const node = pick(event)
  element.style.cursor = node ? 'pointer' : 'grab'

  if (!node) {
    tooltip.show = false
    return
  }

  const rect = element.getBoundingClientRect()
  tooltip.show = true
  tooltip.x = event.clientX - rect.left
  tooltip.y = event.clientY - rect.top
  tooltip.label = node.label
  tooltip.type = node.type
}

function onPointerLeave() {
  tooltip.show = false
}

function onClick(event: MouseEvent) {
  const node = pick(event)
  if (node) selectNode(node)
  else clearSelection()
}

function onDoubleClick(event: MouseEvent) {
  if (!pick(event)) clearSelection()
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  const typing =
    target &&
    (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)
  if (event.key === '/' && !typing) {
    event.preventDefault()
    searchRef.value?.focus()
  }
  if (event.key === 'Escape') {
    tooltip.show = false
  }
}

onMounted(async () => {
  refreshPalette()
  await nextTick()
  resizeCanvas()
  setupInteractions()
  window.addEventListener('keydown', onKeydown)

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => resizeCanvas())
    if (wrap.value) resizeObserver.observe(wrap.value)
  }

  await load()
})

onBeforeUnmount(() => {
  simulation?.stop()
  stopRing()
  cancelAnimationFrame(layoutFrame)
  resizeObserver?.disconnect()
  window.removeEventListener('keydown', onKeydown)
  const element = canvas.value
  if (element) {
    element.removeEventListener('pointermove', onPointerMove)
    element.removeEventListener('pointerleave', onPointerLeave)
    element.removeEventListener('click', onClick)
    element.removeEventListener('dblclick', onDoubleClick)
    d3.select(element).on('.zoom', null).on('.drag', null)
  }
})

watch(
  () => themeStore.isDark,
  () => {
    refreshPalette()
    draw()
  }
)
</script>

<style scoped>
.graph {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: transparent;
}

.graph__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  cursor: grab;
}

.graph__outline {
  left: 50%;
  bottom: -6%;
  transform: translateX(-50%);
  font-size: clamp(120px, 17vw, 260px);
  opacity: 0.5;
  pointer-events: none;
}

.graph__filters {
  position: absolute;
  top: 18px;
  left: 20px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 178px;
  padding: 10px 10px 8px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}

.graph__stats {
  margin-bottom: 6px;
  color: var(--t2);
}

.graph__filter {
  display: grid;
  grid-template-columns: 14px 1fr auto;
  align-items: center;
  gap: 8px;
  height: 26px;
  padding: 0 6px;
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background-color var(--d-fast) var(--ease-out);
}

.graph__filter:hover {
  background: var(--panel-2);
  color: var(--t2);
}

.graph__filter--on {
  color: var(--t2);
}

.graph__filter-label {
  font-size: 12px;
  text-align: left;
}

.graph__filter-count {
  font-size: 10px;
  color: var(--t3);
}

.graph__glyph {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  justify-self: center;
}

.graph__glyph--note {
  background: var(--gold);
}

.graph__glyph--tag {
  border: 1px solid var(--steel);
}

.graph__glyph--folder {
  border: 1px solid var(--t3);
  box-shadow: inset 0 0 0 1.5px var(--t3);
}

.graph__search {
  position: absolute;
  top: 18px;
  left: 50%;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(360px, calc(100% - 40px));
  height: 34px;
  padding: 0 10px;
  transform: translateX(-50%);
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
}

.graph__search:focus-within {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-soft);
}

.graph__search-icon {
  color: var(--t3);
}

.graph__search-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  background: transparent;
  border: 0;
  outline: none;
  font-size: 12px;
  color: var(--text);
}

.graph__search-input::placeholder {
  color: var(--t3);
}

.graph__panel {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 3;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 286px;
  max-height: calc(100% - 120px);
  padding: 14px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-float);
  overflow-y: auto;
}

.graph__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.graph__panel-close {
  display: inline-flex;
  width: 20px;
  height: 20px;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  color: var(--t3);
}

.graph__panel-close:hover {
  color: var(--text);
  background: var(--panel-2);
}

.graph__panel-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.35;
}

.graph__panel-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.graph__panel-body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 2px;
  min-height: 0;
  overflow-y: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}

.graph__panel-body > .readout {
  margin-bottom: 6px;
}

.graph__connection {
  display: grid;
  grid-template-columns: 12px 1fr auto;
  align-items: center;
  gap: 8px;
  height: 28px;
  padding: 0 4px;
  border-radius: var(--r-sm);
  text-align: left;
  color: var(--t2);
}

.graph__connection:hover {
  background: var(--panel-2);
  color: var(--gold);
}

.graph__connection-label {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graph__panel-empty {
  font-size: 11px;
  color: var(--t3);
}

.graph__controls {
  position: absolute;
  bottom: 18px;
  left: 50%;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px;
  transform: translateX(-50%);
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
}

.graph__divider {
  width: 1px;
  height: 16px;
  margin: 0 4px;
  background: var(--line);
}

.graph__zoom {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--r-sm);
  color: var(--t3);
}

.graph__zoom:hover {
  color: var(--gold);
  background: var(--panel-2);
}

.graph__zoom-value {
  min-width: 38px;
  text-align: center;
  font-size: 10px;
  color: var(--t3);
}

.graph__hint {
  position: absolute;
  bottom: 14px;
  left: 20px;
  z-index: 1;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.05em;
  color: var(--t3);
  pointer-events: none;
}

.graph__tooltip {
  position: absolute;
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  box-shadow: var(--shadow-float);
  pointer-events: none;
  white-space: nowrap;
}

.graph__tooltip-label {
  font-size: 11px;
  color: var(--text);
}

.graph__state {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: color-mix(in srgb, var(--bg) 78%, transparent);
}

.graph__state--inline {
  inset: auto 0 70px;
  background: none;
}

.graph__state-text {
  font-size: 12px;
  color: var(--t2);
}

.panel-enter-active,
.panel-leave-active {
  transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out);
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

@media (max-width: 767px) {
  .graph__filters {
    top: 12px;
    left: 12px;
    min-width: 140px;
  }

  .graph__search {
    top: auto;
    bottom: 62px;
    width: calc(100% - 24px);
  }

  .graph__panel {
    top: auto;
    bottom: 104px;
    left: 12px;
    right: 12px;
    width: auto;
    max-height: 46%;
  }

  .graph__controls {
    bottom: 12px;
  }

  .graph__hint {
    display: none;
  }
}
</style>
