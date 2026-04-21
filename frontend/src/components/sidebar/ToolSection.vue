<template>
  <div class="sidebar-section tools-section">
    <div class="section-header">
      <h3>工具</h3>
    </div>
    <div class="tool-list">
      <div
        class="tool-item"
        :class="{ active: isCurrentRoute('/personal/search') }"
        @click="goToSearch"
      >
        <Search :size="16" />
        <span>智能检索</span>
      </div>
      <div
        class="tool-item"
        :class="{ active: isCurrentRoute('/graph') || isCurrentRoute('/personal/graph') }"
        @click="goToGraph"
      >
        <GitBranch :size="16" />
        <span>知识图谱</span>
      </div>
      <div
        class="tool-item ai-tool"
        :class="{ active: isCurrentRoute('/personal/ai') }"
        @click="goToAI"
      >
        <Bot :size="16" />
        <span>AI 助手</span>
      </div>
      <div
        class="tool-item"
        :class="{ active: isCurrentRoute('/prompt-lab') }"
        @click="goToPromptLab"
      >
        <Microscope :size="16" />
        <span>提示词实验室</span>
      </div>
      <div
        class="tool-item import-tool"
        @click="openImport"
      >
        <Download :size="16" />
        <span>智能导入</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useImportStore } from '@/stores/import'
import { Search, GitBranch, Bot, Microscope, Download } from 'lucide-vue-next'

const router = useRouter()
const importStore = useImportStore()

function isCurrentRoute(path: string): boolean {
  return router.currentRoute.value.path === path
}

function goToGraph() {
  router.push('/graph')
}

function goToSearch() {
  router.push('/personal/search')
}

function goToAI() {
  router.push('/personal/ai')
}

function goToPromptLab() {
  router.push('/prompt-lab')
}

function openImport() {
  importStore.openImportModal()
}
</script>

<style scoped lang="scss">
.sidebar-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  h3 {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: var(--bg-active);
    color: var(--text-primary);
  }

  &.ai-tool {
    color: var(--primary-color);

    &:hover {
      background: var(--primary-muted);
    }

    &.active {
      background: var(--primary-muted);
      font-weight: 500;
    }
  }

  &.import-tool {
    color: var(--accent-purple);

    &:hover {
      background: rgba(139, 92, 246, 0.1);
    }
  }
}
</style>
