<template>
  <nav class="breadcrumb" aria-label="面包屑">
    <template v-for="(item, index) in items" :key="`${item.label}-${index}`">
      <RouterLink v-if="item.to && index < items.length - 1" :to="item.to" class="breadcrumb__link">
        {{ item.label }}
      </RouterLink>
      <span v-else class="breadcrumb__current" :aria-current="index === items.length - 1 ? 'page' : undefined">
        {{ item.label }}
      </span>
      <span v-if="index < items.length - 1" class="breadcrumb__sep" aria-hidden="true">/</span>
    </template>
  </nav>
</template>

<script setup lang="ts">
defineProps<{ items: Array<{ label: string; to?: string }> }>()
</script>

<style scoped>
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  min-width: 0;
}

.breadcrumb__link {
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.breadcrumb__link:hover {
  color: var(--gold);
}

.breadcrumb__current {
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumb__sep {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--t3);
}
</style>
