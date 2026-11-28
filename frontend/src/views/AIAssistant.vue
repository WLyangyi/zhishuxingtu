<template>
  <div class="assistant">
    <div v-if="sessionsOpen" class="assistant__overlay" @click="sessionsOpen = false" />

    <aside :class="['assistant__sessions', sessionsOpen && 'assistant__sessions--open']">
      <header class="sessions__head">
        <span class="readout">AGENT · 会话</span>
        <button type="button" class="sessions__close" aria-label="关闭会话列表" @click="sessionsOpen = false">
          <X :size="14" />
        </button>
      </header>

      <AppButton block size="sm" variant="secondary" @click="createNewChat">
        <template #icon><Plus :size="14" /></template>
        新对话
      </AppButton>

      <div class="sessions__search">
        <Search :size="12" />
        <input
          v-model="sessionQuery"
          type="search"
          placeholder="搜索会话标题…"
          aria-label="搜索会话"
          @input="onSessionSearch"
        />
      </div>

      <div class="sessions__list">
        <button
          v-for="chat in visibleChats"
          :key="chat.id"
          type="button"
          :class="['session', chat.id === currentChatId && 'session--active']"
          @click="switchChat(chat.id)"
        >
          <span class="session__bar" aria-hidden="true" />
          <span class="session__main">
            <span class="session__title">{{ chat.title || '新会话' }}</span>
            <span v-if="chat.core_intent" class="session__goal">{{ chat.core_intent.goal }}</span>
            <span class="session__meta">{{ relativeTime(chat.updated_at || chat.created_at || '') || '刚刚' }}</span>
          </span>
          <span class="session__delete" @click.stop="deleteChat(chat.id)">
            <X :size="12" />
          </span>
        </button>

        <p v-if="!visibleChats.length" class="sessions__empty">
          {{ sessionQuery ? '没有匹配的会话。' : '还没有历史对话。' }}
        </p>
      </div>
    </aside>

    <main class="assistant__main">
      <header class="assistant__head">
        <button type="button" class="assistant__menu" aria-label="打开会话" @click="sessionsOpen = true">
          <MessagesSquare :size="16" />
        </button>

        <div class="assistant__title-group">
          <span class="readout">OBSERVER · AGENTIC RAG</span>
          <h1 class="assistant__title">和你的知识库一起思考</h1>
        </div>

        <div class="assistant__head-actions">
          <span v-if="usageLabel" class="usage" :title="usageTitle">
            <Gauge :size="12" />
            {{ usageLabel }}
          </span>
          <RouterLink to="/ai/observability" class="head-btn">
            <Activity :size="14" />
            <span>可观测</span>
          </RouterLink>
          <button
            type="button"
            class="head-btn"
            :disabled="!messages.length"
            @click="clearChat"
          >
            <Trash2 :size="14" />
            <span>清空</span>
          </button>
          <button type="button" class="assistant__inspector-toggle" aria-label="打开 Inspector" @click="inspectorOpen = true">
            <PanelRight :size="16" />
          </button>
        </div>
      </header>

      <div v-if="offline" class="offline">
        <WifiOff :size="13" />
        <span class="offline__text">
          连接中断<span v-if="retryIn">，{{ retryIn }}s 后自动重连</span>
        </span>
        <button v-if="lastStream && !streamingContent" type="button" class="offline__retry" @click="retryNow">
          立即重连
        </button>
        <button type="button" class="offline__close" aria-label="关闭提示" @click="dismissOffline">
          <X :size="12" />
        </button>
      </div>

      <div ref="chatContainer" class="conversation" @click="handleConversationClick">
        <div v-if="anchorInfo" class="anchor-bar" data-test="anchor-bar">
          <Target :size="12" :stroke-width="2" class="anchor-bar__icon" />
          <span class="anchor-bar__label">任务锚点</span>
          <span class="anchor-bar__goal">{{ anchorInfo.goal }}</span>
          <span v-if="anchorUpdated" class="anchor-bar__updated">已更新</span>
          <span class="anchor-bar__version">v{{ anchorVersion }}</span>
        </div>

        <div v-if="taskList.length" class="task-bar" data-test="task-bar">
          <Layers :size="12" :stroke-width="2" class="task-bar__icon" />
          <span class="task-bar__label">任务</span>
          <div class="task-bar__chips">
            <button
              v-for="task in taskList"
              :key="task.id"
              type="button"
              :class="['task-chip', task.is_current && 'task-chip--current']"
              :disabled="task.is_current"
              @click="switchTask(task.id)"
            >
              <span class="task-chip__title">{{ task.title || task.goal || '未命名任务' }}</span>
              <span class="task-chip__phase">{{ task.phase }}</span>
              <span v-if="task.is_current" class="task-chip__badge">当前</span>
              <span v-else class="task-chip__status">{{ task.status }}</span>
              <span
                v-if="!task.is_current && task.status === 'completed'"
                class="task-chip__restore"
                role="button"
                @click.stop="restoreTask(task.id)"
              >恢复</span>
            </button>
          </div>
        </div>

        <div v-if="!messages.length && !isStreaming && !pendingApproval" class="welcome">
          <Sparkles :size="26" :stroke-width="1.4" class="welcome__icon" />
          <h2 class="welcome__title">和你的知识库一起思考</h2>
          <p class="welcome__desc">
            Agent 会自主检索、调用工具，并在写入笔记前请求你的确认。
          </p>
          <div class="welcome__actions">
            <button v-for="action in quickActions" :key="action" type="button" @click="sendQuickAction(action)">
              {{ action }}
            </button>
          </div>
        </div>

        <MessageBubble
          v-for="(message, index) in messages"
          :key="messageScope(message, index)"
          :role="message.role"
          :name="message.role === 'assistant' ? '观测员' : ''"
        >
          <div
            v-if="message.role === 'assistant'"
            class="message-markdown"
            :data-source-scope="messageScope(message, index)"
            v-html="renderAssistant(message.content, message.sources, messageScope(message, index))"
          />
          <span v-else>{{ message.content }}</span>

          <ErrorBoundary v-if="message.role === 'assistant' && message.sources?.length">
            <div class="message-sources" :data-source-scope="messageScope(message, index)">
              <SourceCard
                v-for="source in message.sources"
                :key="source.source_id"
                :source="source"
                :saved="savedSourceIds.has(source.source_id)"
                :class="{ 'source-card--highlighted': highlightedSourceKey === sourceHighlightKey(messageScope(message, index), source.source_id) }"
                @save="openSourceSave"
              />
            </div>
          </ErrorBoundary>

          <ErrorBoundary v-if="message.role === 'assistant' && message.visual_evidence?.length">
            <div class="visual-evidence-list">
              <VisualEvidenceCard
                v-for="evidence in message.visual_evidence"
                :key="evidence.asset_id"
                :evidence="evidence"
                @view="openVisualEvidence"
              />
            </div>
          </ErrorBoundary>

          <details v-if="message.trace?.length" class="turn-trace">
            <summary class="turn-trace__head">
              <Wrench :size="11" :stroke-width="1.8" />
              <span>工具轨迹 · {{ message.trace.length }} 事件</span>
              <ChevronDown :size="11" :stroke-width="1.8" class="turn-trace__chevron" />
            </summary>
            <ToolTrace :events="message.trace" />
          </details>
        </MessageBubble>

        <div
          v-for="record in approvalRecords"
          :key="record.id"
          :class="['approval-record', `approval-record--${record.approved ? 'approved' : 'rejected'}`]"
        >
          <component :is="record.approved ? Check : X" :size="12" :stroke-width="2" />
          <span>{{ record.approved ? '已批准' : '已拒绝' }} · {{ record.tool }}</span>
          <span class="readout">{{ record.time }}</span>
        </div>

        <div v-if="isStreaming" class="stream-block">
          <div class="stream-meta">
            <span class="readout">观测员 · STREAMING</span>
            <span v-if="streamingContent" class="readout">{{ streamingContent.length }} 字</span>
          </div>

          <ToolTrace v-if="liveTimeline.length" :events="liveTimeline" class="stream-trace" />

          <div
            v-if="streamingContent"
            class="message-markdown stream-answer"
            data-source-scope="streaming"
            v-html="renderAssistant(streamingContent, streamingSources, 'streaming')"
          />
          <span v-if="!streamingContent" class="typing"><i /><i /><i /></span>
          <span v-else class="stream-cursor" aria-hidden="true" />

          <ErrorBoundary v-if="streamingSources.length">
            <div class="message-sources" data-source-scope="streaming">
              <SourceCard
                v-for="source in streamingSources"
                :key="source.source_id"
                :source="source"
                :saved="savedSourceIds.has(source.source_id)"
                :class="{ 'source-card--highlighted': highlightedSourceKey === sourceHighlightKey('streaming', source.source_id) }"
                @save="openSourceSave"
              />
            </div>
          </ErrorBoundary>

          <ErrorBoundary v-if="streamingVisualEvidence.length">
            <div class="visual-evidence-list">
              <VisualEvidenceCard
                v-for="evidence in streamingVisualEvidence"
                :key="evidence.asset_id"
                :evidence="evidence"
                @view="openVisualEvidence"
              />
            </div>
          </ErrorBoundary>
        </div>

        <div v-if="pendingApproval && approvalVm" class="approval-wrap">
          <ApprovalCard
            :title="approvalVm.title"
            :summary="approvalVm.summary"
            :payload="approvalVm.payload"
            status="pending"
            @approve="resumeApproval(true)"
            @reject="resumeApproval(false)"
          />
        </div>
      </div>

      <footer class="composer">
        <div class="composer__box">
          <textarea
            ref="inputRef"
            v-model="inputMessage"
            rows="1"
            class="composer__input"
            placeholder="输入问题，或让 Agent 创建一篇笔记…"
            :disabled="loading || !!pendingApproval"
            @keydown.enter.exact.prevent="sendMessage"
            @input="resizeInput"
          />
          <button
            v-if="!isStreaming"
            type="button"
            class="composer__send"
            :disabled="!inputMessage.trim() || loading || !!pendingApproval"
            aria-label="发送"
            @click="sendMessage"
          >
            <Send :size="16" />
          </button>
          <button v-else type="button" class="composer__stop" aria-label="停止生成" @click="stopStreaming">
            <Square :size="15" />
          </button>
        </div>
        <p class="composer__hint">Enter 发送 · Shift+Enter 换行 · 写操作必须审批</p>
      </footer>
    </main>

    <div v-if="inspectorOpen" class="assistant__overlay assistant__overlay--right" @click="inspectorOpen = false" />

    <aside :class="['assistant__inspector', inspectorOpen && 'assistant__inspector--open']">
      <header class="inspector__head">
        <span class="readout">INSPECTOR · 运行读数</span>
        <button type="button" class="sessions__close" aria-label="关闭 Inspector" @click="inspectorOpen = false">
          <X :size="14" />
        </button>
      </header>

      <section class="inspector__section">
        <div class="usage-grid">
          <div class="usage-cell">
            <span class="num usage-cell__value">{{ formatTokens(sessionUsage?.tokens ?? 0) }}</span>
            <span class="readout">TOKENS</span>
          </div>
          <div class="usage-cell">
            <span class="num usage-cell__value">¥{{ (sessionUsage?.cost ?? 0).toFixed(3) }}</span>
            <span class="readout">COST</span>
          </div>
          <div class="usage-cell">
            <span class="num usage-cell__value">{{ combinedTimeline.length }}</span>
            <span class="readout">EVENTS</span>
          </div>
        </div>
      </section>

      <section class="inspector__section inspector__section--trace">
        <header class="inspector__section-head">
          <span class="readout">TOOL TRACE · 工具轨迹</span>
          <button
            type="button"
            class="inspector__export"
            data-test="export-trace"
            :disabled="!combinedTimeline.length"
            title="导出工具轨迹为 JSON"
            @click="exportTrace"
          >
            <Download :size="12" />
            导出 JSON
          </button>
        </header>
        <div class="inspector__trace-scroll">
          <ToolTrace :events="combinedTimeline" empty-text="本轮运行后，工具调用与三查过程会出现在这里。" />
        </div>
      </section>

      <section class="inspector__section">
        <span class="readout">LONG-TERM · 长期偏好</span>
        <div class="prefs">
          <span v-for="(value, key) in preferences" :key="key" class="pref">
            <b>{{ key }}</b>
            <span>{{ value }}</span>
            <button type="button" aria-label="删除偏好" @click="removePreference(String(key))">
              <X :size="10" />
            </button>
          </span>
          <span v-if="!Object.keys(preferences).length" class="prefs__empty">尚未设置偏好。</span>
        </div>
        <div class="prefs__form">
          <input v-model="preferenceKey" placeholder="名称，如 answer_style" />
          <input
            v-model="preferenceValue"
            placeholder="内容，如 先给结论"
            @keydown.enter="savePreference"
          />
          <button
            type="button"
            :disabled="!preferenceKey.trim() || !preferenceValue.trim()"
            @click="savePreference"
          >
            保存
          </button>
        </div>
        <span v-if="preferenceStatus" class="prefs__status">{{ preferenceStatus }}</span>
      </section>
    </aside>

    <AppModal
      :open="!!saveTarget"
      title="确认存入知识库"
      description="核对来源后创建笔记"
      :hide-close="!!savingSourceId"
      @update:open="handleSaveModalOpen"
    >
      <div v-if="saveTarget" class="source-save-preview">
        <h3 class="source-save-preview__title">{{ saveTarget.title || saveTarget.url }}</h3>
        <p class="source-save-preview__url">{{ saveTarget.url }}</p>
        <p class="source-save-preview__excerpt">{{ saveTarget.excerpt }}</p>
        <p v-if="saveTarget.truncated" class="source-save-preview__notice">
          正文已截断，保存的是现有快照中的部分正文。
        </p>
        <p class="source-save-preview__risk">
          将创建一篇知识库笔记，不会重新抓取网页。仅搜索摘要或抓取失败的来源只会保存现有证据。
        </p>
        <p v-if="sourceSaveError" class="source-save-preview__error" role="alert">{{ sourceSaveError }}</p>
      </div>
      <template #footer>
        <AppButton variant="ghost" size="sm" :disabled="!!savingSourceId" @click="closeSourceSave">取消</AppButton>
        <AppButton size="sm" :disabled="!!savingSourceId" @click="confirmSourceSave">
          {{ savingSourceId ? '保存中…' : '确认存入' }}
        </AppButton>
      </template>
    </AppModal>

    <AppModal
      :open="!!visualPreview"
      title="原图核验"
      description="对照原始页面确认视觉描述"
      @update:open="handleVisualPreviewOpen"
    >
      <div v-if="visualPreview" class="visual-evidence-preview">
        <p v-if="visualPreview.loading" class="visual-evidence-preview__status">正在加载原图…</p>
        <p v-else-if="visualPreview.error" class="visual-evidence-preview__status" role="alert">
          {{ visualPreview.error }}
        </p>
        <img
          v-else-if="visualPreview.url"
          class="visual-evidence-preview__image"
          :src="visualPreview.url"
          :alt="`${visualPreview.evidence.source_filename || '文档'}第 ${visualPreview.evidence.page_number} 页原图`"
        />
      </div>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  Activity,
  Check,
  ChevronDown,
  Download,
  Gauge,
  Layers,
  MessagesSquare,
  PanelRight,
  Plus,
  Search,
  Send,
  Sparkles,
  Square,
  Target,
  Trash2,
  WifiOff,
  Wrench,
  X
} from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import {
  agentApi,
  type AgentMessage,
  type AgentSession,
  type AgentTask,
  type CoreIntent,
  type PendingApproval,
  type TimelineEvent,
  type VisualEvidence,
  type WebSource,
} from '@/api/agent'
import MessageBubble from '@/components/domain/MessageBubble.vue'
import ApprovalCard from '@/components/domain/ApprovalCard.vue'
import SourceCard from '@/components/domain/SourceCard.vue'
import VisualEvidenceCard from '@/components/domain/VisualEvidenceCard.vue'
import ToolTrace from '@/components/agent/ToolTrace.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppModal from '@/components/ui/AppModal.vue'
import ErrorBoundary from '@/components/ui/ErrorBoundary.vue'
import { useAuthStore } from '@/stores/auth'
import { SSEClient, type SSEMessage } from '@/utils/sse'
import { relativeTime } from '@/lib/time'
import { buildTraceExport, filterSessions } from '@/lib/agentExport'

const authStore = useAuthStore()

interface ChatMessage extends AgentMessage {
  trace?: TimelineEvent[]
}

const messages = ref<ChatMessage[]>([])
const chatList = ref<AgentSession[]>([])
const sessionQuery = ref('')
const visibleChats = computed(() => filterSessions(chatList.value, sessionQuery.value))
const currentChatId = ref('')
const inputMessage = ref('')
const loading = ref(false)
const isStreaming = ref(false)
const streamingContent = ref('')
const streamingSources = ref<WebSource[]>([])
const streamingVisualEvidence = ref<VisualEvidence[]>([])
const streamingMessageId = ref('')
const highlightedSourceKey = ref('')
const persistedTimeline = ref<TimelineEvent[]>([])
const liveTimeline = ref<TimelineEvent[]>([])
const pendingApproval = ref<PendingApproval | null>(null)
const saveTarget = ref<WebSource | null>(null)
const savingSourceId = ref('')
const savedSourceIds = ref(new Set<string>())
const sourceSaveError = ref('')
const visualPreview = ref<{
  evidence: VisualEvidence
  url: string
  loading: boolean
  error: string
} | null>(null)
/** 阶段1b:会话锚点(完整 core_intent),off/shadow 模式后端返回 null 即隐藏 */
const anchorInfo = ref<CoreIntent | null>(null)
const anchorVersion = ref(0)
const anchorUpdated = ref(false)
/** 二期2.6:当前会话任务列表(task 分层,进度展示与切换) */
const taskList = ref<AgentTask[]>([])
const chatContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const sseClient = ref<SSEClient | null>(null)

const sessionsOpen = ref(false)
const inspectorOpen = ref(false)
const offline = ref(false)
const retryIn = ref(0)
const lastStream = ref<{ url: string; body: Record<string, unknown> } | null>(null)

interface ApprovalRecord {
  id: number
  approved: boolean
  tool: string
  time: string
}

const approvalRecords = ref<ApprovalRecord[]>([])

const preferences = ref<Record<string, string>>({})
const preferenceKey = ref('')
const preferenceValue = ref('')
const preferenceStatus = ref('')

const quickActions = ['我有哪些笔记？', '帮我总结一下知识库', '对比最近的两篇笔记']

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

let retryTimer: ReturnType<typeof setInterval> | null = null
let retryAttempts = 0
let disposed = false

interface SessionUsage {
  tokens: number
  cost: number
  tokenBudget: number
  costBudget: number
}

const sessionUsage = ref<SessionUsage | null>(null)
const combinedTimeline = computed(() => [...persistedTimeline.value, ...liveTimeline.value])

function formatTokens(value: number) {
  return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value)
}

const usageLabel = computed(() => {
  const usage = sessionUsage.value
  if (!usage || (!usage.tokens && !usage.cost)) return ''
  return `${formatTokens(usage.tokens)} tokens · ¥${usage.cost.toFixed(4)}`
})

const usageTitle = computed(() => {
  const usage = sessionUsage.value
  if (!usage) return ''
  const base = `本会话累计 ${usage.tokens} tokens / ¥${usage.cost.toFixed(4)}`
  if (!usage.tokenBudget && !usage.costBudget) return base
  return `${base}，上限 ${formatTokens(usage.tokenBudget)} tokens / ¥${usage.costBudget.toFixed(2)}`
})

const approvalVm = computed(() => {
  const approval = pendingApproval.value
  if (!approval) return null
  return {
    title: approval.title || `需要审批：${approval.tool_name ?? '写入操作'}`,
    summary: approval.description || 'Agent 请求执行写操作，确认后才会写入知识库。',
    payload: JSON.stringify(
      { tool: approval.tool_name, args: approval.args, preview: approval.preview },
      null,
      2
    )
  }
})

function messageScope(message: ChatMessage, index: number) {
  return message.id || `legacy-${index}`
}

function sourceHighlightKey(scope: string, sourceId: string) {
  return `${scope}:${sourceId}`
}

function openSourceSave(source: WebSource) {
  saveTarget.value = source
  sourceSaveError.value = ''
}

function closeSourceSave() {
  saveTarget.value = null
  sourceSaveError.value = ''
}

async function openVisualEvidence(evidence: VisualEvidence) {
  closeVisualPreview()
  visualPreview.value = { evidence, url: '', loading: true, error: '' }
  try {
    const blob = await agentApi.getVisualEvidenceImage(evidence.note_id, evidence.asset_id)
    const url = URL.createObjectURL(blob)
    if (visualPreview.value?.evidence.asset_id === evidence.asset_id) {
      visualPreview.value = { evidence, url, loading: false, error: '' }
    } else {
      URL.revokeObjectURL(url)
    }
  } catch (error) {
    if (visualPreview.value?.evidence.asset_id === evidence.asset_id) {
      visualPreview.value = {
        evidence,
        url: '',
        loading: false,
        error: error instanceof Error ? error.message : '原图加载失败，请重试'
      }
    }
  }
}

function closeVisualPreview() {
  if (visualPreview.value?.url) URL.revokeObjectURL(visualPreview.value.url)
  visualPreview.value = null
}

function handleVisualPreviewOpen(open: boolean) {
  if (!open) closeVisualPreview()
}

function handleSaveModalOpen(open: boolean) {
  if (!open && !savingSourceId.value) closeSourceSave()
}

async function confirmSourceSave() {
  const source = saveTarget.value
  if (!source || !currentChatId.value || savingSourceId.value) return
  savingSourceId.value = source.source_id
  sourceSaveError.value = ''
  try {
    await agentApi.saveSource(currentChatId.value, source.source_id)
    savedSourceIds.value.add(source.source_id)
    closeSourceSave()
  } catch (error) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    sourceSaveError.value = detail || (error instanceof Error ? error.message : '保存失败，请重试')
  } finally {
    savingSourceId.value = ''
  }
}

function renderAssistant(content: string, sources: WebSource[] = [], sourceScope = '') {
  const normalized = content.replace(/【([^】]+)】/g, '**$1**')
  const sanitized = DOMPurify.sanitize(md.render(normalized))
  if (!sources.length) return sanitized

  const sourceByOrdinal = new Map(sources.map((source) => [source.ordinal, source]))
  const document = new DOMParser().parseFromString(sanitized, 'text/html')
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  const textNodes: Text[] = []
  while (walker.nextNode()) textNodes.push(walker.currentNode as Text)

  for (const node of textNodes) {
    if (node.parentElement?.closest('a, code, pre')) continue
    const text = node.textContent || ''
    let cursor = 0
    let replaced = false
    const fragment = document.createDocumentFragment()
    for (const match of text.matchAll(/\[(\d+)\]/g)) {
      const source = sourceByOrdinal.get(Number(match[1]))
      if (!source) continue
      fragment.append(text.slice(cursor, match.index))
      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'citation'
      button.dataset.sourceId = source.source_id
      button.dataset.sourceScope = sourceScope
      button.setAttribute('aria-label', `查看来源 ${source.ordinal}`)
      button.textContent = match[0]
      fragment.append(button)
      cursor = match.index + match[0].length
      replaced = true
    }
    if (replaced) {
      fragment.append(text.slice(cursor))
      node.replaceWith(fragment)
    }
  }
  return document.body.innerHTML
}

function handleConversationClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  const citation = target?.closest<HTMLButtonElement>('button.citation')
  if (!citation || !chatContainer.value?.contains(citation)) return

  const sourceId = citation.dataset.sourceId
  const scope = citation.dataset.sourceScope
  if (!sourceId || !scope) return
  const scopeElement = Array.from(chatContainer.value.querySelectorAll<HTMLElement>('.message-sources[data-source-scope]'))
    .find((element) => element.dataset.sourceScope === scope)
  const card = Array.from(scopeElement?.querySelectorAll<HTMLElement>('.source-card[data-source-id]') || [])
    .find((element) => element.dataset.sourceId === sourceId)
  if (!card) return

  highlightedSourceKey.value = sourceHighlightKey(scope, sourceId)
  card.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function resizeInput() {
  const element = inputRef.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(140, element.scrollHeight)}px`
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  })
}

async function loadSessions() {
  chatList.value = await agentApi.listSessions()
  if (!chatList.value.length) {
    await createNewChat()
  } else if (!currentChatId.value) {
    await switchChat(chatList.value[0].id)
  }
}

/** 会话搜索（P2-6）：按标题向后端请求过滤，空结果不触发新建会话。 */
async function onSessionSearch() {
  const keyword = sessionQuery.value.trim()
  const result = await agentApi.listSessions(keyword || undefined)
  chatList.value = result
}

/** 工具轨迹一键导出 JSON（P2-6）。 */
function exportTrace() {
  if (!combinedTimeline.value.length) return
  const session = chatList.value.find((item) => item.id === currentChatId.value) ?? null
  const payload = buildTraceExport(session, combinedTimeline.value)
  const filename = `agent-trace-${session?.id || 'session'}-${Date.now()}.json`
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

async function createNewChat() {
  const chat = await agentApi.createSession()
  chatList.value.unshift(chat)
  await switchChat(chat.id)
}

async function switchChat(chatId: string) {
  sseClient.value?.abort()
  sseClient.value = null
  clearRetry()
  offline.value = false
  currentChatId.value = chatId
  pendingApproval.value = null
  approvalRecords.value = []
  sessionsOpen.value = false
  closeSourceSave()
  highlightedSourceKey.value = ''

  const meta = chatList.value.find((item) => item.id === chatId)
  sessionUsage.value =
    meta && (meta.total_tokens || meta.total_cost_cny)
      ? {
          tokens: meta.total_tokens || 0,
          cost: meta.total_cost_cny || 0,
          tokenBudget: 0,
          costBudget: 0
        }
      : null
  anchorVersion.value = meta?.core_intent?.version ?? 0
  anchorUpdated.value = false

  streamingContent.value = ''
  streamingSources.value = []
  streamingVisualEvidence.value = []
  streamingMessageId.value = ''
  loading.value = false
  isStreaming.value = false
  liveTimeline.value = []

  const [chatData, timeline, tasks] = await Promise.all([
    agentApi.getMessages(chatId),
    agentApi.getTimeline(chatId),
    agentApi.listTasks(chatId)
  ])
  messages.value = chatData.messages
  pendingApproval.value = chatData.pending_approval
  // 阶段1b:完整锚点来自 messages 接口;off/shadow 模式后端返回 null,锚点条自动隐藏
  anchorInfo.value = chatData.core_intent ?? null
  persistedTimeline.value = timeline
  // 二期2.6:加载任务列表(进度展示与切换)
  taskList.value = tasks ?? []
  scrollToBottom()
}

/** 二期2.6:刷新当前会话任务列表。 */
async function loadTasks() {
  if (!currentChatId.value) return
  taskList.value = (await agentApi.listTasks(currentChatId.value)) ?? []
}

/** 二期2.6:刷新锚点(任务切换后锚点随 task 变化,重新拉取完整 core_intent)。 */
async function refreshAnchor() {
  if (!currentChatId.value) return
  const chatData = await agentApi.getMessages(currentChatId.value)
  anchorInfo.value = chatData.core_intent ?? null
}

/** 二期2.6:切换当前任务(后端完成旧任务、激活目标任务并写入图状态)。 */
async function switchTask(taskId: string) {
  if (!currentChatId.value) return
  await agentApi.switchTask(currentChatId.value, taskId)
  await loadTasks()
  await refreshAnchor()
}

/** 二期2.6:恢复已完成的非当前任务。 */
async function restoreTask(taskId: string) {
  if (!currentChatId.value) return
  await agentApi.restoreTask(currentChatId.value, taskId)
  await loadTasks()
  await refreshAnchor()
}

async function deleteChat(chatId: string) {
  if (!window.confirm('确认删除该会话及其 checkpoint 和审计记录？')) return
  await agentApi.deleteSession(chatId)
  chatList.value = chatList.value.filter((chat) => chat.id !== chatId)
  if (currentChatId.value === chatId) {
    if (chatList.value.length) await switchChat(chatList.value[0].id)
    else await createNewChat()
  }
}

async function clearChat() {
  if (!currentChatId.value) return
  sseClient.value?.abort()
  sseClient.value = null
  clearRetry()
  offline.value = false
  await agentApi.clearSession(currentChatId.value)
  messages.value = []
  persistedTimeline.value = []
  liveTimeline.value = []
  approvalRecords.value = []
  pendingApproval.value = null
  anchorInfo.value = null
  anchorVersion.value = 0
  anchorUpdated.value = false
}

function apiBase() {
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
}

function handleStreamMessage(message: SSEMessage) {
  offline.value = false
  clearRetry()

  if (['thought', 'action', 'observation', 'check', 'intent'].includes(message.type)) {
    if (message.content) {
      liveTimeline.value.push({
        type: message.type as TimelineEvent['type'],
        content: message.content,
        node: message.node
      })
    }
  } else if (message.type === 'final_answer') {
    streamingContent.value = message.answer || ''
    streamingMessageId.value = message.message_id || streamingMessageId.value
  } else if (message.type === 'sources') {
    streamingSources.value = message.sources || []
    streamingMessageId.value = message.message_id || streamingMessageId.value
  } else if (message.type === 'visual_evidence') {
    streamingVisualEvidence.value = message.visual_evidence || []
    streamingMessageId.value = message.message_id || streamingMessageId.value
  } else if (message.type === 'usage') {
    sessionUsage.value = {
      tokens: message.session_tokens || 0,
      cost: message.session_cost_cny || 0,
      tokenBudget: message.token_budget || 0,
      costBudget: message.cost_budget_cny || 0
    }
  } else if (message.type === 'budget_exceeded') {
    liveTimeline.value.push({
      type: 'observation',
      content: message.message || '会话预算已用尽',
      status: 'error'
    })
  } else if (message.type === 'approval_required') {
    pendingApproval.value = message as unknown as PendingApproval
  } else if (message.type === 'error') {
    liveTimeline.value.push({
      type: 'observation',
      content: message.message || 'Agent 执行异常',
      status: 'error'
    })
  }

  scrollToBottom()
}

async function refreshAfterStream() {
  if (streamingContent.value) {
    messages.value.push({
      id: streamingMessageId.value || undefined,
      role: 'assistant',
      content: streamingContent.value,
      sources: streamingSources.value.length ? [...streamingSources.value] : undefined,
      visual_evidence: streamingVisualEvidence.value.length ? [...streamingVisualEvidence.value] : undefined,
      trace: liveTimeline.value.length ? [...liveTimeline.value] : undefined
    })
  }
  streamingContent.value = ''
  streamingSources.value = []
  streamingVisualEvidence.value = []
  streamingMessageId.value = ''
  liveTimeline.value = []
  loading.value = false
  isStreaming.value = false
  offline.value = false
  clearRetry()

  if (currentChatId.value) {
    persistedTimeline.value = await agentApi.getTimeline(currentChatId.value)
    chatList.value = await agentApi.listSessions()
    // 阶段1b:流结束后会话镜像的 intent_version 可能已 bump,刷新版本并提示锚点已更新
    const meta = chatList.value.find((item) => item.id === currentChatId.value)
    const nextVersion = meta?.core_intent?.version ?? 0
    if (nextVersion !== anchorVersion.value) {
      anchorVersion.value = nextVersion
      if (nextVersion > 0) anchorUpdated.value = true
    }
  }
  scrollToBottom()
}

async function restorePendingState() {
  if (!currentChatId.value) return
  try {
    const chatData = await agentApi.getMessages(currentChatId.value)
    messages.value = chatData.messages
    pendingApproval.value = chatData.pending_approval
  } catch {
    /* 恢复失败时保持当前界面状态 */
  }
}

function clearRetry() {
  if (retryTimer) clearInterval(retryTimer)
  retryTimer = null
  retryIn.value = 0
}

function startRetryCountdown() {
  clearRetry()
  retryIn.value = 3
  retryTimer = setInterval(() => {
    retryIn.value -= 1
    if (retryIn.value <= 0) {
      clearRetry()
      retryNow()
    }
  }, 1000)
}

function retryNow() {
  if (!lastStream.value || disposed) return
  retryAttempts += 1
  offline.value = false
  loading.value = true
  isStreaming.value = true
  void connectStream(lastStream.value.url, lastStream.value.body, undefined, true)
}

function dismissOffline() {
  offline.value = false
  clearRetry()
}

async function connectStream(
  url: string,
  body: Record<string, unknown> = {},
  onConflict?: () => void,
  isRetry = false
) {
  if (disposed) return
  lastStream.value = { url, body }
  if (!isRetry) retryAttempts = 0

  const token = authStore.token || localStorage.getItem('token') || undefined
  sseClient.value = new SSEClient()
  await sseClient.value.connect(url, body, {
    method: 'POST',
    token,
    onMessage: handleStreamMessage,
    onError: async (error) => {
      loading.value = false
      isStreaming.value = false
      const status = (error as Error & { status?: number }).status

      if (status === 409) {
        await restorePendingState()
        messages.value.push({
          role: 'assistant',
          content: '该会话存在待审批操作，请先在审批卡中确认或拒绝。'
        })
        onConflict?.()
        scrollToBottom()
        return
      }

      offline.value = true
      if (!streamingContent.value && retryAttempts < 2) {
        startRetryCountdown()
      } else {
        clearRetry()
      }
      scrollToBottom()
    },
    onComplete: () => {
      if (!disposed) void refreshAfterStream()
    }
  })
}

async function sendMessage() {
  const question = inputMessage.value.trim()
  if (!question || loading.value || pendingApproval.value) return
  if (!currentChatId.value) await createNewChat()

  messages.value.push({ role: 'user', content: question })
  inputMessage.value = ''
  nextTick(() => resizeInput())
  liveTimeline.value = []
  streamingContent.value = ''
  streamingSources.value = []
  streamingVisualEvidence.value = []
  streamingMessageId.value = ''
  loading.value = true
  isStreaming.value = true
  offline.value = false
  retryAttempts = 0
  clearRetry()
  scrollToBottom()

  const params = new URLSearchParams({ question, session_id: currentChatId.value })
  await connectStream(`${apiBase()}/api/agent/chat/stream?${params.toString()}`, {}, () => {
    inputMessage.value = question
  })
}

async function resumeApproval(approved: boolean) {
  if (!pendingApproval.value || loading.value) return
  const approval = pendingApproval.value
  pendingApproval.value = null
  approvalRecords.value.push({
    id: Date.now(),
    approved,
    tool: approval.tool_name || '写入操作',
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  streamingContent.value = ''
  streamingSources.value = []
  streamingVisualEvidence.value = []
  streamingMessageId.value = ''
  loading.value = true
  isStreaming.value = true
  liveTimeline.value.push({
    type: 'action',
    content: approved ? `用户批准 ${approval.tool_name}` : `用户拒绝 ${approval.tool_name}`,
    status: approved ? 'success' : 'rejected'
  })

  await connectStream(`${apiBase()}/api/agent/resume`, {
    session_id: approval.session_id || currentChatId.value,
    approved,
    reason: approved ? '用户在前端审批卡确认' : '用户在前端审批卡拒绝'
  })
}

function stopStreaming() {
  sseClient.value?.abort()
  loading.value = false
  isStreaming.value = false
  clearRetry()
  offline.value = false
}

function sendQuickAction(text: string) {
  inputMessage.value = text
  void sendMessage()
}

async function loadPreferences() {
  preferences.value = await agentApi.getPreferences()
}

async function savePreference() {
  const key = preferenceKey.value.trim()
  const value = preferenceValue.value.trim()
  if (!key || !value) return
  await agentApi.putPreference(key, value)
  preferences.value[key] = value
  preferenceKey.value = ''
  preferenceValue.value = ''
  preferenceStatus.value = '偏好已保存，并会注入后续会话。'
}

async function removePreference(key: string) {
  await agentApi.deletePreference(key)
  delete preferences.value[key]
  preferenceStatus.value = '偏好已删除。'
}

onMounted(async () => {
  await Promise.all([loadSessions(), loadPreferences()])
  inputRef.value?.focus()
})

onUnmounted(() => {
  disposed = true
  sseClient.value?.abort()
  clearRetry()
  closeVisualPreview()
})
</script>

<style scoped>
.assistant {
  position: relative;
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.assistant__overlay {
  display: none;
}

.assistant__sessions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 236px;
  flex: none;
  padding: 18px 12px;
  border-right: 1px solid var(--line);
  overflow-y: auto;
  background: color-mix(in srgb, var(--panel) 30%, transparent);
}

.sessions__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 6px 8px;
}

.sessions__close {
  display: none;
  color: var(--t3);
}

.sessions__search {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 2px 0;
  padding: 5px 8px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  color: var(--t3);
}

.sessions__search:focus-within {
  border-color: var(--gold);
}

.sessions__search input {
  width: 100%;
  font-size: 11px;
  color: var(--t1);
}

.sessions__search input::placeholder {
  color: var(--t3);
}

.sessions__list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}

.session {
  position: relative;
  display: grid;
  grid-template-columns: 2px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 8px 8px 0;
  border-radius: var(--r-sm);
  text-align: left;
  transition: background-color var(--d-fast) var(--ease-out);
}

.session:hover {
  background: var(--panel-2);
}

.session--active {
  background: var(--gold-soft);
}

.session__bar {
  width: 2px;
  height: 22px;
  margin-left: 0;
  border-radius: 2px;
  background: transparent;
}

.session--active .session__bar {
  background: var(--gold);
}

.session__main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding-left: 3px;
}

.session__title {
  font-size: 12px;
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session--active .session__title {
  color: var(--gold);
}

.session__meta {
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--t3);
}

.session__goal {
  font-size: 10px;
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session__delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--t3);
  opacity: 0;
  transition: opacity var(--d-fast) var(--ease-out);
}

.session:hover .session__delete {
  opacity: 1;
}

.session__delete:hover {
  color: var(--danger);
}

.sessions__empty {
  padding: 16px 6px;
  font-size: 11px;
  color: var(--t3);
}

.assistant__main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.assistant__head {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 22px;
  border-bottom: 1px solid var(--line);
  flex: none;
}

.assistant__menu {
  display: none;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--r-sm);
  color: var(--t2);
}

.assistant__menu:hover {
  background: var(--panel-2);
}

.assistant__title-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.assistant__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--text);
  white-space: nowrap;
}

.assistant__head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex: none;
}

.usage {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 8px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--t3);
}

.head-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  font-size: 11px;
  color: var(--t3);
}

.head-btn:hover {
  color: var(--t2);
  background: var(--panel-2);
}

.head-btn:disabled {
  opacity: 0.4;
}

.assistant__inspector-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--r-sm);
  color: var(--t2);
}

.offline {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 22px;
  border-bottom: 1px solid color-mix(in srgb, var(--danger) 35%, var(--line));
  background: color-mix(in srgb, var(--danger-soft) 55%, transparent);
  color: var(--danger);
  flex: none;
}

.offline__text {
  flex: 1;
  font-size: 11px;
}

.offline__retry {
  font-size: 11px;
  color: var(--danger);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.offline__close {
  color: var(--danger);
  opacity: 0.7;
}

.conversation {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 26px 28px 20px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.anchor-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-left: 2px solid var(--gold);
  border-radius: var(--r-md);
  background: var(--panel-2);
}

.anchor-bar__icon {
  color: var(--gold);
  flex: none;
}

.anchor-bar__label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.03em;
  color: var(--t3);
  flex: none;
}

.anchor-bar__goal {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.anchor-bar__updated {
  font-size: 9px;
  color: var(--success);
  flex: none;
}

.anchor-bar__version {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--gold);
  flex: none;
}

.task-bar {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  width: 100%;
  max-width: 720px;
  margin: var(--sp-2) auto 0;
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--line);
  border-left: 2px solid var(--steel);
  border-radius: var(--r-md);
  background: var(--panel-2);
}

.task-bar__icon {
  color: var(--steel);
  flex: none;
}

.task-bar__label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.03em;
  color: var(--t3);
  flex: none;
}

.task-bar__chips {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.task-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 3px var(--sp-2);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--panel);
  cursor: pointer;
  flex: none;
}

.task-chip:hover:not(:disabled) {
  border-color: var(--steel);
}

.task-chip:disabled {
  cursor: default;
  opacity: 0.65;
}

.task-chip--current {
  border-color: var(--steel);
  background: var(--panel-2);
}

.task-chip__title {
  font-size: 11px;
  color: var(--t2);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-chip__phase {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--t3);
  flex: none;
}

.task-chip__badge {
  font-size: 9px;
  color: var(--steel);
  flex: none;
}

.task-chip__status {
  font-size: 9px;
  color: var(--t3);
  flex: none;
}

.task-chip__restore {
  font-size: 9px;
  color: var(--steel);
  cursor: pointer;
  flex: none;
  padding: 0 4px;
  border-radius: var(--r-sm);
}

.task-chip__restore:hover {
  background: var(--steel-soft);
}

.conversation > :deep(.message) {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 70px 20px 30px;
  text-align: center;
}

.welcome__icon {
  color: var(--gold);
  margin-bottom: 14px;
}

.welcome__title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 500;
  letter-spacing: -0.03em;
}

.welcome__desc {
  margin-top: 8px;
  max-width: 420px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--t3);
}

.welcome__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 7px;
  margin-top: 20px;
}

.welcome__actions button {
  padding: 7px 11px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  font-size: 11px;
  color: var(--t3);
  transition: border-color var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out);
}

.welcome__actions button:hover {
  border-color: var(--line-strong);
  color: var(--gold);
}

.message-markdown {
  font-size: 14px;
  line-height: 1.85;
  color: var(--t2);
  word-break: break-word;
}

.message-markdown :deep(p) {
  margin: 0 0 0.9em;
}

.message-markdown :deep(strong) {
  color: var(--text);
}

.message-markdown :deep(ul),
.message-markdown :deep(ol) {
  margin: 0 0 0.9em;
  padding-left: 1.4em;
}

.message-markdown :deep(li::marker) {
  color: var(--gold);
}

.message-markdown :deep(code) {
  padding: 1px 5px;
  border-radius: var(--r-sm);
  background: var(--panel-2);
  font-family: var(--font-mono);
  font-size: 0.86em;
  color: var(--gold);
}

.message-markdown :deep(pre) {
  padding: 12px 14px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow-x: auto;
}

.message-markdown :deep(pre code) {
  padding: 0;
  background: transparent;
  color: var(--t2);
}

.message-markdown :deep(blockquote) {
  margin: 1em 0;
  padding: 4px 0 4px 14px;
  border-left: 2px solid var(--gold);
  color: var(--t2);
}

.message-markdown :deep(a) {
  color: var(--gold);
}

.message-markdown :deep(.citation) {
  display: inline-flex;
  align-items: center;
  margin: 0 var(--sp-1);
  padding: 0 var(--sp-1);
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  background: var(--gold-soft);
  color: var(--gold-deep);
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  line-height: 1.6;
  vertical-align: baseline;
  cursor: pointer;
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.message-markdown :deep(.citation:hover) {
  background: var(--gold-deep);
  color: var(--gold-ink);
}

.message-markdown :deep(.citation:focus-visible) {
  outline: 1px solid var(--gold);
  outline-offset: var(--sp-1);
}

.message-sources {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--sp-3);
  margin-top: var(--sp-4);
  scroll-margin-block: var(--sp-6);
}

.visual-evidence-list {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--sp-3);
  margin-top: var(--sp-4);
}

.visual-evidence-preview {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
}

.visual-evidence-preview__status {
  color: var(--t2);
  font-size: var(--fs-small);
}

.visual-evidence-preview__image {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
}

.source-save-preview {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
}

.source-save-preview__title {
  color: var(--text);
  font-size: var(--fs-body-l);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.source-save-preview__url {
  color: var(--t3);
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  overflow-wrap: anywhere;
}

.source-save-preview__excerpt {
  max-height: 24vh;
  overflow-y: auto;
  color: var(--t2);
  font-size: var(--fs-body-s);
  line-height: 1.7;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.source-save-preview__notice {
  color: var(--gold-deep);
  font-size: var(--fs-micro);
  line-height: 1.7;
}

.source-save-preview__risk {
  padding: var(--sp-3);
  border-left: 2px solid var(--gold-line);
  border-radius: var(--r-sm);
  background: var(--gold-soft);
  color: var(--t2);
  font-size: var(--fs-micro);
  line-height: 1.7;
}

.source-save-preview__error {
  color: var(--danger);
  font-size: var(--fs-micro);
  line-height: 1.7;
}

.stream-block {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
}

.stream-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.stream-trace {
  max-height: 240px;
  overflow-y: auto;
}

.stream-answer {
  padding-right: 10px;
}

.stream-cursor {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 7px;
  height: 14px;
  background: var(--gold);
  animation: blink 1s steps(2, start) infinite;
}

.typing {
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}

.typing i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--t3);
  animation: typing 1.2s ease-in-out infinite;
}

.typing i:nth-child(2) {
  animation-delay: 0.15s;
}

.typing i:nth-child(3) {
  animation-delay: 0.3s;
}

.approval-wrap {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
}

.composer {
  flex: none;
  padding: 12px 28px 14px;
  border-top: 1px solid var(--line);
}

.composer__box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: 6px 6px 6px 12px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  background: var(--panel);
  transition: border-color var(--d-fast) var(--ease-out), box-shadow var(--d-fast) var(--ease-out);
}

.composer__box:focus-within {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-soft);
}

.composer__input {
  flex: 1;
  min-width: 0;
  max-height: 140px;
  padding: 6px 0;
  background: transparent;
  border: 0;
  outline: none;
  resize: none;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}

.composer__input::placeholder {
  color: var(--t3);
}

.composer__send,
.composer__stop {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--r-md);
  flex: none;
}

.composer__send {
  background: var(--gold);
  color: var(--gold-ink);
}

.composer__send:disabled {
  opacity: 0.35;
}

.composer__stop {
  background: var(--danger-soft);
  color: var(--danger);
}

.composer__hint {
  margin-top: 7px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--t3);
}

.assistant__inspector {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 300px;
  flex: none;
  padding: 18px 16px 24px;
  border-left: 1px solid var(--line);
  overflow-y: auto;
  background: color-mix(in srgb, var(--panel) 30%, transparent);
}

.inspector__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.inspector__section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.inspector__section--trace {
  flex: 1;
  min-height: 160px;
  border-bottom: 0;
}

.inspector__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.inspector__export {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font-size: 10px;
  color: var(--t2);
}

.inspector__export:hover:not(:disabled) {
  color: var(--gold);
  border-color: var(--gold);
}

.inspector__export:disabled {
  opacity: 0.4;
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.usage-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
}

.usage-cell__value {
  font-size: 13px;
  color: var(--text);
}

.inspector__trace-scroll {
  flex: 1;
  min-height: 120px;
  max-height: 46vh;
  overflow-y: auto;
}

.prefs {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pref {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px;
  border-radius: var(--r-sm);
  background: var(--panel-2);
  font-size: 10px;
  color: var(--t3);
}

.pref b {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--gold);
}

.pref span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pref button {
  color: var(--t3);
}

.prefs__empty {
  font-size: 10px;
  color: var(--t3);
}

.prefs__form {
  display: grid;
  grid-template-columns: 1fr;
  gap: 5px;
}

.prefs__form input {
  height: 26px;
  padding: 0 8px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font-size: 10px;
  color: var(--text);
  outline: none;
}

.prefs__form input:focus {
  border-color: var(--gold);
}

.prefs__form button {
  height: 26px;
  border-radius: var(--r-sm);
  background: var(--panel-2);
  color: var(--t2);
  font-size: 10px;
}

.prefs__form button:disabled {
  opacity: 0.4;
}

.prefs__status {
  font-size: 9px;
  color: var(--success);
}

.turn-trace {
  margin-top: 12px;
  border-top: 1px solid var(--line);
  padding-top: 8px;
}

.turn-trace__head {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  list-style: none;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.03em;
  color: var(--t3);
}

.turn-trace__head::-webkit-details-marker {
  display: none;
}

.turn-trace__chevron {
  margin-left: auto;
  transition: transform var(--d-fast) var(--ease-out);
}

.turn-trace[open] .turn-trace__chevron {
  transform: rotate(180deg);
}

.turn-trace :deep(.trace) {
  margin-top: 6px;
}

.approval-record {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.03em;
}

.approval-record--approved {
  color: var(--success);
}

.approval-record--rejected {
  color: var(--danger);
}

.approval-record .readout {
  margin-left: auto;
  color: var(--t3);
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@keyframes typing {
  50% {
    opacity: 0.25;
    transform: translateY(-2px);
  }
}

@media (max-width: 1100px) {
  .assistant__inspector {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 5;
    background: var(--panel);
    border-left-color: var(--line-strong);
    transform: translateX(100%);
    transition: transform var(--d-panel) var(--ease-out);
  }

  .assistant__inspector--open {
    transform: translateX(0);
  }

  .assistant__inspector-toggle {
    display: inline-flex;
  }

  .assistant__overlay--right {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 4;
    background: var(--overlay);
  }
}

@media (max-width: 900px) {
  .assistant__sessions {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 5;
    width: 260px;
    background: var(--panel);
    border-right-color: var(--line-strong);
    transform: translateX(-100%);
    transition: transform var(--d-panel) var(--ease-out);
  }

  .assistant__sessions--open {
    transform: translateX(0);
  }

  .assistant__overlay {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 4;
    background: var(--overlay);
  }

  .assistant__menu {
    display: inline-flex;
  }

  .assistant__head {
    padding: 10px 16px;
  }

  .head-btn span,
  .usage {
    display: none;
  }

  .conversation {
    padding: 20px 16px;
  }

  .composer {
    padding: 10px 16px 12px;
  }
}

@media (max-width: 767px) {
  .assistant__title {
    font-size: 14px;
  }

  .conversation > :deep(.message) {
    max-width: 100%;
  }

  .stream-block,
  .approval-wrap {
    max-width: 100%;
  }
}
</style>
