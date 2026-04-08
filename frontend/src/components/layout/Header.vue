<template>
  <header class="header">
    <div class="header-left">
      <button @click="goHome" class="logo-btn">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" class="logo-svg">
            <circle cx="12" cy="5" r="2" />
            <circle cx="5" cy="12" r="2" />
            <circle cx="19" cy="12" r="2" />
            <circle cx="8" cy="19" r="2" />
            <circle cx="16" cy="19" r="2" />
            <line x1="12" y1="5" x2="5" y2="12" stroke-width="1" opacity="0.4" />
            <line x1="12" y1="5" x2="19" y2="12" stroke-width="1" opacity="0.4" />
            <line x1="5" y1="12" x2="8" y2="19" stroke-width="1" opacity="0.4" />
            <line x1="19" y1="12" x2="16" y2="19" stroke-width="1" opacity="0.4" />
            <circle cx="12" cy="12" r="2.5" />
          </svg>
        </div>
        <span class="logo-text">知枢星图</span>
      </button>
    </div>
    
    <div class="search-box">
      <Search :size="16" class="search-icon" />
      <input 
        v-model="searchQuery"
        type="text"
        placeholder="搜索笔记..."
        @keyup.enter="handleSearch"
        class="search-input"
      />
      <button @click="handleSearch" class="search-btn">
        搜索
      </button>
    </div>
    
    <div class="header-right">
      <button @click="goToGraph" class="icon-btn" title="知识图谱">
        <Network :size="20" />
      </button>
      <button @click="toggleTheme" class="icon-btn" :title="themeStore.isDark ? '浅色模式' : '深色模式'">
        <Sun v-if="themeStore.isDark" :size="20" />
        <Moon v-else :size="20" />
      </button>
      <div class="user-menu">
        <div class="user-avatar">
          {{ authStore.user?.username?.charAt(0).toUpperCase() }}
        </div>
        <span class="user-name">{{ authStore.user?.username }}</span>
        <button @click="handleLogout" class="logout-btn">
          <LogOut :size="16" />
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { Search, Network, Sun, Moon, LogOut } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const searchQuery = ref('')

function goHome() {
  router.push('/')
}

function handleSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } })
  }
}

function goToGraph() {
  router.push('/graph')
}

function toggleTheme() {
  themeStore.toggle()
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped lang="scss">
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }
}

.logo-icon {
  width: 28px;
  height: 28px;
}

.logo-svg {
  width: 100%;
  height: 100%;
  
  circle {
    fill: var(--primary-color);
  }
  
  circle:last-child {
    fill: var(--accent-purple);
  }
  
  line {
    stroke: var(--primary-color);
  }
}

.logo-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  max-width: 480px;
  margin: 0 24px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:focus-within {
    border-color: var(--border-default);
    background: var(--bg-tertiary);
  }
  
  .search-icon {
    color: var(--text-muted);
    flex-shrink: 0;
  }
  
  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    color: var(--text-primary);
    font-size: 14px;
    
    &:focus {
      outline: none;
    }
    
    &::placeholder {
      color: var(--text-muted);
    }
  }
  
  .search-btn {
    padding: 6px 14px;
    background: var(--primary-color);
    border: none;
    border-radius: var(--radius-sm);
    color: #000;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
    
    &:hover {
      background: var(--primary-hover);
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 6px 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.user-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  color: #000;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover {
    background: rgba(239, 68, 68, 0.1);
    color: var(--accent-red);
  }
}

@media (max-width: 768px) {
  .header {
    padding: 10px 16px;
  }
  
  .logo-text {
    display: none;
  }
  
  .search-box {
    margin: 0 16px;
    
    .search-btn {
      display: none;
    }
  }
  
  .user-name {
    display: none;
  }
}
</style>
