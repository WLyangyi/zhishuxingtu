<template>
  <div class="graph-page">
    <div class="graph-header">
      <div class="header-left">
        <button @click="goHome" class="back-btn" title="返回主页">
          <span class="back-icon">←</span>
          <span class="back-text">主页</span>
        </button>
        <h2>知识图谱</h2>
      </div>
      <div class="graph-controls">
        <button @click="zoomIn">放大</button>
        <button @click="zoomOut">缩小</button>
        <button @click="resetView">重置</button>
      </div>
    </div>
    <div ref="graphContainer" class="graph-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { graphApi } from '@/api/graph'
import type { GraphData, GraphNode } from '@/types'

const router = useRouter()
const graphContainer = ref<HTMLDivElement>()
const graphData = ref<GraphData>({ nodes: [], edges: [] })

let graphInstance: any = null
let canvas: HTMLCanvasElement | null = null
let ctx: CanvasRenderingContext2D | null = null
let scale = 1
let offsetX = 0
let offsetY = 0
let isDragging = false
let lastMouseX = 0
let lastMouseY = 0

interface SimNode extends GraphNode {
  x: number
  y: number
  vx: number
  vy: number
}

let nodes: SimNode[] = []

onMounted(async () => {
  const response = await graphApi.getGlobal()
  graphData.value = response.data
  
  if (graphContainer.value) {
    renderGraph()
  }
})

function renderGraph() {
  if (!graphContainer.value) return
  
  const container = graphContainer.value
  const width = container.clientWidth
  const height = container.clientHeight
  
  canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  container.appendChild(canvas)
  
  ctx = canvas.getContext('2d')
  if (!ctx) return
  
  nodes = graphData.value.nodes.map(node => ({
    ...node,
    x: Math.random() * width,
    y: Math.random() * height,
    vx: 0,
    vy: 0
  }))
  
  const edges = graphData.value.edges
  
  function simulate() {
    nodes.forEach(node => {
      node.vx *= 0.9
      node.vy *= 0.9
      node.x += node.vx
      node.y += node.vy
      
      if (node.x < 50) { node.x = 50; node.vx *= -0.5 }
      if (node.x > width - 50) { node.x = width - 50; node.vx *= -0.5 }
      if (node.y < 50) { node.y = 50; node.vy *= -0.5 }
      if (node.y > height - 50) { node.y = height - 50; node.vy *= -0.5 }
    })
    
    nodes.forEach(n1 => {
      nodes.forEach(n2 => {
        if (n1.id === n2.id) return
        const dx = n2.x - n1.x
        const dy = n2.y - n1.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 100) {
          const force = (100 - dist) * 0.01
          n1.vx -= dx / dist * force
          n1.vy -= dy / dist * force
        }
      })
    })
    
    edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source)
      const target = nodes.find(n => n.id === edge.target)
      if (!source || !target) return
      
      const dx = target.x - source.x
      const dy = target.y - source.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      const force = (dist - 150) * 0.001
      
      source.vx += dx / dist * force
      source.vy += dy / dist * force
      target.vx -= dx / dist * force
      target.vy -= dy / dist * force
    })
  }
  
  function draw() {
    if (!ctx || !canvas) return
    
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.save()
    ctx.translate(offsetX, offsetY)
    ctx.scale(scale, scale)
    
    edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source)
      const target = nodes.find(n => n.id === edge.target)
      if (!source || !target) return
      
      ctx!.beginPath()
      ctx!.strokeStyle = 'rgba(100, 100, 100, 0.3)'
      ctx!.lineWidth = 1
      ctx!.moveTo(source.x, source.y)
      ctx!.lineTo(target.x, target.y)
      ctx!.stroke()
    })
    
    nodes.forEach(node => {
      ctx!.beginPath()
      ctx!.fillStyle = node.color
      ctx!.arc(node.x, node.y, node.size / 2, 0, Math.PI * 2)
      ctx!.fill()
      
      ctx!.fillStyle = '#ffffff'
      ctx!.font = '12px sans-serif'
      ctx!.textAlign = 'center'
      ctx!.fillText(node.label.slice(0, 10), node.x, node.y + node.size / 2 + 16)
    })
    
    ctx.restore()
  }
  
  function animate() {
    simulate()
    draw()
    graphInstance = requestAnimationFrame(animate)
  }
  
  animate()
  
  canvas.addEventListener('click', (e) => {
    const rect = canvas!.getBoundingClientRect()
    const x = (e.clientX - rect.left - offsetX) / scale
    const y = (e.clientY - rect.top - offsetY) / scale
    
    for (const node of nodes) {
      const dx = x - node.x
      const dy = y - node.y
      if (dx * dx + dy * dy < (node.size / 2) ** 2) {
        if (node.type === 'note') {
          router.push(`/notes/${node.id}`)
        }
        break
      }
    }
  })
  
  canvas.addEventListener('mousedown', (e) => {
    isDragging = true
    lastMouseX = e.clientX
    lastMouseY = e.clientY
  })
  
  canvas.addEventListener('mousemove', (e) => {
    if (!isDragging) return
    offsetX += e.clientX - lastMouseX
    offsetY += e.clientY - lastMouseY
    lastMouseX = e.clientX
    lastMouseY = e.clientY
  })
  
  canvas.addEventListener('mouseup', () => {
    isDragging = false
  })
  
  canvas.addEventListener('mouseleave', () => {
    isDragging = false
  })
  
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const newScale = Math.max(0.3, Math.min(3, scale * delta))
    
    const rect = canvas!.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top
    
    offsetX = mouseX - (mouseX - offsetX) * (newScale / scale)
    offsetY = mouseY - (mouseY - offsetY) * (newScale / scale)
    
    scale = newScale
  })
}

function goHome() {
  router.push('/')
}

function zoomIn() {
  scale = Math.min(3, scale * 1.2)
}

function zoomOut() {
  scale = Math.max(0.3, scale * 0.8)
}

function resetView() {
  scale = 1
  offsetX = 0
  offsetY = 0
}

onUnmounted(() => {
  if (graphInstance) {
    cancelAnimationFrame(graphInstance)
  }
})
</script>

<style scoped lang="scss">
.graph-page {
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  background: rgba(18, 18, 31, 0.8);
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  h2 {
    font-size: 20px;
    font-weight: 600;
  }
  
  .graph-controls {
    display: flex;
    gap: 8px;
    
    button {
      padding: 8px 16px;
      background: rgba(0, 212, 255, 0.1);
      border: 1px solid rgba(0, 212, 255, 0.2);
      border-radius: 8px;
      cursor: pointer;
      color: rgba(255, 255, 255, 0.8);
      transition: all 0.2s;
      
      &:hover {
        background: rgba(0, 212, 255, 0.2);
        border-color: rgba(0, 212, 255, 0.4);
        color: #00d4ff;
      }
    }
  }
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  color: #00d4ff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.2);
    border-color: rgba(0, 212, 255, 0.4);
    transform: translateX(-2px);
    
    .back-icon {
      transform: translateX(-3px);
    }
  }
  
  .back-icon {
    font-size: 16px;
    transition: transform 0.3s;
  }
  
  .back-text {
    font-weight: 500;
  }
}

.graph-container {
  flex: 1;
  background: linear-gradient(135deg, #0a0a14 0%, #0d0d1a 100%);
}
</style>
