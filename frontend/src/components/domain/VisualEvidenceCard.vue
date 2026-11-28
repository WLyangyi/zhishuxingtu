<script setup lang="ts">
import type { VisualEvidence } from '@/api/agent'

const props = defineProps<{ evidence: VisualEvidence }>()
const emit = defineEmits<{ view: [evidence: VisualEvidence] }>()
</script>

<template>
  <article class="visual-evidence-card">
    <header class="visual-evidence-card__head">
      <span class="visual-evidence-card__label">原图证据</span>
      <span class="visual-evidence-card__page">第 {{ props.evidence.page_number }} 页</span>
    </header>
    <p class="visual-evidence-card__source">{{ props.evidence.source_filename || props.evidence.note_id }}</p>
    <p v-if="props.evidence.description" class="visual-evidence-card__description">
      {{ props.evidence.description }}
    </p>
    <p v-else class="visual-evidence-card__description">视觉描述不可用</p>
    <button type="button" class="visual-evidence-card__view" @click="emit('view', props.evidence)">
      查看原图
    </button>
  </article>
</template>

<style scoped>
.visual-evidence-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-4);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
}

.visual-evidence-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
}

.visual-evidence-card__label {
  color: var(--gold-deep);
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
}

.visual-evidence-card__page,
.visual-evidence-card__source {
  color: var(--t2);
  font-size: var(--fs-micro);
}

.visual-evidence-card__description {
  color: var(--t1);
  font-size: var(--fs-small);
  line-height: 1.7;
}

.visual-evidence-card__view {
  align-self: flex-start;
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  background: var(--gold-soft);
  color: var(--gold-deep);
  cursor: pointer;
}
</style>
