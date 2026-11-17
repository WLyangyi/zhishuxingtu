<template>
  <div class="code-block">
    <header v-if="language || copyable" class="code-block__bar">
      <span class="readout">{{ language || 'CODE' }}</span>
      <button v-if="copyable" type="button" class="code-block__copy" @click="copy">
        {{ copied ? '已复制' : '复制' }}
      </button>
    </header>
    <pre class="code-block__pre"><code><template v-for="token in tokens" :key="token.id"><span :class="{ 'code-block__var': token.isVar }">{{ token.text }}</span></template></code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

const props = withDefaults(
  defineProps<{ code: string; language?: string; copyable?: boolean }>(),
  { language: '', copyable: true }
)

const copied = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

const tokens = computed(() =>
  props.code
    .split(/(\{\{[^}]+\}\})/g)
    .filter((text) => text.length > 0)
    .map((text, index) => ({ id: index, text, isVar: /^\{\{[^}]+\}\}$/.test(text) }))
)

async function copy() {
  try {
    await navigator.clipboard?.writeText(props.code)
    copied.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch {
    copied.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<style scoped>
.code-block {
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--bg);
  overflow: hidden;
}

.code-block__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
}

.code-block__copy {
  font-size: 11px;
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.code-block__copy:hover {
  color: var(--gold);
}

.code-block__pre {
  margin: 0;
  padding: 12px 14px;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.75;
  color: var(--t2);
}

.code-block__var {
  color: var(--gold);
}
</style>
