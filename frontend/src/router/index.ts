import { createRouter, createWebHistory, type RouteLocation, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/**
 * 信息架构（设计文档 §5.2）
 * - 图标栏主入口：/ 观测台、/library 我的笔记、/graph 图谱、/ai AI 助手
 * - LAB 组：/lab、/skills、/prompts、/ai/observability
 * - 旧路由一律重定向，保留书签与外部链接可用性
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/Home.vue')
      },
      {
        path: 'notes/new',
        name: 'NewNote',
        component: () => import('@/views/NoteEditor.vue')
      },
      {
        path: 'notes/:id',
        name: 'NoteEditor',
        component: () => import('@/views/NoteEditor.vue')
      },
      {
        path: 'library',
        name: 'Library',
        component: () => import('@/views/CategoryView.vue')
      },
      {
        path: 'library/:categoryId',
        name: 'LibraryDetail',
        component: () => import('@/views/CategoryView.vue')
      },
      {
        path: 'library/:categoryId/content/new',
        name: 'NewContent',
        component: () => import('@/views/ContentEditor.vue')
      },
      {
        path: 'library/:categoryId/content/:id',
        name: 'ContentEditor',
        component: () => import('@/views/ContentEditor.vue')
      },
      {
        path: 'graph',
        name: 'Graph',
        component: () => import('@/views/GraphView.vue')
      },
      {
        path: 'ai',
        name: 'AIAssistant',
        component: () => import('@/views/AIAssistant.vue')
      },
      {
        path: 'ai/observability',
        name: 'AgentObservability',
        component: () => import('@/views/AgentObservability.vue')
      },
      {
        path: 'skills',
        name: 'Skills',
        component: () => import('@/views/SkillsView.vue')
      },
      {
        path: 'lab',
        name: 'PromptLab',
        component: () => import('@/views/PromptLab.vue')
      },
      {
        path: 'prompts',
        name: 'Prompts',
        component: () => import('@/views/PromptsView.vue')
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/SearchResults.vue')
      },
      {
        path: 'import-history',
        name: 'ImportHistory',
        component: () => import('@/views/ImportHistory.vue')
      },
      {
        path: 'dev/ui',
        name: 'DevUI',
        component: () => import('@/views/DevUI.vue')
      }
    ]
  },

  // ---- 旧路由重定向（P0 清理，不保留别名页面） ----
  { path: '/categories', redirect: '/library' },
  {
    path: '/categories/:categoryId',
    redirect: (to: RouteLocation) => ({ name: 'LibraryDetail', params: { categoryId: to.params.categoryId } })
  },
  {
    path: '/categories/:categoryId/content/new',
    redirect: (to: RouteLocation) => ({ name: 'NewContent', params: { categoryId: to.params.categoryId } })
  },
  {
    path: '/categories/:categoryId/content/:id',
    redirect: (to: RouteLocation) => ({
      name: 'ContentEditor',
      params: { categoryId: to.params.categoryId, id: to.params.id }
    })
  },
  { path: '/personal/folders', redirect: { path: '/library', query: { area: 'personal' } } },
  { path: '/work', redirect: { path: '/library', query: { area: 'work' } } },
  { path: '/assets', redirect: { path: '/library', query: { area: 'assets' } } },
  { path: '/personal/graph', redirect: '/graph' },
  { path: '/personal/ai', redirect: '/ai' },
  { path: '/personal/search', redirect: '/search' },
  { path: '/prompt-lab', redirect: '/lab' },
  { path: '/observability', redirect: '/ai/observability' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

function isTokenExpired(): boolean {
  const token = localStorage.getItem('token')
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && (!authStore.isAuthenticated || isTokenExpired())) {
    authStore.logout()
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated && !isTokenExpired()) {
    next('/')
  } else {
    next()
  }
})

export default router
