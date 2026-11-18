<template>
  <div class="trace">
    <p v-if="!events.length" class="trace__empty">{{ emptyText }}</p>

    <details
      v-for="(event, index) in events"
      :key="event.id || `${event.type}-${index}`"
      :class="['trace__card', `trace__card--${event.type}`]"
      :open="index === events.length - 1 && event.type === 'action'"
    >
      <summary class="trace__head">
        <component :is="iconOf(event.type)" :size="12" :stroke-width="1.8" class="trace__icon" />
        <span class="trace__label">{{ labelOf(event) }}</span>
        <span v-if="event.latency_ms !== undefined" class="num trace__latency">{{ event.latency_ms }}ms</span>
        <span v-if="event.status" :class="['trace__status', `trace__status--${event.status}`]">
          {{ statusOf(event.status) }}
        </span>
        <ChevronDown :size="12" :stroke-width="1.8" class="trace__chevron" />
      </summary>
      <pre class="trace__body">{{ textOf(event) }}</pre>
    </details>
  </div>
</template>

<script setup lang="ts">
import { Brain, ChevronDown, Compass, Eye, ShieldCheck, Wrench } from 'lucide-vue-next'
import type { TimelineEvent } from '@/api/agent'

withDefaults(defineProps<{ events: TimelineEvent[]; emptyText?: string }>(), {
  emptyText: 'Agent 运行后，这里会显示思考、工具调用与检查过程。'
})

const LABELS: Record<string, string> = {
  thought: '思考',
  action: '工具调用',
  observation: '观察',
  check: '质量检查',
  intent: '意图识别',
  tool: '工具'
}

const STATUS: Record<string, string> = {
  success: '成功',
  pending: '待审批',
  rejected: '已拒绝',
  error: '失败'
}

function iconOf(type: TimelineEvent['type']) {
  if (type === 'thought') return Brain
  if (type === 'observation') return Eye
  if (type === 'check') return ShieldCheck
  if (type === 'intent') return Compass
  return Wrench
}

function labelOf(event: TimelineEvent) {
  if (event.type === 'tool' && event.tool_name) return event.tool_name
  if (event.type === 'action' && event.tool_name) return `调用 ${event.tool_name}`
  return LABELS[event.type] ?? event.type
}

function textOf(event: TimelineEvent) {
  if (event.content) return event.content
  const parts: string[] = []
  if (event.args) parts.push(`参数：${JSON.stringify(event.args, null, 2)}`)
  if (event.result) {
    const result = typeof event.result === 'string' ? event.result : JSON.stringify(event.result, null, 2)
    parts.push(`结果：${result}`)
  }
  return parts.join('\n\n') || '处理中…'
}

function statusOf(status: string) {
  return STATUS[status] ?? status
}
</script>

<style scoped>
.trace {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.trace__empty {
  padding: 10px 4px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--t3);
}

.trace__card {
  border: 1px solid var(--line);
  border-left: 2px solid var(--line-strong);
  border-radius: var(--r-sm);
  background: color-mix(in srgb, var(--panel) 35%, transparent);
  overflow: hidden;
}

.trace__card--action {
  border-left-color: var(--gold);
}

.trace__card--check {
  border-left-color: var(--sage);
}

.trace__card--intent {
  border-left-color: var(--steel);
}

.trace__head {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 28px;
  padding: 0 8px;
  cursor: pointer;
  list-style: none;
}

.trace__head::-webkit-details-marker {
  display: none;
}

.trace__icon {
  color: var(--t3);
}

.trace__card--action .trace__icon {
  color: var(--gold);
}

.trace__label {
  flex: 1;
  min-width: 0;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.03em;
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace__latency {
  font-size: 8.5px;
  color: var(--t3);
}

.trace__status {
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

.trace__status--success {
  color: var(--success);
}

.trace__status--error,
.trace__status--rejected {
  color: var(--danger);
}

.trace__status--pending {
  color: var(--gold);
}

.trace__chevron {
  color: var(--t3);
  transition: transform var(--d-fast) var(--ease-out);
}

.trace__card[open] .trace__chevron {
  transform: rotate(180deg);
}

.trace__body {
  max-height: 220px;
  margin: 0;
  padding: 8px 10px 10px;
  border-top: 1px solid var(--line);
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.7;
  color: var(--t3);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
