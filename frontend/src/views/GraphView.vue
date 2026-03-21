<template>
  <div class="graph-page">
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <button @click="goHome" class="toolbar-btn back-btn">
          <ArrowLeft :size="18" />
          <span>返回</span>
        </button>
        <div class="toolbar-divider"></div>
        <h1 class="toolbar-title">知识图谱</h1>
        <span class="node-count">{{ nodes.length }} 个节点</span>
      </div>
      
      <div class="toolbar-center">
        <div class="search-box">
          <Search :size="16" />
          <input 
            v-model="searchQuery" 
            placeholder="搜索节点..." 
            class="search-input"
          />
        </div>
      </div>
      
      <div class="toolbar-right">
        <div class="layout-switch">
          <button 
            class="layout-btn" 
            :class="{ active: layout === 'force' }"
            @click="setLayout('force')"
            title="力导向布局"
          >
            <Circle :size="16" />
          </button>
          <button 
            class="layout-btn" 
            :class="{ active: layout === 'radial' }"
            @click="setLayout('radial')"
            title="径向布局"
          >
            <Target :size="16" />
          </button>
        </div>
        <div class="toolbar-divider"></div>
        <div class="zoom-controls">
          <button @click="zoomIn" class="zoom-btn" title="放大">
            <Plus :size="16" />
          </button>
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <button @click="zoomOut" class="zoom-btn" title="缩小">
            <Minus :size="16" />
          </button>
          <button @click="resetZoom" class="zoom-btn reset" title="重置">
            <Maximize2 :size="16" />
          </button>
        </div>
      </div>
    </div>

    <div class="graph-main">
      <div class="graph-sidebar">
        <div class="sidebar-section">
          <h3 class="section-title">节点类型</h3>
          <div class="type-filters">
            <label 
              v-for="type in nodeTypes" 
              :key="type.id"
              class="type-filter"
              :class="{ active: activeTypes.includes(type.id) }"
            >
              <input 
                type="checkbox" 
                :value="type.id" 
                v-model="activeTypes"
                @change="filterNodes"
              />
              <span class="type-color" :style="{ backgroundColor: type.color }"></span>
              <span class="type-name">{{ type.name }}</span>
              <span class="type-count">{{ getTypeCount(type.id) }}</span>
            </label>
          </div>
        </div>

        <div class="sidebar-section">
          <h3 class="section-title">选中节点</h3>
          <div v-if="selectedNode" class="selected-info">
            <div class="selected-header">
              <span class="selected-type" :style="{ color: getNodeColor(selectedNode) }">
                {{ selectedNode.type }}
              </span>
              <h4 class="selected-title">{{ selectedNode.label }}</h4>
            </div>
            <div class="selected-stats">
              <div class="stat">
                <span class="stat-value">{{ getNodeConnections(selectedNode.id) }}</span>
                <span class="stat-label">连接</span>
              </div>
            </div>
            <button v-if="selectedNode.type === 'note'" @click="openNote(selectedNode.id)" class="open-btn">
              <ExternalLink :size="14" />
              打开笔记
            </button>
          </div>
          <div v-else class="empty-selection">
            <p>点击节点查看详情</p>
          </div>
        </div>

        <div class="sidebar-section">
          <h3 class="section-title">操作提示</h3>
          <div class="tips-list">
            <div class="tip-item">
              <MousePointer :size="14" />
              <span>点击节点查看详情</span>
            </div>
            <div class="tip-item">
              <Move :size="14" />
              <span>拖拽节点调整位置</span>
            </div>
            <div class="tip-item">
              <ZoomIn :size="14" />
              <span>滚轮缩放视图</span>
            </div>
            <div class="tip-item">
              <Move :size="14" />
              <span>拖拽空白区域平移</span>
            </div>
          </div>
        </div>
      </div>

      <div ref="graphContainer" class="graph-container">
        <svg ref="svgElement" class="graph-svg">
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            <marker 
              id="arrow" 
              viewBox="0 -5 10 10" 
              refX="20" 
              refY="0" 
              markerWidth="6" 
              markerHeight="6" 
              orient="auto"
            >
              <path d="M0,-5L10,0L0,5" fill="currentColor" class="arrow-path" />
            </marker>
          </defs>
          <g class="zoom-layer">
            <g class="edges-layer"></g>
            <g class="nodes-layer"></g>
          </g>
        </svg>
        
        <div v-if="loading" class="graph-loading">
          <div class="loading-spinner"></div>
          <span>加载图谱数据...</span>
        </div>
        
        <div v-if="!loading && nodes.length === 0" class="graph-empty">
          <Network :size="48" />
          <h3>暂无知识图谱</h3>
          <p>创建笔记并添加双向链接后，知识图谱将自动生成</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'
import { graphApi } from '@/api/graph'
import type { GraphData, GraphNode } from '@/types'
import { 
  ArrowLeft, Search, Circle, Target, Plus, Minus, Maximize2,
  ExternalLink, MousePointer, Move, ZoomIn, Network
} from 'lucide-vue-next'

const router = useRouter()
const graphContainer = ref<HTMLDivElement>()
const svgElement = ref<SVGSVGElement>()
const graphData = ref<GraphData>({ nodes: [], edges: [] })
const loading = ref(true)
const searchQuery = ref('')
const layout = ref<'force' | 'radial'>('force')
const zoomLevel = ref(1)
const selectedNode = ref<GraphNode | null>(null)

const nodes = computed(() => graphData.value.nodes)
const edges = computed(() => graphData.value.edges)

const nodeTypes = [
  { id: 'note', name: '笔记', color: '#f59e0b' },
  { id: 'tag', name: '标签', color: '#10b981' },
  { id: 'folder', name: '文件夹', color: '#6366f1' }
]

const activeTypes = ref<string[]>(['note', 'tag', 'folder'])

let simulation: d3.Simulation<SimNode, undefined> | null = null
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let zoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null

interface SimNode extends GraphNode, d3.SimulationNodeDatum {
  filtered?: boolean
}

let simNodes: SimNode[] = []
let simEdges: d3.SimulationLinkDatum<SimNode>[] = []

onMounted(async () => {
  await loadGraphData()
})

onUnmounted(() => {
  if (simulation) {
    simulation.stop()
  }
})

async function loadGraphData() {
  loading.value = true
  try {
    const response = await graphApi.getGlobal()
    graphData.value = response.data
    if (graphContainer.value && svgElement.value) {
      initGraph()
    }
  } catch (error) {
    console.error('Failed to load graph data:', error)
  } finally {
    loading.value = false
  }
}

function initGraph() {
  if (!graphContainer.value || !svgElement.value) return

  const width = graphContainer.value.clientWidth
  const height = graphContainer.value.clientHeight

  svg = d3.select(svgElement.value)
    .attr('width', width)
    .attr('height', height)

  zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      svg?.select('.zoom-layer').attr('transform', event.transform)
      zoomLevel.value = event.transform.k
    })

  svg.call(zoom)

  simNodes = graphData.value.nodes.map(n => ({ ...n }))
  simEdges = graphData.value.edges.map(e => ({
    source: e.source,
    target: e.target
  }))

  createSimulation(width, height)
  renderGraph()
}

function createSimulation(width: number, height: number) {
  if (simulation) {
    simulation.stop()
  }

  simulation = d3.forceSimulation<SimNode>(simNodes)
    .force('link', d3.forceLink<SimNode, d3.SimulationLinkDatum<SimNode>>(simEdges)
      .id(d => d.id)
      .distance(120)
      .strength(0.5))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(50))
    .on('tick', ticked)
}

function ticked() {
  svg?.select('.edges-layer')
    .selectAll('line')
    .attr('x1', d => (d as any).source.x)
    .attr('y1', d => (d as any).source.y)
    .attr('x2', d => (d as any).target.x)
    .attr('y2', d => (d as any).target.y)

  svg?.select('.nodes-layer')
    .selectAll('g.node-group')
    .attr('transform', d => `translate(${(d as any).x}, ${(d as any).y})`)
}

function renderGraph() {
  if (!svg) return

  const edgesLayer = svg.select('.edges-layer')
  const nodesLayer = svg.select('.nodes-layer')

  edgesLayer.selectAll('*').remove()
  nodesLayer.selectAll('*').remove()

  edgesLayer.selectAll('line')
    .data(simEdges)
    .enter()
    .append('line')
    .attr('class', 'edge')
    .attr('stroke', 'rgba(255, 255, 255, 0.15)')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrow)')

  nodesLayer.selectAll<SVGGElement, SimNode>('g.node-group')
    .data(simNodes)
    .enter()
    .append('g')
    .attr('class', 'node-group')
    .style('cursor', 'pointer')
    .call(d3.drag<SVGGElement, SimNode>()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded))
    .on('click', (_, d) => selectNode(d))
    .append('circle')
    .attr('class', 'node-bg')
    .attr('r', d => getNodeRadius(d))
    .attr('fill', d => getNodeColor(d))
    .attr('stroke', 'rgba(255, 255, 255, 0.2)')
    .attr('stroke-width', 2)

  nodesLayer.selectAll<SVGGElement, SimNode>('g.node-group')
    .append('circle')
    .attr('class', 'node-inner')
    .attr('r', d => getNodeRadius(d) * 0.6)
    .attr('fill', d => d3.color(getNodeColor(d))?.brighter(0.5)?.toString() || getNodeColor(d))

  nodesLayer.selectAll<SVGGElement, SimNode>('g.node-group')
    .append('text')
    .attr('class', 'node-label')
    .attr('dy', d => getNodeRadius(d) + 16)
    .attr('text-anchor', 'middle')
    .attr('fill', 'rgba(255, 255, 255, 0.8)')
    .attr('font-size', '12px')
    .attr('font-weight', '500')
    .text(d => truncateText(d.label, 12))

  function dragStarted(event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, d: SimNode) {
    if (!event.active && simulation) {
      simulation.alphaTarget(0.3).restart()
    }
    d.fx = d.x
    d.fy = d.y
  }

  function dragged(event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, d: SimNode) {
    d.fx = event.x
    d.fy = event.y
  }

  function dragEnded(event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, d: SimNode) {
    if (!event.active && simulation) {
      simulation.alphaTarget(0)
    }
    d.fx = null
    d.fy = null
  }
}

function getNodeRadius(node: GraphNode): number {
  const connections = getNodeConnections(node.id)
  return Math.max(20, Math.min(40, 15 + connections * 3))
}

function getNodeColor(node: GraphNode): string {
  const type = nodeTypes.find(t => t.id === node.type)
  return type?.color || '#6b7280'
}

function getNodeConnections(nodeId: string): number {
  return edges.value.filter(e => e.source === nodeId || e.target === nodeId).length
}

function truncateText(text: string, maxLength: number): string {
  return text.length > maxLength ? text.slice(0, maxLength) + '...' : text
}

function selectNode(node: SimNode) {
  selectedNode.value = node
  
  svg?.select('.nodes-layer')
    .selectAll('g.node-group')
    .select('.node-bg')
    .attr('stroke-width', d => (d as SimNode).id === node.id ? 4 : 2)
    .attr('stroke', d => (d as SimNode).id === node.id ? '#fff' : 'rgba(255, 255, 255, 0.2)')
}

function openNote(id: string) {
  router.push(`/notes/${id}`)
}

function goHome() {
  router.push('/')
}

function setLayout(newLayout: 'force' | 'radial') {
  layout.value = newLayout
  if (!graphContainer.value || !simulation) return

  const width = graphContainer.value.clientWidth
  const height = graphContainer.value.clientHeight

  if (newLayout === 'radial') {
    simulation.force('center', null)
    simulation.force('r', d3.forceRadial<SimNode>(d => {
      const connections = getNodeConnections(d.id)
      return connections * 50 + 100
    }, width / 2, height / 2).strength(0.8))
  } else {
    simulation.force('r', null)
    simulation.force('center', d3.forceCenter(width / 2, height / 2))
  }
  simulation.alpha(1).restart()
}

function filterNodes() {
  simNodes.forEach(n => {
    n.filtered = !activeTypes.value.includes(n.type)
  })
  
  svg?.select('.nodes-layer')
    .selectAll('g.node-group')
    .style('opacity', d => (d as SimNode).filtered ? 0.1 : 1)
  
  svg?.select('.edges-layer')
    .selectAll('line')
    .style('opacity', d => {
      const source = simNodes.find(n => n.id === (d as any).source.id || (d as any).source)
      const target = simNodes.find(n => n.id === (d as any).target.id || (d as any).target)
      return (source?.filtered || target?.filtered) ? 0.05 : 1
    })
}

function getTypeCount(typeId: string): number {
  return nodes.value.filter(n => n.type === typeId).length
}

function zoomIn() {
  if (!svg || !zoom) return
  svg.transition().call(zoom.scaleBy as any, 1.3)
}

function zoomOut() {
  if (!svg || !zoom) return
  svg.transition().call(zoom.scaleBy as any, 0.7)
}

function resetZoom() {
  if (!svg || !zoom) return
  svg.transition().call(zoom.transform as any, d3.zoomIdentity)
}

watch(searchQuery, (query) => {
  const lowerQuery = query.toLowerCase()
  
  svg?.select('.nodes-layer')
    .selectAll('g.node-group')
    .style('opacity', d => {
      const node = d as SimNode
      if (!query) return node.filtered ? 0.1 : 1
      const matches = node.label.toLowerCase().includes(lowerQuery)
      return matches ? 1 : 0.1
    })
})
</script>

<style scoped lang="scss">
.graph-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0a0b;
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #141416;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.2);
    color: #fff;
  }
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.node-count {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.toolbar-center {
  flex: 1;
  max-width: 400px;
  margin: 0 24px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.5);

  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    color: #fff;
    font-size: 13px;
    outline: none;

    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }
  }
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.layout-switch {
  display: flex;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  padding: 4px;
}

.layout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: rgba(255, 255, 255, 0.8);
  }

  &.active {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #fff;
  }
}

.zoom-level {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  min-width: 40px;
  text-align: center;
}

.graph-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.graph-sidebar {
  width: 260px;
  background: #0f0f11;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 20px;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.type-filters {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.type-filter {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  input {
    display: none;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  &.active {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.12);
  }
}

.type-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.type-name {
  flex: 1;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.type-count {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.selected-info {
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
}

.selected-header {
  margin-bottom: 16px;
}

.selected-type {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.selected-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 6px 0 0;
}

.selected-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.open-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px;
  background: #f59e0b;
  border: none;
  border-radius: 8px;
  color: #000;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #fbbf24;
  }
}

.empty-selection {
  padding: 24px;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
}

.tips-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.graph-svg {
  width: 100%;
  height: 100%;
  background: #0a0a0b;

  :deep(.node-group) {
    transition: opacity 0.3s ease;

    &:hover .node-bg {
      filter: brightness(1.2);
    }
  }

  :deep(.edge) {
    transition: opacity 0.3s ease;
  }

  :deep(.arrow-path) {
    fill: rgba(255, 255, 255, 0.3);
  }
}

.graph-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: rgba(10, 10, 11, 0.9);
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #f59e0b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: rgba(255, 255, 255, 0.3);

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
  }

  p {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.3);
    margin: 0;
  }
}
</style>
