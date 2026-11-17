<template>
  <section v-if="!decided" class="approval" aria-label="待审批操作">
    <span class="readout approval__kicker">APPROVAL REQUIRED</span>

    <div class="approval__content">
      <h3 class="approval__title">{{ title }}</h3>
      <p v-if="summary" class="approval__summary">{{ summary }}</p>

      <div v-if="payload" class="approval__payload">
        <pre class="approval__preview" :class="{ 'approval__preview--expanded': expanded }">{{ payload }}</pre>
        <button type="button" class="approval__toggle" @click="expanded = !expanded">
          {{ expanded ? '收起参数' : '展开完整参数' }}
          <ChevronDown :size="12" :class="['approval__chevron', expanded && 'approval__chevron--open']" />
        </button>
      </div>
    </div>

    <footer class="approval__actions">
      <AppButton size="sm" @click="approve">批准执行</AppButton>
      <AppButton variant="ghost" size="sm" @click="reject">拒绝</AppButton>
      <span class="approval__hint">
        <Kbd keys="Y" /> 批准
        <Kbd keys="N" /> 拒绝
      </span>
    </footer>
  </section>

  <div v-else class="approval-record" :class="`approval-record--${status}`">
    <component :is="approved ? Check : X" :size="13" :stroke-width="2" />
    <span>{{ approved ? '已批准' : '已拒绝' }}</span>
    <span v-if="decidedAt" class="approval-record__time">{{ decidedAt }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, ChevronDown, X } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import Kbd from '@/components/ui/Kbd.vue'

const props = withDefaults(
  defineProps<{
    title: string
    summary?: string
    payload?: string
    status?: 'pending' | 'approved' | 'rejected'
    decidedAt?: string
  }>(),
  { summary: '', payload: '', status: 'pending', decidedAt: '' }
)

const emit = defineEmits<{ approve: []; reject: [] }>()

const expanded = ref(false)
const decided = computed(() => props.status !== 'pending')
const approved = computed(() => props.status === 'approved')

function approve() {
  if (decided.value) return
  emit('approve')
}

function reject() {
  if (decided.value) return
  emit('reject')
}

function onKeydown(event: KeyboardEvent) {
  if (decided.value) return
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  if (event.metaKey || event.ctrlKey || event.altKey) return

  const key = event.key.toLowerCase()
  if (key === 'y') {
    event.preventDefault()
    approve()
  } else if (key === 'n') {
    event.preventDefault()
    reject()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.approval {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px 14px 18px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
}

.approval::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background: var(--gold);
  border-radius: 2px;
}

.approval__kicker {
  color: var(--gold);
}

.approval__title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
}

.approval__summary {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--t2);
}

.approval__payload {
  margin-top: 10px;
}

.approval__preview {
  max-height: 54px;
  overflow: hidden;
  padding: 8px 10px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-all;
  transition: max-height var(--d-panel) var(--ease-out);
}

.approval__preview--expanded {
  max-height: 320px;
  overflow-y: auto;
}

.approval__toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 11px;
  color: var(--t3);
}

.approval__toggle:hover {
  color: var(--gold);
}

.approval__chevron {
  transition: transform var(--d-base) var(--ease-out);
}

.approval__chevron--open {
  transform: rotate(180deg);
}

.approval__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.approval__hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  font-size: 10px;
  color: var(--t3);
}

.approval-record {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

.approval-record--approved {
  color: var(--success);
}

.approval-record--rejected {
  color: var(--danger);
}

.approval-record__time {
  color: var(--t3);
}
</style>
