<template>
  <svg
    class="constellation-art"
    :viewBox="`0 0 ${width} ${height}`"
    :width="width"
    :height="height"
    role="img"
    :aria-label="ariaLabel"
  >
    <path
      v-for="(link, index) in linkPaths"
      :key="`link-${index}`"
      :d="link.d"
      pathLength="1"
      :class="['c-line', link.gold && 'c-line--gold', animate && 'c-line--draw']"
      :style="animate ? { animationDelay: `${index * 150}ms` } : undefined"
    />

    <g
      v-for="(point, index) in resolvedPoints"
      :key="`star-${index}`"
      :class="animate && 'c-star--in'"
      :style="animate ? { animationDelay: `${index * 90}ms` } : undefined"
    >
      <circle
        :cx="point.x"
        :cy="point.y"
        :r="point.r"
        :class="['c-star', point.gold && 'c-star--gold']"
      />
      <circle
        v-if="point.gold"
        :cx="point.x"
        :cy="point.y"
        :r="point.r + 3"
        class="c-halo"
      />
    </g>

    <text v-if="code" :x="width - 4" :y="height - 4" text-anchor="end" class="c-label">
      {{ code }}
    </text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface ConstellationPoint {
  x: number
  y: number
  r: number
  gold?: boolean
}

const PRESETS: Record<string, { points: ConstellationPoint[]; links: Array<[number, number]> }> = {
  hero: {
    points: [
      { x: 34, y: 168, r: 2.4, gold: true },
      { x: 86, y: 104, r: 1.6 },
      { x: 148, y: 126, r: 2.2 },
      { x: 194, y: 62, r: 1.6 },
      { x: 252, y: 90, r: 2.8, gold: true },
      { x: 296, y: 34, r: 1.5 },
      { x: 218, y: 170, r: 1.8 }
    ],
    links: [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5],
      [2, 6],
      [6, 4]
    ]
  },
  login: {
    points: [
      { x: 26, y: 62, r: 1.8 },
      { x: 82, y: 34, r: 2.6, gold: true },
      { x: 138, y: 74, r: 1.6 },
      { x: 196, y: 42, r: 2.2 },
      { x: 250, y: 82, r: 1.5 },
      { x: 296, y: 50, r: 2, gold: true }
    ],
    links: [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5]
    ]
  },
  mini: {
    points: [
      { x: 20, y: 46, r: 1.6 },
      { x: 58, y: 22, r: 2.2, gold: true },
      { x: 96, y: 52, r: 1.4 },
      { x: 134, y: 28, r: 2 },
      { x: 164, y: 62, r: 1.4 }
    ],
    links: [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4]
    ]
  }
}

const props = withDefaults(
  defineProps<{
    variant?: keyof typeof PRESETS
    points?: ConstellationPoint[]
    links?: Array<[number, number]>
    width?: number
    height?: number
    code?: string
    animate?: boolean
    ariaLabel?: string
  }>(),
  {
    variant: 'hero',
    points: undefined,
    links: undefined,
    width: 320,
    height: 200,
    code: 'ZS·128',
    animate: true,
    ariaLabel: '星座插画'
  }
)

const resolvedPoints = computed(() => props.points ?? PRESETS[props.variant].points)
const resolvedLinks = computed(() => props.links ?? PRESETS[props.variant].links)

const linkPaths = computed(() =>
  resolvedLinks.value.map(([from, to], index) => {
    const a = resolvedPoints.value[from]
    const b = resolvedPoints.value[to]
    return {
      d: `M ${a.x} ${a.y} L ${b.x} ${b.y}`,
      gold: index < 2 || (a.gold && b.gold)
    }
  })
)
</script>

<style scoped>
.constellation-art {
  overflow: visible;
}

.c-halo {
  fill: none;
  stroke: var(--gold);
  stroke-width: 0.6;
  opacity: 0.28;
}

.c-line--draw {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: constellation-draw 1.4s var(--ease-out) forwards;
}

.c-star--in {
  transform-box: fill-box;
  transform-origin: center;
  animation: constellation-star-in 500ms var(--ease-out) both;
}

@keyframes constellation-draw {
  to {
    stroke-dashoffset: 0;
  }
}

@keyframes constellation-star-in {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
