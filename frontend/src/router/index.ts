import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
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
        path: 'categories',
        name: 'Categories',
        component: () => import('@/views/CategoryView.vue')
      },
      {
        path: 'categories/:categoryId',
        name: 'CategoryDetail',
        component: () => import('@/views/CategoryView.vue')
      },
      {
        path: 'categories/:categoryId/content/new',
        name: 'NewContent',
        component: () => import('@/views/ContentEditor.vue')
      },
      {
        path: 'categories/:categoryId/content/:id',
        name: 'ContentEditor',
        component: () => import('@/views/ContentEditor.vue')
      },
      {
        path: 'personal/folders',
        name: 'PersonalFolders',
        component: () => import('@/views/Home.vue')
      },
      {
        path: 'personal/search',
        name: 'PersonalSearch',
        component: () => import('@/views/SearchResults.vue')
      },
      {
        path: 'personal/graph',
        name: 'PersonalGraph',
        component: () => import('@/views/GraphView.vue')
      },
      {
        path: 'personal/ai',
        name: 'PersonalAI',
        component: () => import('@/views/AIAssistant.vue')
      },
      {
        path: 'work',
        name: 'Work',
        component: () => import('@/views/Home.vue')
      },
      {
        path: 'assets',
        name: 'Assets',
        component: () => import('@/views/Home.vue')
      },
      {
        path: 'graph',
        name: 'Graph',
        component: () => import('@/views/GraphView.vue')
      },
      {
        path: 'skills',
        name: 'Skills',
        component: () => import('@/views/SkillsView.vue')
      },
      {
        path: 'prompt-lab',
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
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
