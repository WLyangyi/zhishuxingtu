<template>
  <div class="login-container">
    <div class="login-left">
      <div class="brand-section">
        <div class="brand-logo">
          <svg viewBox="0 0 40 40" class="logo-svg">
            <circle cx="20" cy="8" r="3" class="logo-dot" />
            <circle cx="8" cy="20" r="3" class="logo-dot" />
            <circle cx="32" cy="20" r="3" class="logo-dot" />
            <circle cx="14" cy="32" r="3" class="logo-dot" />
            <circle cx="26" cy="32" r="3" class="logo-dot" />
            <line x1="20" y1="8" x2="8" y2="20" class="logo-line" />
            <line x1="20" y1="8" x2="32" y2="20" class="logo-line" />
            <line x1="8" y1="20" x2="14" y2="32" class="logo-line" />
            <line x1="32" y1="20" x2="26" y2="32" class="logo-line" />
            <line x1="14" y1="32" x2="26" y2="32" class="logo-line" />
            <circle cx="20" cy="20" r="4" class="logo-center" />
          </svg>
        </div>
        <h1 class="brand-title">知枢星图</h1>
        <p class="brand-tagline">连接知识，点亮思维</p>
      </div>

      <div class="features-section">
        <div class="feature-item">
          <div class="feature-icon">
            <Network :size="20" />
          </div>
          <div class="feature-text">
            <h4>知识图谱</h4>
            <p>可视化展示知识关联</p>
          </div>
        </div>
        <div class="feature-item">
          <div class="feature-icon">
            <Link :size="20" />
          </div>
          <div class="feature-text">
            <h4>双向链接</h4>
            <p>构建知识网络</p>
          </div>
        </div>
        <div class="feature-item">
          <div class="feature-icon">
            <Search :size="20" />
          </div>
          <div class="feature-text">
            <h4>智能搜索</h4>
            <p>快速定位内容</p>
          </div>
        </div>
      </div>
    </div>

    <div class="login-right">
      <div class="login-form-wrapper">
        <div class="form-header">
          <h2>{{ isRegister ? '创建账号' : '欢迎回来' }}</h2>
          <p>{{ isRegister ? '开始您的知识管理之旅' : '登录您的知枢星图账号' }}</p>
        </div>

        <form @submit.prevent="handleSubmit" class="login-form">
          <div class="form-group">
            <label for="username">用户名</label>
            <div class="input-wrapper">
              <User :size="18" class="input-icon" />
              <input
                v-model="username"
                type="text"
                id="username"
                placeholder="请输入用户名"
                required
                autocomplete="username"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="password">密码</label>
            <div class="input-wrapper">
              <Lock :size="18" class="input-icon" />
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                id="password"
                placeholder="请输入密码"
                required
                autocomplete="current-password"
              />
              <button type="button" class="toggle-btn" @click="showPassword = !showPassword">
                <Eye v-if="!showPassword" :size="18" />
                <EyeOff v-else :size="18" />
              </button>
            </div>
          </div>

          <div v-if="isRegister" class="form-group">
            <label for="confirmPassword">确认密码</label>
            <div class="input-wrapper">
              <Shield :size="18" class="input-icon" />
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                id="confirmPassword"
                placeholder="请再次输入密码"
                required
                autocomplete="new-password"
              />
              <button type="button" class="toggle-btn" @click="showConfirmPassword = !showConfirmPassword">
                <Eye v-if="!showConfirmPassword" :size="18" />
                <EyeOff v-else :size="18" />
              </button>
            </div>
          </div>

          <transition name="fade">
            <div v-if="error" class="error-message">
              <AlertCircle :size="16" />
              <span>{{ error }}</span>
            </div>
          </transition>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="!loading">{{ isRegister ? '创建账号' : '登录' }}</span>
            <span v-else class="loading-spinner"></span>
          </button>
        </form>

        <div class="form-footer">
          <p>
            {{ isRegister ? '已有账号？' : '还没有账号？' }}
            <button type="button" class="switch-btn" @click="switchMode">
              {{ isRegister ? '立即登录' : '立即注册' }}
            </button>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, Lock, Shield, Eye, EyeOff, AlertCircle, Network, Link, Search } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)

function switchMode() {
  isRegister.value = !isRegister.value
  error.value = ''
  confirmPassword.value = ''
}

async function handleSubmit() {
  error.value = ''
  
  if (isRegister.value) {
    if (password.value !== confirmPassword.value) {
      error.value = '两次输入的密码不一致'
      return
    }
    if (password.value.length < 6) {
      error.value = '密码长度至少6位'
      return
    }
    
    loading.value = true
    try {
      await authStore.register(username.value, password.value)
      await authStore.login(username.value, password.value)
      router.push('/')
    } catch (e: any) {
      error.value = e.response?.data?.detail || '注册失败'
    } finally {
      loading.value = false
    }
  } else {
    loading.value = true
    try {
      await authStore.login(username.value, password.value)
      router.push('/')
    } catch (e: any) {
      error.value = e.response?.data?.detail || '登录失败'
    } finally {
      loading.value = false
    }
  }
}
</script>

<style scoped lang="scss">
.login-container {
  min-height: 100vh;
  display: flex;
  background: var(--bg-primary);
}

.login-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: var(--bg-secondary);
  position: relative;
  
  @media (max-width: 900px) {
    display: none;
  }
}

.brand-section {
  text-align: center;
  margin-bottom: 60px;
}

.brand-logo {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
}

.logo-svg {
  width: 100%;
  height: 100%;
  
  .logo-dot {
    fill: var(--primary-color);
  }
  
  .logo-line {
    stroke: var(--primary-color);
    stroke-width: 1;
    opacity: 0.4;
  }
  
  .logo-center {
    fill: var(--accent-purple);
  }
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
  letter-spacing: 4px;
}

.brand-tagline {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
  letter-spacing: 2px;
}

.features-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 280px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);

  &:hover {
    border-color: var(--border-default);
    transform: translateX(4px);
  }
}

.feature-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-muted);
  border-radius: var(--radius-md);
  color: var(--primary-color);
}

.feature-text {
  h4 {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
    margin: 0 0 2px;
  }
  
  p {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
  }
}

.login-right {
  width: 480px;
  min-width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: var(--bg-primary);
  
  @media (max-width: 900px) {
    width: 100%;
    min-width: auto;
    padding: 40px 24px;
  }
}

.login-form-wrapper {
  width: 100%;
  max-width: 360px;
}

.form-header {
  margin-bottom: 32px;
  
  h2 {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px;
  }
  
  p {
    font-size: 14px;
    color: var(--text-muted);
    margin: 0;
  }
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  
  label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
  }
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:focus-within {
    border-color: var(--primary-color);
    background: var(--bg-tertiary);
  }
  
  .input-icon {
    color: var(--text-muted);
    flex-shrink: 0;
  }
  
  input {
    flex: 1;
    padding: 12px 0;
    background: transparent;
    border: none;
    font-size: 14px;
    color: var(--text-primary);
    
    &::placeholder {
      color: var(--text-muted);
    }
    
    &:focus {
      outline: none;
    }
  }
  
  .toggle-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: color var(--transition-fast);
    
    &:hover {
      color: var(--text-secondary);
    }
  }
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-md);
  color: #f87171;
  font-size: 13px;
}

.fade-enter-active, .fade-leave-active {
  transition: all 0.2s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 14px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
  margin-top: 8px;
  
  &:hover:not(:disabled) {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
  
  .loading-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(0, 0, 0, 0.2);
    border-top-color: #000;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  
  p {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }
  
  .switch-btn {
    background: none;
    border: none;
    color: var(--primary-color);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    padding: 0;
    margin-left: 4px;
    transition: color var(--transition-fast);
    
    &:hover {
      color: var(--primary-hover);
    }
  }
}
</style>
