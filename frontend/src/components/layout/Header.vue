<template>
  <header class="header">
    <div class="header-left">
      <button @click="goHome" class="home-btn" title="返回主页">
        <span class="logo-icon">🌟</span>
        <span class="logo-text">知枢星图</span>
      </button>
    </div>
    
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input 
        v-model="searchQuery"
        type="text"
        placeholder="搜索笔记或输入问题..."
        @keyup.enter="handleSearch"
        class="search-input"
      />
      <button @click="handleSearch" class="search-btn">
        <span>搜索</span>
        <span class="shortcut">⌘K</span>
      </button>
    </div>
    
    <div class="header-actions">
      <button @click="goToGraph" class="action-btn" title="知识图谱">
        <span>🌐</span>
      </button>
      <button @click="toggleTheme" class="action-btn theme-btn" :title="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'">
        <span v-if="themeStore.isDark">🌙</span>
        <span v-else>☀️</span>
      </button>
      <div class="user-menu">
        <div class="user-avatar">
          {{ authStore.user?.username?.charAt(0).toUpperCase() }}
        </div>
        <span class="user-name">{{ authStore.user?.username }}</span>
        <button @click="handleLogout" class="logout-btn">
          <span>登出</span>
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
  padding: 12px 24px;
  background: linear-gradient(180deg, rgba(18, 18, 31, 0.95) 0%, rgba(13, 13, 26, 0.95) 100%);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  backdrop-filter: blur(10px);
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, 
      transparent 0%, 
      rgba(0, 212, 255, 0.3) 50%, 
      transparent 100%
    );
  }
}

.header-left {
  display: flex;
  align-items: center;
}

.home-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.2);
    
    .logo-icon {
      transform: rotate(180deg) scale(1.1);
    }
    
    .logo-text {
      color: #00d4ff;
    }
  }
  
  .logo-icon {
    font-size: 22px;
    transition: transform 0.5s ease;
  }
  
  .logo-text {
    font-size: 16px;
    font-weight: 600;
    background: linear-gradient(135deg, #00d4ff, #7b2cbf);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    transition: all 0.3s;
  }
}

.search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  max-width: 600px;
  margin: 0 24px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  padding: 4px 4px 4px 16px;
  transition: all 0.3s;
  
  &:focus-within {
    border-color: rgba(0, 212, 255, 0.4);
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
  }
  
  .search-icon {
    font-size: 16px;
    opacity: 0.5;
  }
  
  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    color: #fff;
    font-size: 14px;
    padding: 8px 0;
    
    &:focus {
      outline: none;
    }
    
    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }
  }
  
  .search-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }
    
    .shortcut {
      font-size: 11px;
      opacity: 0.7;
      padding: 2px 6px;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 4px;
    }
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.action-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 10px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.3);
    transform: translateY(-2px);
  }
}

:global(body.light) .action-btn {
  background: rgba(255, 255, 255, 0.6);
  border-color: rgba(8, 145, 178, 0.2);
  
  &:hover {
    background: rgba(8, 145, 178, 0.1);
    border-color: rgba(8, 145, 178, 0.4);
  }
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 4px 4px 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: white;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
}

.logout-btn {
  padding: 8px 14px;
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  cursor: pointer;
  color: rgba(239, 68, 68, 0.8);
  font-size: 13px;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.5);
    color: #ef4444;
  }
}

@media (max-width: 768px) {
  .header {
    padding: 12px 16px;
  }
  
  .logo-text {
    display: none;
  }
  
  .search-box {
    margin: 0 12px;
    
    .search-btn {
      padding: 8px 12px;
      
      .shortcut {
        display: none;
      }
    }
  }
  
  .user-name {
    display: none;
  }
}
</style>
