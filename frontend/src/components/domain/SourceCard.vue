<script setup lang="ts">
import { computed } from 'vue'
import type { WebSource } from '@/api/agent'

const props = withDefaults(
  defineProps<{
    source: WebSource
    state?: 'loading' | 'empty' | 'error' | 'normal'
    errorMessage?: string
    saved?: boolean
  }>(),
  { state: 'normal', errorMessage: '', saved: false }
)
const emit = defineEmits<{ save: [source: WebSource] }>()

const domain = computed(() => {
  try {
    return new URL(props.source.url).hostname
  } catch {
    return props.source.url
  }
})

const title = computed(() => props.source.title.trim() || props.source.url)
const safeHref = computed(() => {
  try {
    const url = new URL(props.source.url)
    return url.hostname && (url.protocol === 'http:' || url.protocol === 'https:')
      ? props.source.url
      : ''
  } catch {
    return ''
  }
})
</script>

<template>
  <div v-if="state === 'loading'" class="source-card source-card--state" role="status">
    正在加载来源
  </div>
  <div v-else-if="state === 'empty'" class="source-card source-card--state">
    暂无来源
  </div>
  <div v-else-if="state === 'error'" class="source-card source-card--state source-card--error" role="alert">
    {{ errorMessage || '来源加载失败，请重试' }}
  </div>
  <article v-else class="source-card" :data-source-id="source.source_id">
    <header class="source-card__header">
      <span class="source-card__ordinal">[{{ source.ordinal }}]</span>
      <span class="source-card__site">{{ source.site_name || domain }}</span>
    </header>

    <h3 class="source-card__title">
      <a
        v-if="safeHref"
        class="source-card__title source-card__title-link"
        :href="safeHref"
        target="_blank"
        rel="noopener noreferrer"
      >{{ title }}</a>
      <span v-else class="source-card__title">{{ title }}</span>
    </h3>
    <p class="source-card__domain">{{ domain }}</p>

    <div class="source-card__times">
      <span>检索：{{ source.retrieved_at || '未知' }}</span>
      <span>抓取：{{ source.fetched_at || '未知' }}</span>
    </div>

    <p v-if="source.content_state === 'fetch_failed'" class="source-card__notice source-card__notice--danger">
      正文抓取失败，当前为搜索摘要
    </p>
    <p v-else-if="source.content_state === 'summary'" class="source-card__notice">
      仅搜索摘要
    </p>
    <p v-if="source.truncated" class="source-card__notice">正文已截断</p>
    <p v-if="source.content_state === 'fetched' && !source.artifact_id" class="source-card__notice">
      正文快照不可用
    </p>
    <p class="source-card__excerpt">{{ source.excerpt }}</p>

    <button type="button" class="source-card__save" :disabled="saved" @click="emit('save', source)">
      {{ saved ? '已存入' : '存入知识库' }}
    </button>
  </article>
</template>

<style scoped>
.source-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-4);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}

.source-card--state {
  color: var(--t2);
  font-size: var(--fs-body-s);
}

.source-card--error {
  color: var(--danger);
  background: var(--danger-soft);
  border-color: var(--danger-line);
}

.source-card--highlighted {
  border-color: var(--gold);
  box-shadow: 0 0 0 2px var(--gold-soft);
}

.source-card__header {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-micro);
}

.source-card__ordinal {
  color: var(--gold-deep);
  font-family: var(--font-mono);
}

.source-card__site,
.source-card__domain,
.source-card__times {
  color: var(--t3);
}

.source-card__title {
  color: var(--text);
  font-size: var(--fs-body);
  font-weight: 600;
}

.source-card__title-link {
  text-decoration: none;
}

.source-card__title-link:hover {
  color: var(--gold-deep);
}

.source-card__title-link:focus-visible {
  outline: 1px solid var(--gold);
  outline-offset: var(--sp-1);
}

.source-card__domain,
.source-card__times {
  font-size: var(--fs-micro);
}

.source-card__times {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-3);
  font-family: var(--font-mono);
}

.source-card__notice {
  font-size: var(--fs-micro);
}

.source-card__notice--danger {
  color: var(--danger);
}

.source-card__excerpt {
  color: var(--t2);
  font-size: var(--fs-body-s);
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.source-card__save {
  align-self: flex-start;
  margin-top: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  color: var(--gold-deep);
  background: var(--gold-soft);
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
  cursor: pointer;
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.source-card__save:hover {
  color: var(--gold-ink);
  background: var(--gold-deep);
}

.source-card__save:focus-visible {
  outline: 1px solid var(--gold);
  outline-offset: var(--sp-1);
}
</style>
