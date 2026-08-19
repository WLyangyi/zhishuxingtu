<template>
  <div class="approval-card">
    <div class="approval-icon"><ShieldAlert :size="22" /></div>
    <div class="approval-body">
      <div class="approval-kicker">需要你的确认</div>
      <h3>{{ approval.title || 'Agent 写操作' }}</h3>
      <p>{{ approval.description }}</p>
      <div class="note-preview">
        <strong>{{ approval.preview?.title || approval.args?.title || '未命名笔记' }}</strong>
        <span>{{ approval.preview?.content || approval.args?.content }}</span>
      </div>
      <div class="approval-actions">
        <button class="reject" :disabled="disabled" @click="$emit('decide', false)">拒绝</button>
        <button class="approve" :disabled="disabled" @click="$emit('decide', true)">
          <Check :size="15" /> 确认创建
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Check, ShieldAlert } from 'lucide-vue-next'
import type { SSEMessage } from '@/utils/sse'

defineProps<{ approval: SSEMessage; disabled?: boolean }>()
defineEmits<{ decide: [approved: boolean] }>()
</script>

<style scoped lang="scss">
.approval-card {
  max-width: 680px;
  display: flex;
  gap: 14px;
  padding: 18px;
  margin: 0 0 20px 48px;
  background: linear-gradient(135deg, var(--primary-muted), var(--bg-secondary));
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: var(--radius-lg);
}

.approval-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  background: var(--primary-muted);
  flex-shrink: 0;
}

.approval-body {
  flex: 1;
  min-width: 0;

  h3 { margin: 2px 0 6px; font-size: 15px; color: var(--text-primary); }
  p { margin: 0 0 12px; font-size: 12px; color: var(--text-secondary); }
}

.approval-kicker {
  color: var(--primary-color);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.note-preview {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);

  strong { font-size: 13px; color: var(--text-primary); }
  span { font-size: 12px; color: var(--text-muted); white-space: pre-wrap; max-height: 80px; overflow: hidden; }
}

.approval-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;

  button {
    padding: 8px 13px;
    border-radius: var(--radius-sm);
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .reject { color: var(--text-secondary); border: 1px solid var(--border-default); }
  .approve { color: #111; background: var(--primary-color); font-weight: 600; }
  button:disabled { opacity: .5; cursor: not-allowed; }
}
</style>
