import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'
import MainLayout from '../MainLayout.vue'

vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ fetchUser: () => Promise.resolve() }) }))
vi.mock('@/stores/folders', () => ({ useFoldersStore: () => ({ fetchFolders: () => Promise.resolve() }) }))
vi.mock('@/stores/tags', () => ({ useTagsStore: () => ({ fetchTags: () => Promise.resolve() }) }))
vi.mock('@/stores/notes', () => ({ useNotesStore: () => ({ fetchNotes: () => Promise.resolve() }) }))

const ThrowingPage = defineComponent({
  setup() {
    throw new Error('page render boom')
  },
  template: '<div>不应出现</div>'
})

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'Home', component: ThrowingPage }]
  })
}

describe('MainLayout 错误隔离', () => {
  it('页面组件抛错时只替换内容区，导航与顶栏仍可用', async () => {
    const router = makeRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(MainLayout, {
      global: {
        plugins: [router],
        stubs: {
          AppRail: { template: '<nav>导航仍在</nav>' },
          TopBar: { template: '<header>顶栏仍在</header>' },
          MobileNav: true,
          CommandHost: true,
          AppDrawer: { template: '<div><slot /></div>', props: ['open'] },
          StarField: true
        }
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('此区域加载失败')
    expect(wrapper.text()).toContain('导航仍在')
    expect(wrapper.text()).toContain('顶栏仍在')
    expect(wrapper.text()).not.toContain('不应出现')

    wrapper.unmount()
  })
})
