<template>
  <div class="ai-assistant">
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="createNewChat">
          <Plus :size="16" /> 新对话
        </button>
      </div>
      <div class="chat-list">
        <button
          v-for="chat in chatList"
          :key="chat.id"
          class="chat-item"
          :class="{ active: chat.id === currentChatId }"
          @click="switchChat(chat.id)"
        >
          <span class="chat-item-info">
            <MessageSquare :size="16" />
            <span class="chat-title">{{ chat.title }}</span>
          </span>
          <span class="delete-chat-btn" @click.stop="deleteChat(chat.id)"><X :size="14" /></span>
        </button>
        <div v-if="chatList.length === 0" class="empty-list">暂无历史对话</div>
      </div>
    </aside>

    <main class="main-content">
      <header class="chat-header">
        <div class="header-info">
          <Bot :size="24" class="header-icon" />
          <div>
            <h1>Agentic RAG 助手</h1>
            <p>多轮记忆 · 工具调用 · 三查反思 · 人工审批</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="header-btn" @click="showPreferences = !showPreferences">
            <SlidersHorizontal :size="16" /> 长期偏好
          </button>
          <router-link class="header-btn" to="/observability">
            <Activity :size="16" /> 可观测面板
          </router-link>
          <button class="header-btn" :disabled="messages.length === 0" @click="clearChat">
            <Trash2 :size="16" /> 清空
          </button>
        </div>
      </header>

      <div v-if="showPreferences" class="preferences-panel">
        <div class="preferences-heading">
          <div>
            <strong>跨会话长期偏好</strong>
            <span>保存后，后续所有 Agent 会话都会自动读取。</span>
          </div>
          <button @click="showPreferences = false"><X :size="16" /></button>
        </div>
        <div class="preference-tags">
          <span v-for="(value, key) in preferences" :key="key" class="preference-tag">
            <b>{{ key }}</b> {{ value }}
            <button @click="removePreference(String(key))"><X :size="12" /></button>
          </span>
          <span v-if="Object.keys(preferences).length === 0" class="preference-empty">尚未设置偏好</span>
        </div>
        <div class="preference-form">
          <input v-model="preferenceKey" placeholder="偏好名称，如 answer_style" />
          <input v-model="preferenceValue" placeholder="偏好内容，如 简洁、先给结论" @keydown.enter="savePreference" />
          <button :disabled="!preferenceKey.trim() || !preferenceValue.trim()" @click="savePreference">保存</button>
        </div>
        <span v-if="preferenceStatus" class="preference-status">{{ preferenceStatus }}</span>
      </div>

      <div class="assistant-workspace">
        <section class="conversation-column">
          <div ref="chatContainer" class="chat-container">
            <div v-if="messages.length === 0" class="welcome-message">
              <div class="welcome-icon"><Sparkles :size="42" /></div>
              <h2>和你的知识库一起思考</h2>
              <p>Agent 会自主检索、调用工具，并在写入笔记前请求你的确认。</p>
              <div class="quick-actions">
                <button v-for="action in quickActions" :key="action" @click="sendQuickAction(action)">
                  {{ action }}
                </button>
              </div>
            </div>

            <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
              <div class="message-avatar">
                <Bot v-if="message.role === 'assistant'" :size="19" />
                <User v-else :size="19" />
              </div>
              <div class="message-content">
                <div class="message-text" v-html="formatMessage(message.content)"></div>
              </div>
            </div>

            <div v-if="isStreaming && streamingContent" class="message assistant streaming">
              <div class="message-avatar"><Bot :size="19" /></div>
              <div class="message-content">
                <div class="message-text">{{ streamingContent }}</div>
              </div>
            </div>

            <div v-if="loading && !streamingContent && !pendingApproval" class="message assistant loading">
              <div class="message-avatar"><Bot :size="19" /></div>
              <div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
            </div>

            <ApprovalCard
              v-if="pendingApproval"
              :approval="pendingApproval"
              :disabled="loading"
              @decide="resumeApproval"
            />
          </div>

          <div class="input-area">
            <div class="input-container">
              <textarea
                ref="inputRef"
                v-model="inputMessage"
                rows="1"
                placeholder="输入问题，或让 Agent 创建一篇笔记…"
                :disabled="loading || !!pendingApproval"
                @keydown.enter.exact.prevent="sendMessage"
              ></textarea>
              <button v-if="!isStreaming" class="send-btn" :disabled="!inputMessage.trim() || loading || !!pendingApproval" @click="sendMessage">
                <Send :size="18" />
              </button>
              <button v-else class="stop-btn" @click="stopStreaming"><Square :size="17" /></button>
            </div>
            <div class="input-hint">会话由 LangGraph checkpoint 持久化 · 写操作必须审批</div>
          </div>
        </section>

        <aside class="timeline-panel">
          <div class="timeline-header">
            <div><Activity :size="16" /><strong>Agent 时间线</strong></div>
            <span>{{ combinedTimeline.length }} 事件</span>
          </div>
          <div class="timeline-scroll"><AgentTimeline :events="combinedTimeline" /></div>
        </aside>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  Activity, Bot, MessageSquare, Plus, Send, SlidersHorizontal,
  Sparkles, Square, Trash2, User, X
} from 'lucide-vue-next'
import { agentApi, type AgentMessage, type AgentSession, type TimelineEvent } from '@/api/agent'
import AgentTimeline from '@/components/agent/AgentTimeline.vue'
import ApprovalCard from '@/components/agent/ApprovalCard.vue'
import { useAuthStore } from '@/stores/auth'
import { SSEClient, type SSEMessage } from '@/utils/sse'

const messages = ref<AgentMessage[]>([])
const chatList = ref<AgentSession[]>([])
const currentChatId = ref('')
const inputMessage = ref('')
const loading = ref(false)
const isStreaming = ref(false)
const streamingContent = ref('')
const persistedTimeline = ref<TimelineEvent[]>([])
const liveTimeline = ref<TimelineEvent[]>([])
const pendingApproval = ref<SSEMessage | null>(null)
const chatContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const sseClient = ref<SSEClient | null>(null)
const authStore = useAuthStore()

const showPreferences = ref(false)
const preferences = ref<Record<string, string>>({})
const preferenceKey = ref('')
const preferenceValue = ref('')
const preferenceStatus = ref('')

const quickActions = ['我有哪些笔记？', '帮我总结一下知识库', '对比最近的两篇笔记']
const combinedTimeline = computed(() => [...persistedTimeline.value, ...liveTimeline.value])

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;')
}

function formatMessage(content: string): string {
  return escapeHtml(content).replace(/\n/g, '<br>').replace(/【([^】]+)】/g, '<strong>【$1】</strong>')
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

async function createNewChat() {
  const chat = await agentApi.createSession()
  chatList.value.unshift(chat)
  await switchChat(chat.id)
}

async function switchChat(chatId: string) {
  // 中止旧会话的流式响应，避免 thought/审批卡等事件串扰到新会话
  sseClient.value?.abort()
  sseClient.value = null
  currentChatId.value = chatId
  pendingApproval.value = null
  streamingContent.value = ''
  loading.value = false
  isStreaming.value = false
  liveTimeline.value = []
  const [chatData, timeline] = await Promise.all([
    agentApi.getMessages(chatId),
    agentApi.getTimeline(chatId)
  ])
  messages.value = chatData.messages
  // 恢复 checkpoint 中尚未处理的审批请求（如刷新页面/切换会话导致审批卡丢失）
  pendingApproval.value = chatData.pending_approval
  persistedTimeline.value = timeline
  scrollToBottom()
}

async function deleteChat(chatId: string) {
  if (!window.confirm('确认删除该会话及其 checkpoint 和审计记录？')) return
  await agentApi.deleteSession(chatId)
  chatList.value = chatList.value.filter(chat => chat.id !== chatId)
  if (currentChatId.value === chatId) {
    if (chatList.value.length) await switchChat(chatList.value[0].id)
    else await createNewChat()
  }
}

async function clearChat() {
  if (!currentChatId.value) return
  sseClient.value?.abort()
  sseClient.value = null
  await agentApi.clearSession(currentChatId.value)
  messages.value = []
  persistedTimeline.value = []
  liveTimeline.value = []
  pendingApproval.value = null
}

function apiBase(): string {
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
}

function handleStreamMessage(message: SSEMessage) {
  if (['thought', 'action', 'observation', 'check', 'intent'].includes(message.type)) {
    if (message.content) {
      liveTimeline.value.push({ type: message.type as TimelineEvent['type'], content: message.content, node: message.node })
    }
  } else if (message.type === 'final_answer') {
    streamingContent.value = message.answer || ''
  } else if (message.type === 'approval_required') {
    pendingApproval.value = message
  } else if (message.type === 'error') {
    liveTimeline.value.push({ type: 'observation', content: message.message || 'Agent 执行异常', status: 'error' })
  }
  scrollToBottom()
}

async function refreshAfterStream() {
  if (streamingContent.value) {
    messages.value.push({ role: 'assistant', content: streamingContent.value })
  }
  streamingContent.value = ''
  loading.value = false
  isStreaming.value = false
  if (currentChatId.value) {
    persistedTimeline.value = await agentApi.getTimeline(currentChatId.value)
    chatList.value = await agentApi.listSessions()
  }
  scrollToBottom()
}

async function restorePendingState() {
  if (!currentChatId.value) return
  try {
    const chatData = await agentApi.getMessages(currentChatId.value)
    messages.value = chatData.messages
    pendingApproval.value = chatData.pending_approval
  } catch { /* 恢复失败时保持当前界面状态 */ }
}

async function connectStream(
  url: string,
  body: Record<string, unknown> = {},
  onConflict?: () => void
) {
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
        // 会话存在待审批操作：恢复审批卡，并把未发送的问题放回输入框
        await restorePendingState()
        messages.value.push({ role: 'assistant', content: '该会话存在待审批操作，请先在审批卡中确认或拒绝。' })
        onConflict?.()
        scrollToBottom()
      } else {
        messages.value.push({ role: 'assistant', content: `连接 Agent 失败：${error.message}` })
        scrollToBottom()
      }
    },
    onComplete: () => { void refreshAfterStream() }
  })
}

async function sendMessage() {
  const question = inputMessage.value.trim()
  if (!question || loading.value || pendingApproval.value) return
  if (!currentChatId.value) await createNewChat()

  messages.value.push({ role: 'user', content: question })
  inputMessage.value = ''
  liveTimeline.value = []
  streamingContent.value = ''
  loading.value = true
  isStreaming.value = true
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
  streamingContent.value = ''
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
  preferenceStatus.value = '偏好已保存，并会注入后续 Agent 会话。'
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

onUnmounted(() => sseClient.value?.abort())
</script>

<style scoped lang="scss">
.ai-assistant { display: flex; height: calc(100vh - 60px); background: var(--bg-primary); }
.chat-sidebar { width: 230px; border-right: 1px solid var(--border-subtle); background: var(--bg-secondary); display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 14px; border-bottom: 1px solid var(--border-subtle); }
.new-chat-btn { width: 100%; display: flex; justify-content: center; align-items: center; gap: 7px; padding: 9px 12px; border-radius: var(--radius-md); background: var(--primary-color); color: #111; font-size: 13px; font-weight: 600; }
.chat-list { padding: 8px; overflow-y: auto; }
.chat-item { width: 100%; color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; padding: 9px 10px; border-radius: var(--radius-sm); margin-bottom: 3px; text-align: left; &:hover, &.active { background: var(--bg-active); color: var(--text-primary); } }
.chat-item-info { display: flex; align-items: center; gap: 8px; min-width: 0; }
.chat-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.delete-chat-btn { display: none; padding: 3px; color: var(--text-muted); }
.chat-item:hover .delete-chat-btn { display: flex; }
.empty-list { padding: 24px; text-align: center; color: var(--text-muted); font-size: 12px; }

.main-content { flex: 1; min-width: 0; display: flex; flex-direction: column; position: relative; }
.chat-header { min-height: 70px; padding: 13px 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--border-subtle); background: var(--bg-secondary); }
.header-info { display: flex; align-items: center; gap: 11px; h1 { margin: 0; color: var(--text-primary); font-size: 17px; } p { margin: 2px 0 0; color: var(--text-muted); font-size: 11px; } }
.header-icon { color: var(--primary-color); }
.header-actions { display: flex; gap: 7px; }
.header-btn { display: flex; align-items: center; gap: 6px; padding: 7px 9px; color: var(--text-secondary); border: 1px solid var(--border-default); border-radius: var(--radius-sm); font-size: 11px; &:hover { color: var(--text-primary); background: var(--bg-hover); } &:disabled { opacity: .4; } }

.preferences-panel { position: absolute; z-index: 10; top: 62px; right: 20px; width: min(520px, calc(100% - 40px)); padding: 16px; background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: var(--radius-lg); box-shadow: 0 18px 50px rgba(0,0,0,.35); }
.preferences-heading { display: flex; justify-content: space-between; gap: 16px; strong { display: block; font-size: 13px; } span { color: var(--text-muted); font-size: 11px; } button { color: var(--text-muted); } }
.preference-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 13px 0; }
.preference-tag { display: flex; align-items: center; gap: 5px; padding: 5px 8px; border-radius: 999px; background: var(--primary-muted); color: var(--text-secondary); font-size: 10px; b { color: var(--primary-color); } button { display: flex; color: var(--text-muted); } }
.preference-empty, .preference-status { color: var(--text-muted); font-size: 10px; }
.preference-form { display: grid; grid-template-columns: .8fr 1.4fr auto; gap: 7px; input { min-width: 0; padding: 8px 9px; background: var(--bg-primary); border: 1px solid var(--border-default); border-radius: var(--radius-sm); font-size: 11px; } button { padding: 8px 12px; background: var(--primary-color); color: #111; border-radius: var(--radius-sm); font-size: 11px; font-weight: 600; &:disabled { opacity: .4; } } }

.assistant-workspace { flex: 1; min-height: 0; display: flex; }
.conversation-column { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.chat-container { flex: 1; overflow-y: auto; padding: 22px; }
.timeline-panel { width: 310px; flex-shrink: 0; border-left: 1px solid var(--border-subtle); background: var(--bg-secondary); display: flex; flex-direction: column; }
.timeline-header { min-height: 48px; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; border-bottom: 1px solid var(--border-subtle); div { display: flex; align-items: center; gap: 7px; color: var(--primary-color); } strong { color: var(--text-primary); font-size: 12px; } span { color: var(--text-muted); font-size: 10px; } }
.timeline-scroll { padding: 14px; overflow-y: auto; }

.welcome-message { max-width: 520px; margin: 70px auto; text-align: center; h2 { margin: 16px 0 8px; font-size: 22px; } p { color: var(--text-secondary); font-size: 13px; } }
.welcome-icon { width: 70px; height: 70px; margin: auto; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--primary-color); background: var(--primary-muted); }
.quick-actions { margin-top: 22px; display: flex; justify-content: center; flex-wrap: wrap; gap: 7px; button { padding: 8px 11px; border: 1px solid var(--border-default); border-radius: var(--radius-md); color: var(--text-secondary); font-size: 11px; &:hover { border-color: var(--primary-color); color: var(--text-primary); } } }

.message { display: flex; gap: 10px; max-width: 760px; margin-bottom: 17px; &.user { flex-direction: row-reverse; margin-left: auto; .message-content { background: var(--primary-color); color: #111; border-color: transparent; } } &.streaming .message-content { border-color: var(--primary-color); } }
.message-avatar { width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--bg-tertiary); color: var(--text-muted); flex-shrink: 0; }
.message-content { max-width: min(680px, 78%); padding: 11px 14px; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); }
.message-text { font-size: 13px; line-height: 1.7; word-break: break-word; :deep(strong) { color: var(--primary-color); } }
.typing-indicator { display: flex; gap: 4px; padding: 5px 0; span { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); animation: typing 1.2s infinite; &:nth-child(2) { animation-delay: .15s; } &:nth-child(3) { animation-delay: .3s; } } }
@keyframes typing { 50% { opacity: .25; transform: translateY(-3px); } }

.input-area { padding: 13px 20px; border-top: 1px solid var(--border-subtle); background: var(--bg-secondary); }
.input-container { max-width: 800px; margin: auto; display: flex; gap: 9px; align-items: flex-end; textarea { flex: 1; min-height: 42px; max-height: 120px; resize: none; padding: 11px 13px; background: var(--bg-primary); border: 1px solid var(--border-default); border-radius: var(--radius-md); font-size: 13px; &:focus { border-color: var(--primary-color); } &:disabled { opacity: .55; } } }
.send-btn, .stop-btn { width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-md); }
.send-btn { color: #111; background: var(--primary-color); &:disabled { opacity: .4; } }
.stop-btn { color: white; background: var(--danger-color); }
.input-hint { margin-top: 6px; text-align: center; color: var(--text-muted); font-size: 10px; }

@media (max-width: 1100px) { .timeline-panel { width: 260px; } .header-btn { span { display: none; } } }
@media (max-width: 850px) { .chat-sidebar { width: 190px; } .timeline-panel { display: none; } .header-actions .header-btn { font-size: 0; } }
</style>
