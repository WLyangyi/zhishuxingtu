<template>
  <div class="home-page">
    <div class="stars-bg">
      <div v-for="n in 50" :key="n" class="star" :style="getStarStyle(n)"></div>
    </div>

    <div class="category-entries">
      <div
        v-for="(category, index) in categories"
        :key="category.id"
        class="category-card"
        :class="'card-' + (index + 1)"
        :style="{
          '--card-color': category.color,
          '--card-image': `url(https://picsum.photos/seed/${category.id}/600/800)`
        }"
        @click="enterCategory(category)"
      >
        <div class="card-image-bg"></div>
        <div class="card-overlay"></div>
        <div class="card-content">
          <div class="card-icon">
            <component :is="getCategoryIcon(category.name)" />
          </div>
          <h2 class="card-title">{{ category.name }}</h2>
          <p class="card-desc">{{ getCategoryDesc(category.name) }}</p>
          <div class="card-meta">
            <span class="meta-item">
              <component :is="getIcon('folder')" />
              {{ getFolderCount(category.id) }} 文件夹
            </span>
            <span class="meta-item">
              <component :is="getIcon('file')" />
              {{ getContentCount(category.id) }} 内容
            </span>
          </div>
        </div>
        <div class="card-arrow">
          <component :is="getIcon('arrow')" />
        </div>
      </div>
    </div>

    <div class="quick-access">
      <div class="quick-header">
        <h3>快捷入口</h3>
      </div>
      <div class="quick-grid">
        <div class="quick-item" @click="goToSearch">
          <div class="quick-icon">
            <component :is="getIcon('search')" />
          </div>
          <span>智能检索</span>
        </div>
        <div class="quick-item" @click="goToGraph">
          <div class="quick-icon">
            <component :is="getIcon('graph')" />
          </div>
          <span>知识图谱</span>
        </div>
        <div class="quick-item" @click="goToSkills">
          <div class="quick-icon">
            <component :is="getIcon('skill')" />
          </div>
          <span>智能模块</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { useFoldersStore } from '@/stores/folders'

const router = useRouter()
const categoryStore = useCategoryStore()
const foldersStore = useFoldersStore()

const categories = computed(() => categoryStore.categories)

const icons = {
  folder: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'currentColor' }, [
    h('path', { d: 'M19.5 21a3 3 0 0 0 3-3v-4.5a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3V18a3 3 0 0 0 3 3h15zM1.5 10.146V6a3 3 0 0 1 3-3h5.379a2.25 2.25 0 0 1 1.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 0 1 3 3v1.146A4.483 4.483 0 0 0 19.5 9h-15a4.483 4.483 0 0 0-3 1.146z' })
  ]),
  file: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', { d: 'M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z' }),
    h('polyline', { points: '14 2 14 8 20 8' })
  ]),
  search: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('circle', { cx: '11', cy: '11', r: '8' }),
    h('path', { d: 'm21 21-4.3-4.3' })
  ]),
  graph: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('circle', { cx: '12', cy: '12', r: '3' }),
    h('circle', { cx: '19', cy: '5', r: '2' }),
    h('circle', { cx: '5', cy: '19', r: '2' }),
    h('path', { d: 'M10.4 10.5 5 5' }),
    h('path', { d: 'M13.6 13.5 19 19' }),
    h('path', { d: 'M5 17v-3' }),
    h('path', { d: 'M19 7V5' })
  ]),
  skill: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', { d: 'M13 2 3 14h9l-1 8 10-12h-9l1-8z' })
  ]),
  arrow: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', { d: 'M5 12h14' }),
    h('path', { d: 'm12 5 7 7-7 7' })
  ]),
  user: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('circle', { cx: '12', cy: '8', r: '5' }),
    h('path', { d: 'M20 21a8 8 0 0 0-16 0' })
  ]),
  briefcase: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('rect', { width: '20', height: '14', x: '2', y: '7', rx: '2', ry: '2' }),
    h('path', { d: 'M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16' })
  ]),
  assets: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', { d: 'm21 8-9 9-4-4-3 3' }),
    h('rect', { width: '6', height: '6', x: '15', y: '3', rx: '1' })
  ])
}

function getIcon(name: string) {
  return icons[name as keyof typeof icons] || icons.file
}

function getCategoryIcon(name: string) {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return icons.user
  if (nameLower.includes('工作')) return icons.briefcase
  if (nameLower.includes('素材')) return icons.assets
  return icons.file
}

function getCategoryDesc(name: string): string {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return '笔记、日记、灵感收集'
  if (nameLower.includes('工作')) return '项目文档、任务管理'
  if (nameLower.includes('素材')) return '图片、链接、附件'
  return '内容管理'
}

function getFolderCount(categoryId: string): number {
  return foldersStore.folders.filter(f => f.category_id === categoryId).length
}

function getContentCount(categoryId: string): number {
  return categoryStore.contents.filter(c => c.category_id === categoryId).length
}

function getStarStyle(_n: number) {
  return {
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    animationDelay: `${Math.random() * 3}s`
  }
}

function enterCategory(category: any) {
  categoryStore.currentCategory = category
  router.push(`/categories/${category.id}`)
}

function goToSearch() {
  router.push('/search')
}

function goToGraph() {
  router.push('/graph')
}

function goToSkills() {
  router.push('/skills')
}

onMounted(async () => {
  await categoryStore.fetchCategories()
  await foldersStore.fetchFolders()
  await categoryStore.fetchContents()
})
</script>

<style scoped lang="scss">
.home-page {
  padding: 24px;
  min-height: 100%;
  min-height: 100dvh;
  max-width: 1400px;
  margin: 0 auto;
  position: relative;
  overflow: hidden;
}

.stars-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.star {
  position: absolute;
  width: 2px;
  height: 2px;
  background: white;
  border-radius: 50%;
  animation: twinkle 3s infinite ease-in-out;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.category-entries {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.8fr;
  gap: 20px;
  margin-bottom: 32px;
  position: relative;
  z-index: 1;
}

.category-card {
  position: relative;
  height: 360px;
  border-radius: 24px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: translateY(-8px);

    .card-arrow {
      opacity: 1;
      transform: translateX(0);
    }

    .card-image-bg {
      transform: scale(1.05);
    }
  }

  &:nth-child(1) {
    grid-row: span 1;
  }

  &:nth-child(2) {
    height: 400px;
    margin-top: -20px;
  }

  &:nth-child(3) {
    height: 340px;
    margin-top: 10px;
  }
}

.card-image-bg {
  position: absolute;
  inset: 0;
  background-image: var(--card-image);
  background-size: cover;
  background-position: center;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.1) 0%,
    rgba(0, 0, 0, 0.6) 50%,
    rgba(0, 0, 0, 0.9) 100%
  );
}

.card-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 28px;
  z-index: 1;
}

.card-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  margin-bottom: 16px;
  color: var(--card-color);
  transition: transform 0.3s;

  svg {
    width: 28px;
    height: 28px;
  }

  .category-card:hover & {
    transform: scale(1.1);
  }
}

.card-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}

.card-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 16px;
}

.card-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);

  svg {
    width: 14px;
    height: 14px;
  }
}

.card-arrow {
  position: absolute;
  top: 28px;
  right: 28px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  color: #fff;
  opacity: 0;
  transform: translateX(-10px);
  transition: all 0.3s;

  svg {
    width: 20px;
    height: 20px;
  }
}

.quick-access {
  background: rgba(18, 18, 31, 0.6);
  border-radius: 20px;
  padding: 24px;
  border: 1px solid rgba(0, 212, 255, 0.1);
  position: relative;
  z-index: 1;
}

.quick-header {
  margin-bottom: 20px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
  }
}

.quick-grid {
  display: flex;
  gap: 16px;
}

.quick-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    background: rgba(0, 212, 255, 0.08);
    border-color: rgba(0, 212, 255, 0.2);
    transform: translateY(-2px);

    .quick-icon {
      background: rgba(0, 212, 255, 0.2);
      color: #00d4ff;
    }
  }

  span {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.7);
  }
}

.quick-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.6);
  transition: all 0.3s;

  svg {
    width: 20px;
    height: 20px;
  }
}

@media (max-width: 1024px) {
  .category-entries {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .category-card {
    height: 240px !important;
    margin-top: 0 !important;
  }
}

@media (max-width: 768px) {
  .home-page {
    padding: 16px;
  }

  .quick-grid {
    flex-direction: column;
  }
}
</style>
