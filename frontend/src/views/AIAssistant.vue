<template>
  <div class="ai-assistant">
    <div class="sidebar">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="createNewChat">
          <Plus :size="16" />
          新对话
        </button>
      </div>
      <div class="chat-list">
        <div 
          v-for="chat in chatList" 
          :key="chat.id"
          class="chat-item"
          :class="{ active: chat.id === currentChatId }"
          @click="switchChat(chat.id)"
        >
          <div class="chat-item-info">
            <MessageSquare :size="16" class="chat-icon" />
            <span class="chat-title">{{ chat.title }}</span>
          </div>
          <button class="delete-chat-btn" @click.stop="deleteChat(chat.id)">
            <X :size="14" />
          </button>
        </div>
        <div v-if="chatList.length === 0" class="empty-list">
          暂无历史对话
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="chat-header">
        <div class="header-info">
          <Bot :size="24" class="header-icon" />
          <div class="header-text">
            <h1>AI 助手</h1>
            <p class="header-desc">基于你的知识库进行智能对话</p>
          </div>
        </div>
        <div class="header-actions">
          <select v-model="selectedRole" class="role-select" @change="onRoleChange">
            <option v-for="role in roles" :key="role.key" :value="role.key">
              {{ role.name }}
            </option>
          </select>
          <button class="clear-btn" @click="clearChat" :disabled="messages.length === 0">
            <Trash2 :size="16" />
            清空对话
          </button>
        </div>
      </div>

    <div class="chat-container" ref="chatContainer">
      <div class="welcome-message" v-if="messages.length === 0">
        <div class="welcome-icon">
          <Sparkles :size="48" />
        </div>
        <h2>你好！我是 {{ selectedRole }}</h2>
        <p>我可以帮助你：</p>
        <ul>
          <li>回答关于知识库内容的问题</li>
          <li>帮你整理和总结笔记</li>
          <li>提供学习和知识管理的建议</li>
          <li>进行一般性的对话交流</li>
        </ul>
        <div class="current-role-info">
          当前角色：{{ roles.find(r => r.key === selectedRole)?.desc }}
        </div>
        <div class="quick-actions">
          <button 
            v-for="action in quickActions" 
            :key="action.text"
            class="quick-action-btn"
            @click="sendQuickAction(action.text)"
          >
            {{ action.text }}
          </button>
        </div>
      </div>

      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          <Bot v-if="msg.role === 'assistant'" :size="20" />
          <User v-else :size="20" />
        </div>
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(msg.content)"></div>
          <div v-if="msg.notes && msg.notes.length > 0" class="related-notes">
            <div class="notes-label">相关笔记：</div>
            <div class="note-links">
              <router-link 
                v-for="note in msg.notes" 
                :key="note.id"
                :to="`/notes/${note.id}`"
                class="note-link"
              >
                <FileText :size="14" />
                {{ note.title }}
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="message assistant loading">
        <div class="message-avatar">
          <Bot :size="20" />
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="input-container">
        <textarea
          v-model="inputMessage"
          placeholder="输入你的问题..."
          @keydown.enter.exact.prevent="sendMessage"
          :disabled="loading"
          rows="1"
          ref="inputRef"
        ></textarea>
        <button 
          class="send-btn" 
          @click="sendMessage" 
          :disabled="!inputMessage.trim() || loading"
        >
          <Send :size="18" />
        </button>
      </div>
      <div class="input-hint">
        按 Enter 发送消息
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { searchApi } from '@/api/search'
import { Bot, User, Send, Sparkles, FileText, Trash2, Plus, MessageSquare, X } from 'lucide-vue-next'

interface Message {
  role: 'user' | 'assistant'
  content: string
  notes?: { id: string; title: string }[]
}

interface ChatHistory {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

const STORAGE_KEY = 'ai_chat_history'

const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const chatList = ref<ChatHistory[]>([])
const currentChatId = ref<string>('')

const quickActions = [
  { text: '我有哪些笔记？' },
  { text: '帮我总结一下知识库' },
  { text: '如何更好地管理知识？' }
]

const roles = [
  { key: '知识问答助手', name: '知识问答助手', desc: '友善、专业、乐于助人' },
  { key: '技术专家', name: '技术专家', desc: '严谨、精确、逻辑性强' },
  { key: '创意写作助手', name: '创意写作助手', desc: '富有创意、想象力丰富' },
  { key: '学习教练', name: '学习教练', desc: '激励、耐心、循循善诱' }
]

const selectedRole = ref('知识问答助手')

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

function loadChatList() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      chatList.value = JSON.parse(saved)
    }
  } catch {
    chatList.value = []
  }
}

function saveChatList() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(chatList.value))
}

function createNewChat() {
  const newChat: ChatHistory = {
    id: generateId(),
    title: '新对话',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now()
  }
  chatList.value.unshift(newChat)
  currentChatId.value = newChat.id
  messages.value = []
  saveChatList()
}

function switchChat(chatId: string) {
  currentChatId.value = chatId
  const chat = chatList.value.find(c => c.id === chatId)
  if (chat) {
    messages.value = [...chat.messages]
    scrollToBottom()
  }
}

function deleteChat(chatId: string) {
  const index = chatList.value.findIndex(c => c.id === chatId)
  if (index > -1) {
    chatList.value.splice(index, 1)
    if (currentChatId.value === chatId) {
      if (chatList.value.length > 0) {
        switchChat(chatList.value[0].id)
      } else {
        createNewChat()
      }
    }
    saveChatList()
  }
}

function updateCurrentChat() {
  if (!currentChatId.value) return
  const chat = chatList.value.find(c => c.id === currentChatId.value)
  if (chat) {
    chat.messages = [...messages.value]
    chat.updatedAt = Date.now()
    if (messages.value.length > 0 && chat.title === '新对话') {
      const firstMsg = messages.value[0].content
      chat.title = firstMsg.slice(0, 20) + (firstMsg.length > 20 ? '...' : '')
    }
    chatList.value.sort((a, b) => b.updatedAt - a.updatedAt)
    saveChatList()
  }
}

watch(messages, () => {
  updateCurrentChat()
}, { deep: true })

function formatMessage(content: string): string {
  return content
    .replace(/\n/g, '<br>')
    .replace(/【([^】]+)】/g, '<strong>【$1】</strong>')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

async function sendMessage() {
  const message = inputMessage.value.trim()
  if (!message || loading.value) return

  messages.value.push({
    role: 'user',
    content: message
  })
  
  inputMessage.value = ''
  scrollToBottom()
  loading.value = true

  try {
    const history = messages.value.slice(-6).map(m => ({
      role: m.role,
      content: m.content
    }))

    const response = await searchApi.aiChat(message, history, currentChatId.value)
    
    messages.value.push({
      role: 'assistant',
      content: response.data.answer,
      notes: response.data.notes
    })
  } catch (error: any) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，发生了错误：' + (error.message || '未知错误')
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function sendQuickAction(text: string) {
  inputMessage.value = text
  sendMessage()
}

function clearChat() {
  messages.value = []
}

function onRoleChange() {
  localStorage.setItem('ai_role', selectedRole.value)
}

onMounted(() => {
  inputRef.value?.focus()
  loadChatList()
  const savedRole = localStorage.getItem('ai_role')
  if (savedRole) {
    selectedRole.value = savedRole
  }
  if (chatList.value.length === 0) {
    createNewChat()
  } else {
    switchChat(chatList.value[0].id)
  }
})
</script>

<style scoped lang="scss">
.ai-assistant {
  display: flex;
  height: calc(100vh - 60px);
  background: var(--bg-primary);
}

.sidebar {
  width: 240px;
  border-right: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--primary-hover);
  }
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 4px;

  &:hover {
    background: var(--bg-hover);
  }

  &.active {
    background: var(--primary-muted);
  }
}

.chat-item-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.chat-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.chat-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-chat-btn {
  display: none;
  padding: 4px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;

  &:hover {
    background: var(--bg-tertiary);
    color: var(--danger-color);
  }
}

.chat-item:hover .delete-chat-btn {
  display: flex;
}

.empty-list {
  text-align: center;
  padding: 24px 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  color: var(--primary-color);
}

.header-text {
  h1 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .header-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 4px 0 0;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.role-select {
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: var(--primary-color);
  }

  option {
    background: var(--bg-primary);
    color: var(--text-primary);
    padding: 8px;
  }
}

.clear-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover:not(:disabled) {
    background: var(--bg-hover);
    border-color: var(--border-strong);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome-message {
  max-width: 500px;
  margin: 60px auto;
  text-align: center;

  .welcome-icon {
    width: 80px;
    height: 80px;
    margin: 0 auto 24px;
    background: var(--primary-muted);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-color);
  }

  h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 16px;
  }

  p {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0 0 12px;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0 0 24px;
    text-align: left;

    li {
      padding: 8px 0;
      font-size: 14px;
      color: var(--text-secondary);
      position: relative;
      padding-left: 20px;

      &::before {
        content: '•';
        position: absolute;
        left: 0;
        color: var(--primary-color);
      }
    }
  }

  .current-role-info {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 24px;
  }

  .quick-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  .quick-action-btn {
    padding: 10px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      border-color: var(--primary-color);
      color: var(--text-primary);
    }
  }
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 800px;

  &.user {
    flex-direction: row-reverse;
    margin-left: auto;

    .message-content {
      background: var(--primary-color);
      color: #000;
    }
  }

  &.assistant {
    .message-content {
      background: var(--bg-secondary);
      border: 1px solid var(--border-subtle);
    }
  }

  &.loading {
    .message-content {
      background: var(--bg-secondary);
      border: 1px solid var(--border-subtle);
    }
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text-muted);
}

.message-content {
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  max-width: 70%;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;

  strong {
    color: var(--primary-color);
  }
}

.related-notes {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.notes-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.note-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.note-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--primary-muted);
    color: var(--primary-color);
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;

  span {
    width: 8px;
    height: 8px;
    background: var(--text-muted);
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;

    &:nth-child(1) { animation-delay: 0s; }
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

.input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}

.input-container {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  max-width: 800px;
  margin: 0 auto;

  textarea {
    flex: 1;
    padding: 12px 16px;
    background: var(--bg-primary);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 14px;
    resize: none;
    min-height: 44px;
    max-height: 120px;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    &::placeholder {
      color: var(--text-muted);
    }

    &:disabled {
      opacity: 0.6;
    }
  }
}

.send-btn {
  width: 44px;
  height: 44px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);

  &:hover:not(:disabled) {
    background: var(--primary-hover);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.input-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}
</style>
