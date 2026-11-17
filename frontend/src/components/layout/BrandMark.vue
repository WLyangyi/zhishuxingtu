<template>
  <svg class="brand-mark" viewBox="0 0 28 28" fill="none" aria-hidden="true">
    <circle cx="14" cy="5" r="1.7" class="brand-mark__star" />
    <circle cx="5.5" cy="14" r="1.4" class="brand-mark__star" />
    <circle cx="22.5" cy="13" r="1.4" class="brand-mark__star" />
    <circle cx="9" cy="22.5" r="1.4" class="brand-mark__star" />
    <circle cx="19.5" cy="21.5" r="1.4" class="brand-mark__star" />
    <path d="M14 5 L5.5 14 L9 22.5 M14 5 L22.5 13 L19.5 21.5 M5.5 14 L22.5 13" class="brand-mark__line" />
    <circle cx="14" cy="14" r="2" class="brand-mark__core" />
  </svg>
</template>

<style scoped>
.brand-mark {
  width: 100%;
  height: 100%;
}

.brand-mark__star {
  fill: var(--gold);
}

.brand-mark__line {
  stroke: var(--gold);
  stroke-width: 0.9;
  opacity: 0.55;
}

.brand-mark__core {
  fill: none;
  stroke: var(--gold);
  stroke-width: 1;
}
</style>
