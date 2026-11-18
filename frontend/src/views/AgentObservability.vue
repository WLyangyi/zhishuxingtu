<template>
  <div class="obs">
    <div class="obs__inner">
      <PageHeader
        kicker="OBSERVABILITY · AGENT RUNS"
        title="可观测面板"
        description="会话、工具调用、延迟与成本的实时读数。数据来自本地审计日志，可切换 Langfuse 云端。"
      >
        <template #actions>
          <div class="obs__actions">
            <AppSelect
              :model-value="source"
              :options="sourceOptions"
              placeholder="数据源"
              aria-label="数据源"
              @update:model-value="onSourceChange"
            />
            <IconButton label="刷新" :disabled="loading" @click="refresh">
              <RefreshCw :size="15" :stroke-width="1.8" :class="loading && 'spin'" />
            </IconButton>
          </div>
        </template>
      </PageHeader>

      <div v-if="fallbackReason" class="obs__banner">
        <CloudOff :size="13" :stroke-width="1.8" />
        <span>Langfuse 暂不可用，已回退本地审计数据：{{ fallbackReason }}</span>
      </div>

      <div v-if="loadError" class="obs__banner obs__banner--bad">
        <ShieldAlert :size="13" :stroke-width="1.8" />
        <span>加载失败：{{ loadError }}</span>
        <button type="button" class="obs__retry" @click="refresh">重试</button>
      </div>

      <section class="readouts" aria-label="关键读数">
        <MetricCard label="SESSIONS" :value="summary?.sessions ?? 0" note="已记录会话" />
        <MetricCard label="TOOL CALLS" :value="summary?.tool_calls ?? 0" note="累计工具调用" />
        <MetricCard
          label="AVG LATENCY"
          :value="formatLatency(summary?.avg_tool_latency_ms ?? 0)"
          note="工具平均耗时"
        />
        <MetricCard label="SUCCESS" :value="successRate" :note="`${summary?.rejected_calls ?? 0} 次被拒绝`" />
        <MetricCard label="PENDING" :value="summary?.pending_approvals ?? 0" note="等待人工审批" />
        <MetricCard label="PREFERENCES" :value="summary?.preferences ?? 0" note="长期偏好条目" />
      </section>

      <section class="obs__grid">
        <div class="traces">
          <header class="traces__head">
            <div class="traces__heading">
              <span class="readout">TRACES</span>
              <h2 class="traces__title">调用记录</h2>
            </div>
            <span class="readout traces__source">{{ traceSourceLabel }} · {{ meta.total_items }} 条</span>
          </header>

          <div class="traces__cols" aria-hidden="true">
            <span>TRACE</span>
            <span>STATUS</span>
            <span>LATENCY</span>
            <span>TOKENS</span>
            <span>COST</span>
            <span>TOOLS</span>
          </div>

          <div v-if="loading && !traces.length" class="traces__skeleton">
            <div v-for="index in 8" :key="index" class="traces__skeleton-row">
              <Skeleton width="42%" :height="12" />
              <Skeleton width="54px" :height="12" />
              <Skeleton width="46px" :height="12" />
            </div>
          </div>

          <EmptyState
            v-else-if="!traces.length"
            title="还没有调用记录"
            description="在 AI 助手里发起一次对话，思考、工具调用与审批都会记录在这里。"
          >
            <RouterLink to="/ai">
              <AppButton size="sm" variant="ghost">去 AI 助手</AppButton>
            </RouterLink>
          </EmptyState>

          <div v-else class="traces__rows">
            <button
              v-for="trace in traces"
              :key="trace.id"
              type="button"
              :class="['trace-row', selectedTrace?.id === trace.id && 'trace-row--active']"
              @click="selectTrace(trace)"
            >
              <span class="trace-row__name">
                <b>{{ trace.name }}</b>
                <small class="readout">{{ formatDate(trace.timestamp) }}</small>
              </span>
              <span class="trace-row__status">
                <StatusDot :status="statusMeta(trace.status).tone" />
                {{ statusMeta(trace.status).label }}
              </span>
              <span class="num trace-row__cell">{{ formatLatency(trace.latency_ms) }}</span>
              <span class="num trace-row__cell">{{ formatTokens(trace.total_tokens) }}</span>
              <span class="num trace-row__cell">{{ formatCost(trace.total_cost) }}</span>
              <span class="trace-row__tools num">{{ trace.tool_calls }}</span>
            </button>
          </div>

          <footer v-if="meta.total_pages > 1" class="traces__foot">
            <IconButton label="上一页" :disabled="meta.page <= 1" @click="changePage(meta.page - 1)">
              <ChevronLeft :size="15" :stroke-width="1.8" />
            </IconButton>
            <span class="readout">{{ meta.page }} / {{ meta.total_pages }}</span>
            <IconButton
              label="下一页"
              :disabled="meta.page >= meta.total_pages"
              @click="changePage(meta.page + 1)"
            >
              <ChevronRight :size="15" :stroke-width="1.8" />
            </IconButton>
          </footer>
        </div>

        <aside class="side">
          <section class="block">
            <header class="block__head">
              <span class="readout">DISTRIBUTION</span>
              <h2 class="block__title">工具分布</h2>
            </header>
            <div v-if="shares.length" class="bars">
              <div v-for="item in shares" :key="item.name" class="bar">
                <div class="bar__row">
                  <span class="bar__name">{{ item.name }}</span>
                  <span class="num bar__count">{{ item.count }}</span>
                </div>
                <div class="bar__track">
                  <i class="bar__fill" :style="{ width: `${item.pct}%` }" />
                </div>
              </div>
            </div>
            <p v-else class="block__empty">暂无工具调用</p>
          </section>

          <section class="block block--detail">
            <header class="block__head">
              <span class="readout">CHAIN</span>
              <h2 class="block__title">调用链详情</h2>
              <a
                v-if="selectedTrace?.url"
                class="block__link"
                :href="selectedTrace.url"
                target="_blank"
                rel="noopener"
              >
                Langfuse <ExternalLink :size="11" :stroke-width="1.8" />
              </a>
            </header>
            <div v-if="selectedTrace" class="detail">
              <div class="detail__meta">
                <span class="readout">{{ selectedTrace.name }}</span>
                <span class="num">{{ formatLatency(selectedTrace.latency_ms) }}</span>
              </div>
              <ToolTrace :events="selectedTimeline" empty-text="该 trace 没有可展开的本地工具日志。" />
            </div>
            <p v-else class="block__empty">选择左侧任一记录，查看思考与工具调用链。</p>
          </section>
        </aside>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ChevronLeft,
  ChevronRight,
  CloudOff,
  ExternalLink,
  RefreshCw,
  ShieldAlert
} from 'lucide-vue-next'
import {
  AppButton,
  AppSelect,
  EmptyState,
  IconButton,
  PageHeader,
  Skeleton,
  StatusDot
} from '@/components/ui'
import MetricCard from '@/components/domain/MetricCard.vue'
import ToolTrace from '@/components/agent/ToolTrace.vue'
import {
  agentApi,
  type AgentTrace,
  type ObservabilitySummary,
  type TimelineEvent
} from '@/api/agent'
import {
  formatCost,
  formatLatency,
  formatTokens,
  statusMeta,
  toolShares
} from '@/lib/observability'

const loading = ref(false)
const source = ref('auto')
const traces = ref<AgentTrace[]>([])
const summary = ref<ObservabilitySummary | null>(null)
const fallbackReason = ref('')
const loadError = ref('')
const actualSource = ref<'local' | 'langfuse'>('local')
const meta = ref({ page: 1, limit: 20, total_items: 0, total_pages: 0 })
const selectedTrace = ref<AgentTrace | null>(null)
const selectedTimeline = ref<TimelineEvent[]>([])

const sourceOptions = computed(() => [
  { label: '自动（Langfuse 优先）', value: 'auto' },
  { label: '本地审计数据', value: 'local' },
  {
    label: 'Langfuse 云端',
    value: 'langfuse',
    disabled: !summary.value?.langfuse_configured
  }
])

const successRate = computed(() => {
  if (!summary.value || summary.value.tool_calls === 0) return '—'
  return `${Math.round(summary.value.success_rate * 100)}%`
})
const traceSourceLabel = computed(() =>
  actualSource.value === 'langfuse' ? 'Langfuse 云端' : '本地审计'
)
const shares = computed(() => toolShares(summary.value?.tool_distribution ?? []))

function errorText(error: unknown): string {
  const err = error as { response?: { data?: { detail?: string } }; message?: string }
  return err?.response?.data?.detail || err?.message || '请求失败'
}

function formatDate(value?: string): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

async function loadTraces() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await agentApi.getTraces(source.value, meta.value.page, meta.value.limit)
    traces.value = result.data
    meta.value = result.meta
    actualSource.value = result.source
    fallbackReason.value = result.fallback_reason || ''
  } catch (error) {
    // 显式选择 Langfuse 源且云端不可达时后端返回 503；展示错误而不是误导性的空态
    traces.value = []
    meta.value = { page: 1, limit: 20, total_items: 0, total_pages: 0 }
    loadError.value = errorText(error)
  } finally {
    loading.value = false
  }
}

async function refresh() {
  try {
    const [summaryData] = await Promise.all([agentApi.getObservabilitySummary(), loadTraces()])
    summary.value = summaryData
  } catch (error) {
    loadError.value = errorText(error)
  }
}

async function onSourceChange(value: string) {
  source.value = value
  meta.value.page = 1
  selectedTrace.value = null
  selectedTimeline.value = []
  await loadTraces()
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
    selectedTimeline.value = [{ type: 'observation', content: '请在 Langfuse 中查看完整 observation / span。' }]
  }
}

onMounted(refresh)
</script>

<style scoped>
.obs {
  position: relative;
  min-height: 100%;
}

.obs__inner {
  width: 100%;
  max-width: 1360px;
  margin: 0 auto;
  padding: 32px 48px 72px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.obs__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.obs__actions :deep(.select-field) {
  width: 190px;
}

.spin {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.obs__banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  background: var(--gold-soft);
  color: var(--t2);
  font-size: var(--fs-micro);
  line-height: 1.5;
}

.obs__banner--bad {
  border-color: var(--danger-line);
  background: var(--danger-soft);
}

.obs__retry {
  margin-left: auto;
  padding: 2px 8px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  color: var(--t2);
  font-size: var(--fs-micro);
}

.obs__retry:hover {
  color: var(--text);
  border-color: var(--gold-line);
}

/* 读数：发丝分隔，不用卡片面 */
.readouts {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.readouts :deep(.metric) {
  padding: 16px 18px;
  border-left: 1px solid var(--line);
}

.readouts :deep(.metric:first-child) {
  border-left: 0;
  padding-left: 0;
}

.obs__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 336px;
  gap: 24px;
  align-items: start;
}

.traces {
  min-width: 0;
  border-top: 1px solid var(--line-strong);
}

.traces__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0 12px;
}

.traces__heading {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.traces__title {
  font-family: var(--font-display);
  font-size: var(--fs-title-3);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.traces__source {
  color: var(--t3);
}

.traces__cols,
.trace-row {
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) 96px 78px 66px 76px 44px;
  gap: 12px;
  align-items: center;
}

.traces__cols {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  color: var(--t3);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
}

.traces__cols span:nth-child(n + 3) {
  text-align: right;
}

.trace-row {
  width: 100%;
  padding: 11px 10px;
  border-bottom: 1px solid var(--line);
  border-left: 2px solid transparent;
  text-align: left;
  transition: background var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out);
}

.trace-row:hover {
  background: var(--panel);
}

.trace-row--active {
  border-left-color: var(--gold);
  background: var(--panel);
}

.trace-row__name {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.trace-row__name b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
  font-size: var(--fs-body-s);
  font-weight: 500;
}

.trace-row__name small {
  color: var(--t3);
  font-size: 9.5px;
}

.trace-row__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--t2);
  font-size: var(--fs-micro);
}

.trace-row__cell {
  text-align: right;
  color: var(--t2);
  font-size: var(--fs-micro);
  font-variant-numeric: tabular-nums;
}

.trace-row__tools {
  justify-self: end;
  min-width: 24px;
  padding: 1px 6px;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  text-align: center;
  color: var(--t2);
  font-size: 10px;
}

.traces__skeleton {
  padding: 6px 10px;
}

.traces__skeleton-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.traces__foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 14px 0;
  color: var(--t3);
}

.side {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.block {
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
  padding: 14px 16px 16px;
}

.block__head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.block__title {
  font-family: var(--font-display);
  font-size: var(--fs-body-s);
  font-weight: 600;
}

.block__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  color: var(--gold);
  font-family: var(--font-mono);
  font-size: 10px;
}

.block__empty {
  padding: 22px 0 8px;
  color: var(--t3);
  font-size: var(--fs-micro);
  line-height: 1.6;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 12px;
}

.bar__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 5px;
}

.bar__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--t2);
  font-family: var(--font-mono);
  font-size: 10.5px;
}

.bar__count {
  color: var(--text);
  font-size: 11px;
}

.bar__track {
  height: 2px;
  background: var(--line);
  border-radius: var(--r-pill);
  overflow: hidden;
}

.bar__fill {
  display: block;
  height: 100%;
  background: var(--gold);
  border-radius: inherit;
}

.block--detail {
  max-height: 520px;
  overflow-y: auto;
}

.detail {
  padding-top: 10px;
}

.detail__meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  color: var(--t3);
}

.detail :deep(.trace) {
  padding-top: 2px;
}

@media (max-width: 1200px) {
  .obs__grid {
    grid-template-columns: 1fr;
  }

  .side {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .block--detail {
    max-height: none;
  }
}

@media (max-width: 1024px) {
  .readouts {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .readouts :deep(.metric) {
    border-left: 1px solid var(--line);
  }

  .readouts :deep(.metric:nth-child(3n + 1)) {
    border-left: 0;
    padding-left: 0;
  }
}

@media (max-width: 767px) {
  .obs__inner {
    padding: 24px 16px 56px;
  }

  .obs__actions {
    width: 100%;
  }

  .obs__actions :deep(.select-field) {
    flex: 1;
    width: auto;
  }

  .readouts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .readouts :deep(.metric) {
    padding: 14px 12px;
    border-left: 1px solid var(--line);
  }

  .readouts :deep(.metric:nth-child(3n + 1)) {
    border-left: 1px solid var(--line);
    padding-left: 12px;
  }

  .readouts :deep(.metric:nth-child(2n + 1)) {
    border-left: 0;
    padding-left: 0;
  }

  .traces__cols,
  .trace-row {
    grid-template-columns: minmax(0, 1fr) 80px 70px 36px;
    gap: 8px;
  }

  .traces__cols span:nth-child(4),
  .traces__cols span:nth-child(5),
  .trace-row__cell:nth-child(4),
  .trace-row__cell:nth-child(5) {
    display: none;
  }

  .side {
    grid-template-columns: 1fr;
  }
}
</style>
