<template>
  <div ref="root" class="star-field" aria-hidden="true">
    <canvas
      v-for="layer in layers"
      :key="layer.name"
      ref="canvasEls"
      class="star-field__layer"
      :class="`star-field__layer--${layer.name}`"
    />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

type LayerName = 'far' | 'mid' | 'near'

interface Star {
  x: number
  y: number
  r: number
  phase: number
  speed: number
  base: number
}

const props = withDefaults(
  defineProps<{
    density?: number
    parallax?: boolean
    static?: boolean
  }>(),
  { density: 90, parallax: true, static: false }
)

const layers: Array<{ name: LayerName; weight: number; radius: number; factor: number }> = [
  { name: 'far', weight: 0.45, radius: 1, factor: 6 },
  { name: 'mid', weight: 0.35, radius: 1.4, factor: 12 },
  { name: 'near', weight: 0.2, radius: 2, factor: 22 }
]

const root = ref<HTMLElement | null>(null)
const canvasEls = ref<HTMLCanvasElement[]>([])

let frame = 0
let disposed = false
let starColor = 'rgba(234,232,226,.85)'
let resizeObserver: ResizeObserver | null = null

const starSets: Star[][] = []
const offsets = { x: 0, y: 0, tx: 0, ty: 0 }

function buildStars(count: number): Star[] {
  return Array.from({ length: count }, () => ({
    x: Math.random(),
    y: Math.random(),
    r: 0,
    phase: Math.random() * Math.PI * 2,
    speed: 0.00018 + Math.random() * 0.00035,
    base: 0.25 + Math.random() * 0.55
  }))
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false
}

function resize() {
  const host = root.value
  if (!host) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const width = host.clientWidth
  const height = host.clientHeight
  if (!width || !height) return

  canvasEls.value.forEach((canvas, index) => {
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    const layer = layers[index]
    const stars = starSets[index]
    stars.forEach((star) => {
      star.r = layer.radius * (0.75 + Math.random() * 0.5)
    })
  })
}

function draw(timestamp: number) {
  if (disposed) return
  const host = root.value
  if (!host) return

  const width = host.clientWidth
  const height = host.clientHeight
  const reduced = props.static || prefersReducedMotion()

  canvasEls.value.forEach((canvas, index) => {
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = starColor

    const layer = layers[index]
    const drift = props.parallax && !reduced ? offsets : { x: 0, y: 0 }

    starSets[index].forEach((star) => {
      const alpha = reduced
        ? star.base
        : star.base + Math.sin(timestamp * star.speed + star.phase) * 0.28
      ctx.globalAlpha = Math.max(0.08, Math.min(1, alpha))
      ctx.beginPath()
      ctx.arc(
        star.x * width + drift.x * (layer.factor / 22),
        star.y * height + drift.y * (layer.factor / 22),
        star.r,
        0,
        Math.PI * 2
      )
      ctx.fill()
    })
  })
  ctxAlphaReset()
}

function ctxAlphaReset() {
  canvasEls.value.forEach((canvas) => {
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.globalAlpha = 1
  })
}

function loop(timestamp: number) {
  if (disposed) return
  offsets.x += (offsets.tx - offsets.x) * 0.045
  offsets.y += (offsets.ty - offsets.y) * 0.045
  canvasEls.value.forEach((canvas, index) => {
    if (!props.parallax) return
    canvas.style.transform = `translate3d(${offsets.x * (layers[index].factor / 22)}px, ${
      offsets.y * (layers[index].factor / 22)
    }px, 0)`
  })
  draw(timestamp)
  frame = requestAnimationFrame(loop)
}

function onPointerMove(event: PointerEvent) {
  if (!props.parallax || props.static || prefersReducedMotion()) return
  offsets.tx = (event.clientX / window.innerWidth - 0.5) * 22
  offsets.ty = (event.clientY / window.innerHeight - 0.5) * 22
}

onMounted(() => {
  starColor =
    getComputedStyle(document.documentElement).getPropertyValue('--star').trim() ||
    'rgba(234,232,226,.85)'

  const total = Math.max(12, props.density)
  layers.forEach((layer, index) => {
    starSets[index] = buildStars(Math.round(total * layer.weight))
  })

  resize()
  draw(0)

  if (props.static || prefersReducedMotion()) return

  if (typeof ResizeObserver !== 'undefined' && root.value) {
    resizeObserver = new ResizeObserver(() => resize())
    resizeObserver.observe(root.value)
  }

  window.addEventListener('pointermove', onPointerMove, { passive: true })
  frame = requestAnimationFrame(loop)
})

onBeforeUnmount(() => {
  disposed = true
  cancelAnimationFrame(frame)
  window.removeEventListener('pointermove', onPointerMove)
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.star-field {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.star-field__layer {
  position: absolute;
  inset: 0;
  will-change: transform;
}
</style>
