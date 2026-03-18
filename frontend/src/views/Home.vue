<template>
  <div class="home-page" ref="homeRef" @mousemove="handleMouseMove">
    <canvas ref="particleCanvas" class="particle-canvas"></canvas>
    
    <div class="home-content">
      <div class="main-area">
        <div class="header-section animate-fade-in-up">
          <h1 class="main-title">
            <span class="title-greeting">{{ timeGreeting }}</span>
            <span class="title-name">{{ username }}</span>
          </h1>
          <p class="subtitle">探索你的知识宇宙</p>
        </div>

        <div class="search-section animate-fade-in-up stagger-1" :class="{ focused: searchFocused }">
          <div class="search-wrapper">
            <Search class="search-icon" :size="20" />
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              type="text"
              placeholder="搜索笔记、标签、链接..."
              class="search-input"
              @focus="handleSearchFocus"
              @blur="handleSearchBlur"
              @keyup.enter="handleSearch"
            />
            <kbd class="search-shortcut">⌘K</kbd>
          </div>
          <Transition name="tag-cloud">
            <div v-if="searchFocused && popularTags.length > 0" class="tag-cloud">
              <span class="tag-label">热门标签：</span>
              <button
                v-for="tag in popularTags"
                :key="tag.id"
                class="tag-item"
                @click="searchByTag(tag.name)"
              >
                {{ tag.name }}
              </button>
            </div>
          </Transition>
        </div>

        <div class="categories-section animate-fade-in-up stagger-2">
          <div class="section-header">
            <h2 class="section-title">知识分类</h2>
            <span class="section-count">{{ categories.length }}</span>
          </div>
          <div class="category-grid">
            <div
              v-for="(category, index) in categories"
              :key="category.id"
              class="category-card"
              :style="{ '--delay': `${index * 0.05}s` }"
              @click="enterCategory(category)"
            >
              <div class="card-glow" :style="{ background: getCategoryColor(category.name) }"></div>
              <div class="card-content">
                <div class="card-header">
                  <div class="card-icon" :style="{ 
                    backgroundColor: getCategoryColor(category.name) + '20',
                    color: getCategoryColor(category.name)
                  }">
                    <component :is="getCategoryIcon(category.name)" :size="24" />
                  </div>
                  <div class="card-stats">
                    <span class="stat">
                      <Folder :size="14" />
                      {{ getFolderCount(category.id) }}
                    </span>
                    <span class="stat">
                      <FileText :size="14" />
                      {{ getContentCount(category.id) }}
                    </span>
                  </div>
                </div>
                <h3 class="card-title">{{ category.name }}</h3>
                <p class="card-desc">{{ getCategoryDesc(category.name) }}</p>
              </div>
              <div class="card-hover-content">
                <p class="hover-text">点击进入 →</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="side-area">
        <div class="graph-section animate-fade-in-up stagger-3">
          <div class="section-header">
            <h2 class="section-title">知识图谱</h2>
            <button class="expand-btn" @click="goToGraph">
              <Expand :size="16" />
            </button>
          </div>
          <div class="graph-container" ref="graphContainerRef">
            <canvas ref="graphCanvas" class="graph-canvas"></canvas>
            <div class="graph-overlay">
              <span class="graph-label">{{ totalNodes }} 个节点</span>
              <span class="graph-label">{{ totalLinks }} 条连接</span>
            </div>
          </div>
        </div>

        <div class="recent-section animate-fade-in-up stagger-4">
          <div class="section-header">
            <h2 class="section-title">最近编辑</h2>
            <button class="view-all-btn" @click="goToSearch">查看全部</button>
          </div>
          <div class="recent-list">
            <div
              v-for="note in recentNotes"
              :key="note.id"
              class="recent-item"
              @click="openNote(note.id)"
            >
              <div class="recent-dot"></div>
              <div class="recent-info">
                <span class="recent-title">{{ note.title }}</span>
                <span class="recent-meta">
                  <Clock :size="12" />
                  {{ formatDate(note.updated_at) }}
                </span>
              </div>
            </div>
            <div v-if="recentNotes.length === 0" class="empty-recent">
              <FileText :size="24" class="empty-icon" />
              <p>暂无笔记</p>
              <p class="empty-hint">创建第一篇笔记开始记录</p>
            </div>
          </div>
        </div>

        <div class="quick-actions animate-fade-in-up stagger-5">
          <button class="action-btn" @click="goToSearch">
            <Search :size="18" />
            <span>全局搜索</span>
          </button>
          <button class="action-btn" @click="goToSkills">
            <Zap :size="18" />
            <span>智能模块</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { useFoldersStore } from '@/stores/folders'
import { useNotesStore } from '@/stores/notes'
import { useTagsStore } from '@/stores/tags'
import { useAuthStore } from '@/stores/auth'
import { 
  Search, FileText, Folder, Clock, Zap, Expand,
  User, Briefcase, TrendingUp, BookOpen, Code, Lightbulb
} from 'lucide-vue-next'

const router = useRouter()
const categoryStore = useCategoryStore()
const foldersStore = useFoldersStore()
const notesStore = useNotesStore()
const tagsStore = useTagsStore()
const authStore = useAuthStore()

const homeRef = ref<HTMLElement | null>(null)
const particleCanvas = ref<HTMLCanvasElement | null>(null)
const graphCanvas = ref<HTMLCanvasElement | null>(null)
const graphContainerRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

const searchQuery = ref('')
const searchFocused = ref(false)
const mouseX = ref(0)
const mouseY = ref(0)

let particleAnimationId: number | null = null
let graphAnimationId: number | null = null
let particles: Particle[] = []
let graphNodes: GraphNode[] = []
let graphEdges: GraphEdge[] = []

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  baseX: number
  baseY: number
}

interface GraphNode {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  color: string
  label: string
}

interface GraphEdge {
  source: number
  target: number
}

const categories = computed(() => categoryStore.categories)
const username = computed(() => authStore.user?.username || '用户')
const popularTags = computed(() => tagsStore.tags.slice(0, 5))
const recentNotes = computed(() => notesStore.notes.slice(0, 5))

const totalNotes = computed(() => notesStore.notes.length)
const totalFolders = computed(() => foldersStore.folders.length)

const totalLinks = computed(() => {
  let count = 0
  notesStore.notes.forEach(note => {
    const matches = note.content?.match(/\[\[([^\]]+)\]\]/g) || []
    count += matches.length
  })
  return count
})

const totalNodes = computed(() => notesStore.notes.length + categories.value.length)

const timeGreeting = computed(() => {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 12) return '早安'
  if (hour >= 12 && hour < 18) return '午安'
  if (hour >= 18 && hour < 22) return '傍晚好'
  return '夜深了'
})

function getCategoryIcon(name: string) {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return User
  if (nameLower.includes('工作')) return Briefcase
  if (nameLower.includes('素材')) return TrendingUp
  if (nameLower.includes('学习')) return BookOpen
  if (nameLower.includes('代码')) return Code
  if (nameLower.includes('灵感')) return Lightbulb
  return Folder
}

function getCategoryColor(name: string): string {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return '#f59e0b'
  if (nameLower.includes('工作')) return '#3b82f6'
  if (nameLower.includes('素材')) return '#10b981'
  if (nameLower.includes('学习')) return '#8b5cf6'
  if (nameLower.includes('代码')) return '#06b6d4'
  if (nameLower.includes('灵感')) return '#ec4899'
  return '#0066FF'
}

function getCategoryDesc(name: string): string {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return '笔记、日记、灵感收集'
  if (nameLower.includes('工作')) return '项目文档、任务管理'
  if (nameLower.includes('素材')) return '图片、链接、附件'
  if (nameLower.includes('学习')) return '学习笔记、知识整理'
  if (nameLower.includes('代码')) return '代码片段、技术文档'
  if (nameLower.includes('灵感')) return '创意想法、灵感记录'
  return '内容管理'
}

function getFolderCount(categoryId: string): number {
  return foldersStore.folders.filter(f => f.category_id === categoryId).length
}

function getContentCount(categoryId: string): number {
  return categoryStore.contents.filter(c => c.category_id === categoryId).length
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function handleMouseMove(e: MouseEvent) {
  if (!homeRef.value) return
  const rect = homeRef.value.getBoundingClientRect()
  mouseX.value = e.clientX - rect.left
  mouseY.value = e.clientY - rect.top
}

function handleSearchFocus() {
  searchFocused.value = true
}

function handleSearchBlur() {
  setTimeout(() => {
    searchFocused.value = false
  }, 200)
}

function handleSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } })
  }
}

function searchByTag(tagName: string) {
  router.push({ path: '/search', query: { q: tagName } })
}

function enterCategory(category: any) {
  categoryStore.currentCategory = category
  router.push(`/categories/${category.id}`)
}

function openNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}

function goToSearch() {
  router.push('/search')
}

function goToGraph() {
  router.push('/graph')
}

function goToSkills() {
  router.push('/skills')
}

function initParticles() {
  const canvas = particleCanvas.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    createParticles()
  }
  
  const createParticles = () => {
    particles = []
    const count = Math.min(80, Math.floor((canvas.width * canvas.height) / 15000))
    
    for (let i = 0; i < count; i++) {
      const x = Math.random() * canvas.width
      const y = Math.random() * canvas.height
      particles.push({
        x,
        y,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 2 + 1,
        baseX: x,
        baseY: y
      })
    }
  }
  
  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    particles.forEach((p, i) => {
      const dx = mouseX.value - p.x
      const dy = mouseY.value - p.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      
      if (dist < 150) {
        const force = (150 - dist) / 150
        p.vx += dx * force * 0.002
        p.vy += dy * force * 0.002
      }
      
      p.x += p.vx
      p.y += p.vy
      
      p.vx *= 0.99
      p.vy *= 0.99
      
      p.x += (p.baseX - p.x) * 0.01
      p.y += (p.baseY - p.y) * 0.01
      
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(0, 102, 255, 0.6)'
      ctx.fill()
      
      particles.slice(i + 1).forEach(p2 => {
        const dx2 = p.x - p2.x
        const dy2 = p.y - p2.y
        const dist2 = Math.sqrt(dx2 * dx2 + dy2 * dy2)
        
        if (dist2 < 120) {
          ctx.beginPath()
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.strokeStyle = `rgba(0, 102, 255, ${0.15 * (1 - dist2 / 120)})`
          ctx.lineWidth = 0.5
          ctx.stroke()
        }
      })
    })
    
    particleAnimationId = requestAnimationFrame(animate)
  }
  
  resize()
  window.addEventListener('resize', resize)
  animate()
}

function initGraph() {
  const canvas = graphCanvas.value
  const container = graphContainerRef.value
  if (!canvas || !container) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const resize = () => {
    const rect = container.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
    createNodes()
  }
  
  const createNodes = () => {
    graphNodes = []
    graphEdges = []
    
    const colors = ['#0066FF', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4']
    const nodeCount = Math.min(20, totalNotes.value + 5)
    
    for (let i = 0; i < nodeCount; i++) {
      graphNodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: Math.random() * 4 + 3,
        color: colors[i % colors.length],
        label: `Node ${i}`
      })
    }
    
    for (let i = 0; i < nodeCount; i++) {
      const connections = Math.floor(Math.random() * 3) + 1
      for (let j = 0; j < connections; j++) {
        const target = Math.floor(Math.random() * nodeCount)
        if (target !== i) {
          graphEdges.push({ source: i, target })
        }
      }
    }
  }
  
  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    graphEdges.forEach(edge => {
      const source = graphNodes[edge.source]
      const target = graphNodes[edge.target]
      
      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
      ctx.lineWidth = 1
      ctx.stroke()
    })
    
    graphNodes.forEach(node => {
      node.x += node.vx
      node.y += node.vy
      
      if (node.x < node.radius || node.x > canvas.width - node.radius) {
        node.vx *= -1
      }
      if (node.y < node.radius || node.y > canvas.height - node.radius) {
        node.vy *= -1
      }
      
      node.x = Math.max(node.radius, Math.min(canvas.width - node.radius, node.x))
      node.y = Math.max(node.radius, Math.min(canvas.height - node.radius, node.y))
      
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
      ctx.fillStyle = node.color
      ctx.fill()
      
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius + 2, 0, Math.PI * 2)
      ctx.strokeStyle = node.color + '40'
      ctx.lineWidth = 2
      ctx.stroke()
    })
    
    graphAnimationId = requestAnimationFrame(animate)
  }
  
  resize()
  window.addEventListener('resize', resize)
  animate()
}

function cleanup() {
  if (particleAnimationId) {
    cancelAnimationFrame(particleAnimationId)
  }
  if (graphAnimationId) {
    cancelAnimationFrame(graphAnimationId)
  }
}

onMounted(async () => {
  await Promise.all([
    categoryStore.fetchCategories(),
    foldersStore.fetchFolders(),
    categoryStore.fetchContents(),
    notesStore.fetchNotes(),
    tagsStore.fetchTags()
  ])
  
  await nextTick()
  initParticles()
  initGraph()
  
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      searchInputRef.value?.focus()
    }
  })
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped lang="scss">
.home-page {
  position: relative;
  min-height: 100%;
  background: var(--bg-deep);
  overflow: hidden;
}

.particle-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.home-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100%;
}

.main-area {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.header-section {
  text-align: center;
  padding: 40px 0 20px;
}

.main-title {
  font-family: 'Exo 2', 'Noto Sans SC', sans-serif;
  font-size: 48px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 12px;
  background: linear-gradient(135deg, #ffffff 0%, rgba(255, 255, 255, 0.7) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  
  .title-greeting {
    display: block;
    font-size: 20px;
    font-weight: 400;
    color: var(--text-tertiary);
    -webkit-text-fill-color: var(--text-tertiary);
    margin-bottom: 4px;
  }
  
  .title-name {
    display: block;
  }
}

.subtitle {
  font-size: 16px;
  color: var(--text-muted);
  margin: 0;
}

.search-section {
  position: relative;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-xl);
  transition: all 0.3s ease;
  
  .search-icon {
    color: var(--text-muted);
    flex-shrink: 0;
  }
  
  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    font-size: 16px;
    color: var(--text-primary);
    
    &::placeholder {
      color: var(--text-muted);
    }
  }
  
  .search-shortcut {
    padding: 4px 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
}

.search-section.focused .search-wrapper {
  border-color: var(--tech-blue);
  box-shadow: 0 0 0 3px var(--tech-blue-muted), 0 8px 32px rgba(0, 0, 0, 0.3);
  background: rgba(255, 255, 255, 0.05);
}

.tag-cloud {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  margin-top: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-lg);
  flex-wrap: wrap;
  
  .tag-label {
    font-size: 12px;
    color: var(--text-muted);
  }
  
  .tag-item {
    padding: 6px 12px;
    background: var(--tech-blue-muted);
    border: 1px solid rgba(0, 102, 255, 0.3);
    border-radius: 20px;
    font-size: 12px;
    color: var(--tech-blue);
    transition: all 0.2s;
    
    &:hover {
      background: rgba(0, 102, 255, 0.25);
      transform: translateY(-1px);
    }
  }
}

.tag-cloud-enter-active,
.tag-cloud-leave-active {
  transition: all 0.3s ease;
}

.tag-cloud-enter-from,
.tag-cloud-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.categories-section {
  flex: 1;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-family: 'Exo 2', 'Noto Sans SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.section-count {
  font-size: 12px;
  color: var(--text-muted);
  padding: 2px 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.category-card {
  position: relative;
  padding: 24px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  animation: fade-in-up 0.4s ease-out backwards;
  animation-delay: var(--delay);
  
  .card-glow {
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    opacity: 0;
    transition: opacity 0.3s;
    filter: blur(60px);
    pointer-events: none;
  }
  
  .card-content {
    position: relative;
    z-index: 1;
  }
  
  .card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  
  .card-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-lg);
  }
  
  .card-stats {
    display: flex;
    gap: 12px;
    
    .stat {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: var(--text-muted);
    }
  }
  
  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px;
  }
  
  .card-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.5;
  }
  
  .card-hover-content {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.7);
    opacity: 0;
    transition: opacity 0.3s;
    
    .hover-text {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
    }
  }
  
  &:hover {
    transform: translateY(-4px);
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
    
    .card-glow {
      opacity: 0.15;
    }
    
    .card-hover-content {
      opacity: 1;
    }
  }
}

.side-area {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.graph-section {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-xl);
  padding: 20px;
  
  .expand-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border-radius: var(--radius-md);
    color: var(--text-muted);
    transition: all 0.2s;
    
    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: var(--text-primary);
    }
  }
}

.graph-container {
  position: relative;
  height: 200px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-top: 12px;
  background: rgba(0, 0, 0, 0.3);
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

.graph-overlay {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  gap: 12px;
  
  .graph-label {
    font-size: 11px;
    color: var(--text-muted);
    padding: 4px 8px;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 4px;
  }
}

.recent-section {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-xl);
  padding: 20px;
  
  .view-all-btn {
    font-size: 12px;
    color: var(--tech-blue);
    transition: color 0.2s;
    
    &:hover {
      color: var(--primary-color);
    }
  }
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
}

.recent-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(255, 255, 255, 0.04);
    
    .recent-dot {
      background: var(--tech-blue);
      box-shadow: 0 0 8px var(--tech-blue-glow);
    }
  }
  
  .recent-dot {
    width: 6px;
    height: 6px;
    margin-top: 6px;
    border-radius: 50%;
    background: var(--text-muted);
    flex-shrink: 0;
    transition: all 0.2s;
  }
  
  .recent-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .recent-title {
    font-size: 13px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .recent-meta {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--text-muted);
  }
}

.empty-recent {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  
  .empty-icon {
    color: var(--text-muted);
    margin-bottom: 12px;
  }
  
  p {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }
  
  .empty-hint {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
    opacity: 0.7;
  }
}

.quick-actions {
  display: flex;
  gap: 8px;
  
  .action-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: var(--radius-lg);
    color: var(--text-secondary);
    font-size: 13px;
    transition: all 0.2s;
    
    &:hover {
      background: rgba(255, 255, 255, 0.06);
      border-color: rgba(255, 255, 255, 0.1);
      color: var(--text-primary);
    }
  }
}

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .home-content {
    grid-template-columns: 1fr;
    padding: 24px;
  }
  
  .side-area {
    flex-direction: row;
    flex-wrap: wrap;
    
    > * {
      flex: 1;
      min-width: 280px;
    }
  }
  
  .graph-section {
    order: -1;
  }
}

@media (max-width: 640px) {
  .home-content {
    padding: 16px;
  }
  
  .main-title {
    font-size: 32px;
    
    .title-greeting {
      font-size: 16px;
    }
  }
  
  .category-grid {
    grid-template-columns: 1fr;
  }
  
  .side-area {
    flex-direction: column;
    
    > * {
      min-width: auto;
    }
  }
}
</style>
