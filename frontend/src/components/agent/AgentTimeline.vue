<template>
  <div class="agent-timeline">
    <div v-if="events.length === 0" class="empty-state">
      Agent 运行后，这里会显示思考、工具调用与检查过程。
    </div>
    <div v-for="(event, index) in events" :key="event.id || `${event.type}-${index}`" class="timeline-item">
      <div class="timeline-marker" :class="event.type">
        <Brain v-if="event.type === 'thought'" :size="14" />
        <Play v-else-if="event.type === 'action'" :size="14" />
        <Eye v-else-if="event.type === 'observation'" :size="14" />
        <ShieldCheck v-else-if="event.type === 'check'" :size="14" />
        <Compass v-else-if="event.type === 'intent'" :size="14" />
        <Wrench v-else :size="14" />
      </div>
      <div class="timeline-content">
        <div class="event-heading">
          <span>{{ eventLabel(event) }}</span>
          <span v-if="event.latency_ms !== undefined" class="latency">{{ event.latency_ms }} ms</span>
        </div>
        <p>{{ eventText(event) }}</p>
        <span v-if="event.status" class="status" :class="event.status">{{ statusLabel(event.status) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Brain, Compass, Eye, Play, ShieldCheck, Wrench } from 'lucide-vue-next'
import type { TimelineEvent } from '@/api/agent'

defineProps<{ events: TimelineEvent[] }>()

function eventLabel(event: TimelineEvent): string {
  if (event.type === 'tool') return event.tool_name || '工具调用'
  const labels: Record<string, string> = {
    thought: '思考',
    action: '行动',
    observation: '观察',
    check: '质量检查',
    intent: '意图识别'
  }
  return labels[event.type] || event.type
}

function eventText(event: TimelineEvent): string {
  if (event.content) return event.content
  if (event.type === 'tool') {
    const args = event.args ? `参数：${JSON.stringify(event.args)}` : ''
    const result = event.result ? `结果：${typeof event.result === 'string' ? event.result : JSON.stringify(event.result)}` : ''
    return [args, result].filter(Boolean).join(' · ') || '工具调用已完成'
  }
  return '处理中…'
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    success: '成功',
    pending: '待审批',
    rejected: '已拒绝',
    error: '失败'
  }
  return labels[status] || status
}
</script>

<style scoped lang="scss">
.agent-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.empty-state {
  padding: 28px 12px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
  text-align: center;
}

.timeline-item {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 8px;
  position: relative;
  padding-bottom: 16px;

  &:not(:last-child)::after {
    content: '';
    position: absolute;
    left: 13px;
    top: 28px;
    bottom: 0;
    width: 1px;
    background: var(--border-default);
  }
}

.timeline-marker {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  color: var(--text-muted);
  border: 1px solid var(--border-default);
  z-index: 1;

  &.thought { color: var(--accent-purple); }
  &.action, &.tool { color: var(--accent-blue); }
  &.observation { color: var(--accent-green); }
  &.check { color: var(--primary-color); }
  &.intent { color: var(--accent-purple); }
}

.timeline-content {
  min-width: 0;
  padding-top: 3px;

  p {
    margin: 5px 0 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.6;
    word-break: break-word;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.event-heading {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
}

.latency {
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 400;
}

.status {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 10px;
  color: var(--text-muted);
  background: var(--bg-hover);

  &.success { color: var(--accent-green); }
  &.pending { color: var(--primary-color); }
  &.rejected, &.error { color: var(--accent-red); }
}
</style>
