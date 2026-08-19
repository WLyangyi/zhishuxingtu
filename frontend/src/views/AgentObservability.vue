<template>
  <div class="observability-page">
    <header class="page-header">
      <div>
        <div class="eyebrow"><Activity :size="15" /> M5 · Agent Observability</div>
        <h1>可观测面板</h1>
        <p>跟踪 Agent 会话、工具调用、延迟、成本与审批状态。</p>
      </div>
      <div class="header-controls">
        <select v-model="source" @change="loadTraces">
          <option value="auto">自动（Langfuse 优先）</option>
          <option value="local">本地审计数据</option>
          <option value="langfuse" :disabled="!summary?.langfuse_configured">Langfuse 云端</option>
        </select>
        <button :disabled="loading" @click="refresh"><RefreshCw :size="15" :class="{ spinning: loading }" /> 刷新</button>
      </div>
    </header>

    <div v-if="fallbackReason" class="fallback-banner">
      <CloudOff :size="15" /> Langfuse 暂不可用，已自动回退本地审计数据：{{ fallbackReason }}
    </div>

    <section class="metric-grid">
      <article class="metric-card">
        <span class="metric-icon purple"><MessagesSquare :size="18" /></span>
        <div><small>会话</small><strong>{{ summary?.sessions ?? 0 }}</strong></div>
      </article>
      <article class="metric-card">
        <span class="metric-icon blue"><Wrench :size="18" /></span>
        <div><small>工具调用</small><strong>{{ summary?.tool_calls ?? 0 }}</strong></div>
      </article>
      <article class="metric-card">
        <span class="metric-icon green"><Gauge :size="18" /></span>
        <div><small>平均工具延迟</small><strong>{{ summary?.avg_tool_latency_ms ?? 0 }}<em> ms</em></strong></div>
      </article>
      <article class="metric-card">
        <span class="metric-icon amber"><BadgeCheck :size="18" /></span>
        <div><small>成功率</small><strong>{{ successRate }}</strong></div>
      </article>
      <article class="metric-card">
        <span class="metric-icon red"><ShieldAlert :size="18" /></span>
        <div><small>待审批</small><strong>{{ summary?.pending_approvals ?? 0 }}</strong></div>
      </article>
      <article class="metric-card">
        <span class="metric-icon purple"><Brain :size="18" /></span>
        <div><small>长期偏好</small><strong>{{ summary?.preferences ?? 0 }}</strong></div>
      </article>
    </section>

    <section class="dashboard-grid">
      <article class="panel traces-panel">
        <div class="panel-header">
          <div><h2>Trace 列表</h2><span>{{ traceSourceLabel }} · {{ meta.total_items }} 条</span></div>
          <div class="legend"><i class="ok"></i>成功 <i class="pending"></i>待处理 <i class="error"></i>异常</div>
        </div>
        <div class="trace-table">
          <div class="trace-row table-head">
            <span>Trace / 会话</span><span>状态</span><span>延迟</span><span>Tokens</span><span>成本</span><span>工具</span>
          </div>
          <button v-for="trace in traces" :key="trace.id" class="trace-row" @click="selectTrace(trace)">
            <span class="trace-name"><b>{{ trace.name }}</b><small>{{ formatDate(trace.timestamp) }}</small></span>
            <span><i class="status-dot" :class="trace.status"></i>{{ statusLabel(trace.status) }}</span>
            <span class="mono">{{ formatLatency(trace.latency_ms) }}</span>
            <span class="mono">{{ formatNumber(trace.total_tokens) }}</span>
            <span class="mono">{{ formatCost(trace.total_cost) }}</span>
            <span class="tool-count">{{ trace.tool_calls }}</span>
          </button>
          <div v-if="!loading && traces.length === 0" class="empty-state">暂无 trace，先在 AI 助手发起一次对话。</div>
          <div v-if="loading" class="empty-state">正在加载可观测数据…</div>
        </div>
        <div v-if="meta.total_pages > 1" class="pagination">
          <button :disabled="meta.page <= 1" @click="changePage(meta.page - 1)">上一页</button>
          <span>{{ meta.page }} / {{ meta.total_pages }}</span>
          <button :disabled="meta.page >= meta.total_pages" @click="changePage(meta.page + 1)">下一页</button>
        </div>
      </article>

      <aside class="right-column">
        <article class="panel distribution-panel">
          <div class="panel-header"><div><h2>工具调用分布</h2><span>基于本地审计日志</span></div></div>
          <div v-if="summary?.tool_distribution.length" class="distribution-list">
            <div v-for="tool in summary.tool_distribution" :key="tool.name" class="distribution-item">
              <div><span>{{ tool.name }}</span><b>{{ tool.count }}</b></div>
              <div class="bar"><i :style="{ width: `${distributionWidth(tool.count)}%` }"></i></div>
            </div>
          </div>
          <div v-else class="empty-state compact">暂无工具调用</div>
        </article>

        <article class="panel detail-panel">
          <div class="panel-header">
            <div><h2>调用链详情</h2><span>{{ selectedTrace?.name || '选择左侧 trace' }}</span></div>
            <a v-if="selectedTrace?.url" :href="selectedTrace.url" target="_blank" rel="noopener">Langfuse <ExternalLink :size="12" /></a>
          </div>
          <AgentTimeline v-if="selectedTrace" :events="selectedTimeline" />
          <div v-else class="empty-state compact">点击 trace 查看工具链</div>
        </article>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Activity, BadgeCheck, Brain, CloudOff, ExternalLink, Gauge,
  MessagesSquare, RefreshCw, ShieldAlert, Wrench
} from 'lucide-vue-next'
import AgentTimeline from '@/components/agent/AgentTimeline.vue'
import {
  agentApi,
  type AgentTrace,
  type ObservabilitySummary,
  type TimelineEvent
} from '@/api/agent'

const loading = ref(false)
const source = ref('auto')
const traces = ref<AgentTrace[]>([])
const summary = ref<ObservabilitySummary | null>(null)
const fallbackReason = ref('')
const actualSource = ref<'local' | 'langfuse'>('local')
const meta = ref({ page: 1, limit: 20, total_items: 0, total_pages: 0 })
const selectedTrace = ref<AgentTrace | null>(null)
const selectedTimeline = ref<TimelineEvent[]>([])

const successRate = computed(() => `${Math.round((summary.value?.success_rate ?? 1) * 100)}%`)
const traceSourceLabel = computed(() => actualSource.value === 'langfuse' ? 'Langfuse 云端' : '本地审计')

async function loadTraces() {
  loading.value = true
  try {
    const result = await agentApi.getTraces(source.value, meta.value.page, meta.value.limit)
    traces.value = result.data
    meta.value = result.meta
    actualSource.value = result.source
    fallbackReason.value = result.fallback_reason || ''
  } finally {
    loading.value = false
  }
}

async function refresh() {
  const [summaryData] = await Promise.all([agentApi.getObservabilitySummary(), loadTraces()])
  summary.value = summaryData
}

async function changePage(page: number) {
  meta.value.page = page
  await loadTraces()
}

async function selectTrace(trace: AgentTrace) {
  selectedTrace.value = trace
  if (trace.session_id) {
    try {
      selectedTimeline.value = await agentApi.getTimeline(trace.session_id)
    } catch {
      selectedTimeline.value = [{ type: 'observation', content: '该 Langfuse trace 没有对应的本地工具日志。' }]
    }
  } else {
    selectedTimeline.value = [{ type: 'observation', content: '请在 Langfuse 中查看完整 observation/span。' }]
  }
}

function distributionWidth(count: number): number {
  const max = Math.max(...(summary.value?.tool_distribution.map(item => item.count) || [1]))
  return Math.max(5, (count / max) * 100)
}

function formatDate(value?: string): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function formatLatency(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${value} ms`
}

function formatNumber(value?: number | null): string {
  return value === null || value === undefined ? '—' : new Intl.NumberFormat('zh-CN').format(value)
}

function formatCost(value?: number | null): string {
  return value === null || value === undefined ? '—' : `$${value.toFixed(4)}`
}

function statusLabel(status: string): string {
  return ({ success: '成功', pending: '待审批', rejected: '已拒绝', error: '异常' } as Record<string, string>)[status] || status
}

onMounted(refresh)
</script>

<style scoped lang="scss">
.observability-page { height: calc(100vh - 60px); overflow-y: auto; padding: 26px; background: var(--bg-primary); }
.page-header { display: flex; justify-content: space-between; gap: 20px; align-items: flex-end; margin-bottom: 22px; h1 { margin: 5px 0 3px; font-size: 26px; } p { margin: 0; color: var(--text-muted); font-size: 12px; } }
.eyebrow { display: flex; align-items: center; gap: 6px; color: var(--primary-color); font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.header-controls { display: flex; gap: 8px; select, button { padding: 8px 11px; background: var(--bg-secondary); border: 1px solid var(--border-default); border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 11px; } button { display: flex; align-items: center; gap: 6px; } }
.spinning { animation: spin .8s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
.fallback-banner { margin-bottom: 14px; padding: 9px 12px; display: flex; align-items: center; gap: 7px; color: var(--primary-color); background: var(--primary-muted); border: 1px solid rgba(245,158,11,.25); border-radius: var(--radius-sm); font-size: 11px; }

.metric-grid { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap: 10px; margin-bottom: 14px; }
.metric-card { padding: 14px; display: flex; align-items: center; gap: 11px; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); }
.metric-icon { width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: 9px; &.purple { color: var(--accent-purple); background: rgba(139,92,246,.1); } &.blue { color: var(--accent-blue); background: rgba(59,130,246,.1); } &.green { color: var(--accent-green); background: rgba(16,185,129,.1); } &.amber { color: var(--primary-color); background: var(--primary-muted); } &.red { color: var(--accent-red); background: rgba(239,68,68,.1); } }
.metric-card div { display: flex; flex-direction: column; small { color: var(--text-muted); font-size: 9px; text-transform: uppercase; } strong { font-family: 'JetBrains Mono', monospace; font-size: 18px; } em { color: var(--text-muted); font-size: 9px; font-style: normal; } }

.dashboard-grid { display: grid; grid-template-columns: minmax(620px, 1fr) 330px; gap: 14px; }
.right-column { display: flex; flex-direction: column; gap: 14px; }
.panel { background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); overflow: hidden; }
.panel-header { min-height: 55px; padding: 12px 15px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); h2 { margin: 0; font-size: 13px; } span { color: var(--text-muted); font-size: 9px; } a { display: flex; gap: 4px; align-items: center; font-size: 10px; } }
.legend { display: flex; align-items: center; gap: 5px; color: var(--text-muted); font-size: 9px; i { width: 6px; height: 6px; border-radius: 50%; margin-left: 5px; } .ok { background: var(--accent-green); } .pending { background: var(--primary-color); } .error { background: var(--accent-red); } }
.trace-table { min-height: 350px; }
.trace-row { width: 100%; display: grid; grid-template-columns: minmax(210px, 1.8fr) .7fr .7fr .6fr .6fr .35fr; gap: 10px; align-items: center; padding: 11px 15px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); text-align: left; font-size: 10px; &:not(.table-head):hover { background: var(--bg-hover); } }
.table-head { color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; font-size: 8px; }
.trace-name { display: flex; flex-direction: column; min-width: 0; b { color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; } small { color: var(--text-muted); font-size: 9px; } }
.status-dot { display: inline-block; width: 6px; height: 6px; margin-right: 5px; border-radius: 50%; background: var(--text-muted); &.success { background: var(--accent-green); } &.pending { background: var(--primary-color); } &.error, &.rejected { background: var(--accent-red); } }
.mono { font-family: 'JetBrains Mono', monospace; }
.tool-count { width: 24px; height: 20px; display: inline-flex; align-items: center; justify-content: center; border-radius: 999px; background: var(--bg-elevated); }
.pagination { display: flex; justify-content: center; align-items: center; gap: 12px; padding: 10px; font-size: 10px; color: var(--text-muted); button { padding: 5px 8px; border: 1px solid var(--border-default); border-radius: var(--radius-sm); color: var(--text-secondary); &:disabled { opacity: .35; } } }
.empty-state { padding: 70px 20px; text-align: center; color: var(--text-muted); font-size: 11px; &.compact { padding: 30px 15px; } }

.distribution-panel { min-height: 230px; }
.distribution-list { padding: 13px 15px; }
.distribution-item { margin-bottom: 12px; > div:first-child { display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 10px; b { color: var(--text-primary); } } }
.bar { height: 5px; margin-top: 5px; background: var(--bg-elevated); border-radius: 99px; overflow: hidden; i { display: block; height: 100%; background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple)); border-radius: inherit; } }
.detail-panel { max-height: 470px; overflow-y: auto; :deep(.agent-timeline) { padding: 14px; } }

@media (max-width: 1300px) { .metric-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 1050px) { .dashboard-grid { grid-template-columns: 1fr; } .right-column { display: grid; grid-template-columns: 1fr 1fr; } }
@media (max-width: 760px) { .observability-page { padding: 16px; } .page-header { align-items: flex-start; flex-direction: column; } .metric-grid { grid-template-columns: repeat(2, 1fr); } .trace-row { grid-template-columns: minmax(170px, 1fr) .7fr .7fr .35fr; > span:nth-child(4), > span:nth-child(5) { display: none; } } .right-column { grid-template-columns: 1fr; } }
</style>
