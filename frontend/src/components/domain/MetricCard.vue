<template>
  <div class="metric">
    <span class="readout metric__label">{{ label }}</span>

    <Skeleton v-if="loading" width="72%" :height="28" />
    <div v-else class="metric__value-row">
      <span class="num metric__value">{{ displayValue }}</span>
      <span v-if="unit" class="metric__unit">{{ unit }}</span>
    </div>

    <span
      v-if="!loading && trend !== undefined"
      class="metric__trend"
      :class="trend >= 0 ? 'metric__trend--up' : 'metric__trend--down'"
    >
      {{ trend >= 0 ? '+' : '' }}{{ trend }}%<span v-if="trendLabel"> · {{ trendLabel }}</span>
    </span>
    <span v-else-if="!loading && note" class="metric__note">{{ note }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    unit?: string
    trend?: number
    trendLabel?: string
    note?: string
    loading?: boolean
  }>(),
  { unit: '', trend: undefined, trendLabel: '', note: '', loading: false }
)

const displayValue = computed(() => {
  if (typeof props.value === 'number') return props.value.toLocaleString('zh-CN')
  return props.value
})
</script>

<style scoped>
.metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.metric__label {
  color: var(--t3);
}

.metric__value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.metric__value {
  font-family: var(--font-mono);
  font-size: 26px;
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--text);
}

.metric__unit {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--t3);
}

.metric__trend {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
}

.metric__trend--up {
  color: var(--gold);
}

.metric__trend--down {
  color: var(--danger);
}

.metric__note {
  font-size: 11px;
  color: var(--t3);
}
</style>
