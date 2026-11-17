<template>
  <article class="message" :class="`message--${role}`">
    <header v-if="name || time" class="message__meta">
      <span v-if="name" class="readout message__name">{{ name }}</span>
      <span v-if="time" class="readout message__time">{{ time }}</span>
    </header>
    <div class="message__body">
      <slot />
      <span v-if="streaming" class="message__cursor" aria-hidden="true" />
    </div>
  </article>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    role?: 'user' | 'assistant' | 'system'
    name?: string
    time?: string
    streaming?: boolean
  }>(),
  { role: 'assistant', name: '', time: '', streaming: false }
)
</script>

<style scoped>
.message {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.message__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message__name {
  color: var(--t2);
}

.message__time {
  color: var(--t3);
}

.message__body {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text);
  word-break: break-word;
}

/* 用户消息：右侧浅面板 */
.message--user {
  align-items: flex-end;
}

.message--user .message__meta {
  flex-direction: row-reverse;
}

.message--user .message__body {
  max-width: 82%;
  padding: 10px 14px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  color: var(--t2);
}

/* AI 消息：无气泡直接排版 */
.message--assistant .message__body {
  max-width: 700px;
}

.message--system {
  align-items: center;
}

.message--system .message__body {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  color: var(--t3);
}

.message__cursor {
  display: inline-block;
  width: 7px;
  height: 14px;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--gold);
  animation: message-cursor 1s steps(2, start) infinite;
}

@keyframes message-cursor {
  50% {
    opacity: 0;
  }
}
</style>
