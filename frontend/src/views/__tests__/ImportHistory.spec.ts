import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ImportHistory from '../ImportHistory.vue'

const store = vi.hoisted(() => ({
  history: [] as any[],
  historyTotal: 0,
  historyLoading: false,
  fetchHistory: vi.fn(),
  openImportModal: vi.fn()
}))

vi.mock('@/stores/import', () => ({ useImportStore: () => store }))

const item = {
  id: 'i1',
  task_id: 't1',
  source_type: 'pdf',
  source_filename: '手册.pdf',
  generated_title: '部署手册',
  note_id: 'n1',
  status: 'completed',
  created_at: '2026-01-02T00:00:00'
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/import-history', component: ImportHistory },
      { path: '/notes/:id', component: { template: '<div>笔记</div>' } }
    ]
  })
}

async function mountHistory() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = makeRouter()
  await router.push('/import-history')
  await router.isReady()

  const wrapper = mount(ImportHistory, {
    global: {
      plugins: [pinia, router],
      stubs: {
        AppSelect: {
          props: ['modelValue', 'options'],
          template: `<select class="stub-select" :value="modelValue" @change="$emit('update:modelValue', $event.target.value)">
            <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>`
        }
      }
    }
  })
  await flushPromises()
  return { wrapper, router }
}

describe('ImportHistory 视图', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.history = [item]
    store.historyTotal = 1
    store.historyLoading = false
  })

  it('挂载时按 all 哨兵请求第一页', async () => {
    const { wrapper } = await mountHistory()

    expect(store.fetchHistory).toHaveBeenCalledWith({
      source_type: undefined,
      page: 1,
      page_size: 20
    })
    expect(wrapper.text()).toContain('部署手册')
    wrapper.unmount()
  })

  it('切换来源过滤时重置页码并带上 source_type', async () => {
    store.historyTotal = 45
    const { wrapper } = await mountHistory()

    await wrapper.find('select.stub-select').setValue('pdf')
    await flushPromises()

    expect(store.fetchHistory).toHaveBeenLastCalledWith({
      source_type: 'pdf',
      page: 1,
      page_size: 20
    })
    wrapper.unmount()
  })

  it('分页按钮切换页码并重新请求', async () => {
    store.historyTotal = 45
    const { wrapper } = await mountHistory()

    expect(wrapper.text()).toContain('1 / 3')
    const next = wrapper.findAll('.imports__pager button').find(button => button.text() === '下一页')
    expect(next).toBeDefined()
    await next!.trigger('click')
    await flushPromises()

    expect(store.fetchHistory).toHaveBeenLastCalledWith({
      source_type: undefined,
      page: 2,
      page_size: 20
    })
    wrapper.unmount()
  })

  it('点击已关联笔记的记录跳到笔记', async () => {
    const { wrapper, router } = await mountHistory()

    await wrapper.find('button.import-row').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/notes/n1')
    wrapper.unmount()
  })
})
