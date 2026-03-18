<template>
  <div class="login-container">
    <div class="login-left">
      <div class="stars-bg">
        <div v-for="n in 50" :key="n" class="star" :style="getStarStyle(n)"></div>
      </div>
      <div class="floating-orbs">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
      </div>
      <div class="brand-content">
        <div class="logo-wrapper">
          <div class="logo-icon">
            <svg viewBox="0 0 100 100" class="constellation-svg">
              <circle cx="50" cy="20" r="4" class="star-point" />
              <circle cx="20" cy="50" r="4" class="star-point" />
              <circle cx="80" cy="50" r="4" class="star-point" />
              <circle cx="35" cy="80" r="4" class="star-point" />
              <circle cx="65" cy="80" r="4" class="star-point" />
              <line x1="50" y1="20" x2="20" y2="50" class="star-line" />
              <line x1="50" y1="20" x2="80" y2="50" class="star-line" />
              <line x1="20" y1="50" x2="35" y2="80" class="star-line" />
              <line x1="80" y1="50" x2="65" y2="80" class="star-line" />
              <line x1="35" y1="80" x2="65" y2="80" class="star-line" />
              <circle cx="50" cy="50" r="6" class="center-point" />
            </svg>
          </div>
        </div>
        <h1 class="brand-title">知枢星图</h1>
        <p class="brand-tagline">连接知识，点亮思维</p>
        <div class="features-list">
          <div class="feature-item">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span>知识图谱可视化</span>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <span>智能笔记管理</span>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
            </div>
            <span>全文智能搜索</span>
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
          <div class="input-group" :class="{ focused: focusedField === 'username', filled: username }">
            <div class="input-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <input
              v-model="username"
              type="text"
              id="username"
              @focus="focusedField = 'username'"
              @blur="focusedField = ''"
              required
              autocomplete="username"
            />
            <label for="username">用户名</label>
            <div class="input-line"></div>
          </div>

          <div class="input-group" :class="{ focused: focusedField === 'password', filled: password }">
            <div class="input-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              id="password"
              @focus="focusedField = 'password'"
              @blur="focusedField = ''"
              required
              autocomplete="current-password"
            />
            <label for="password">密码</label>
            <div class="input-line"></div>
            <button type="button" class="toggle-password" @click="showPassword = !showPassword">
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>

          <div v-if="isRegister" class="input-group" :class="{ focused: focusedField === 'confirmPassword', filled: confirmPassword }">
            <div class="input-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <input
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              id="confirmPassword"
              @focus="focusedField = 'confirmPassword'"
              @blur="focusedField = ''"
              required
              autocomplete="new-password"
            />
            <label for="confirmPassword">确认密码</label>
            <div class="input-line"></div>
            <button type="button" class="toggle-password" @click="showConfirmPassword = !showConfirmPassword">
              <svg v-if="!showConfirmPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>

          <transition name="fade">
            <div v-if="error" class="error-toast">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span>{{ error }}</span>
            </div>
          </transition>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span class="btn-text">{{ loading ? '' : (isRegister ? '创建账号' : '登录') }}</span>
            <div v-if="loading" class="btn-loader">
              <div class="loader-ring"></div>
            </div>
            <svg v-if="!loading" class="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12"/>
              <polyline points="12 5 19 12 12 19"/>
            </svg>
          </button>
        </form>

        <div class="form-footer">
          <p class="toggle-text">
            {{ isRegister ? '已有账号？' : '还没有账号？' }}
            <button type="button" class="toggle-btn" @click="switchMode">
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

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')
const focusedField = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)

function getStarStyle(_n: number) {
  const size = Math.random() * 3 + 1
  const x = Math.random() * 100
  const y = Math.random() * 100
  const delay = Math.random() * 3
  const duration = Math.random() * 2 + 2
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${x}%`,
    top: `${y}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

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
  background: #0a0a14;
  position: relative;
  overflow: hidden;
}

.login-left {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: linear-gradient(135deg, #0a0a14 0%, #0f0f1a 50%, #12121f 100%);
  padding: 60px;
  
  @media (max-width: 968px) {
    display: none;
  }
}

.stars-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.star {
  position: absolute;
  background: white;
  border-radius: 50%;
  animation: twinkle ease-in-out infinite;
  opacity: 0.6;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.floating-orbs {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.4;
  animation: float-orb 20s ease-in-out infinite;
}

.orb-1 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #00d4ff, #0066ff);
  top: 10%;
  left: 20%;
  animation-delay: 0s;
}

.orb-2 {
  width: 250px;
  height: 250px;
  background: linear-gradient(135deg, #7b2cbf, #9d4edd);
  bottom: 20%;
  right: 10%;
  animation-delay: -7s;
}

.orb-3 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #00ff9d, #00d4ff);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -14s;
}

@keyframes float-orb {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -30px) scale(1.1); }
  50% { transform: translate(-20px, 20px) scale(0.9); }
  75% { transform: translate(20px, 30px) scale(1.05); }
}

.brand-content {
  position: relative;
  z-index: 1;
  text-align: center;
}

.logo-wrapper {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.logo-icon {
  width: 120px;
  height: 120px;
  position: relative;
  animation: logo-float 4s ease-in-out infinite;
}

@keyframes logo-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.constellation-svg {
  width: 100%;
  height: 100%;
  
  .star-point {
    fill: #00d4ff;
    filter: drop-shadow(0 0 8px #00d4ff);
    animation: pulse-star 2s ease-in-out infinite;
  }
  
  .star-line {
    stroke: rgba(0, 212, 255, 0.3);
    stroke-width: 1;
    animation: line-glow 3s ease-in-out infinite;
  }
  
  .center-point {
    fill: #7b2cbf;
    filter: drop-shadow(0 0 12px #7b2cbf);
    animation: pulse-center 2s ease-in-out infinite;
  }
}

@keyframes pulse-star {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

@keyframes pulse-center {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.3); opacity: 1; }
}

@keyframes line-glow {
  0%, 100% { stroke-opacity: 0.3; }
  50% { stroke-opacity: 0.6; }
}

.brand-title {
  font-size: 48px;
  font-weight: 700;
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 50%, #00ff9d 100%);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradient-shift 5s ease infinite;
  margin-bottom: 12px;
  letter-spacing: 4px;
}

@keyframes gradient-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.brand-tagline {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 48px;
  letter-spacing: 2px;
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 280px;
  margin: 0 auto;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(0, 212, 255, 0.3);
    transform: translateX(8px);
    
    .feature-icon {
      color: #00d4ff;
      transform: scale(1.1);
    }
  }
}

.feature-icon {
  width: 24px;
  height: 24px;
  color: rgba(255, 255, 255, 0.6);
  transition: all 0.3s ease;
  
  svg {
    width: 100%;
    height: 100%;
  }
}

.feature-item span {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.8);
}

.login-right {
  width: 520px;
  min-width: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: linear-gradient(180deg, #0d0d1a 0%, #0a0a14 100%);
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 1px;
    background: linear-gradient(180deg, transparent, rgba(0, 212, 255, 0.3), transparent);
  }
  
  @media (max-width: 968px) {
    width: 100%;
    min-width: auto;
    padding: 40px 24px;
    
    &::before {
      display: none;
    }
  }
}

.login-form-wrapper {
  width: 100%;
  max-width: 380px;
  animation: form-enter 0.6s ease-out;
}

@keyframes form-enter {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-header {
  margin-bottom: 40px;
  
  h2 {
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 8px;
    letter-spacing: 1px;
  }
  
  p {
    font-size: 15px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.input-group {
  position: relative;
  
  .input-icon {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    color: rgba(255, 255, 255, 0.4);
    transition: color 0.3s ease;
    z-index: 2;
    
    svg {
      width: 100%;
      height: 100%;
    }
  }
  
  input {
    width: 100%;
    padding: 16px 0 16px 32px;
    background: transparent;
    border: none;
    font-size: 16px;
    color: #fff;
    position: relative;
    z-index: 2;
    
    &:focus {
      outline: none;
    }
  }
  
  label {
    position: absolute;
    left: 32px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 16px;
    color: rgba(255, 255, 255, 0.4);
    pointer-events: none;
    transition: all 0.3s ease;
    z-index: 1;
  }
  
  .input-line {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      width: 0;
      height: 2px;
      background: linear-gradient(90deg, #00d4ff, #7b2cbf);
      transition: all 0.3s ease;
      transform: translateX(-50%);
    }
  }
  
  &.focused, &.filled {
    label {
      top: -8px;
      left: 0;
      font-size: 12px;
      color: #00d4ff;
      transform: none;
    }
    
    .input-icon {
      color: #00d4ff;
    }
    
    .input-line::after {
      width: 100%;
    }
  }
  
  .toggle-password {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    cursor: pointer;
    padding: 0;
    z-index: 2;
    transition: color 0.3s ease;
    
    &:hover {
      color: #00d4ff;
    }
    
    svg {
      width: 100%;
      height: 100%;
    }
  }
}

.error-toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  color: #ef4444;
  font-size: 14px;
  
  svg {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }
}

.fade-enter-active, .fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.submit-btn {
  position: relative;
  width: 100%;
  padding: 18px;
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
  margin-top: 8px;
  
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #7b2cbf 0%, #00d4ff 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
    
    &::before {
      opacity: 1;
    }
    
    .btn-arrow {
      transform: translateX(4px);
    }
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
  
  .btn-text, .btn-arrow, .btn-loader {
    position: relative;
    z-index: 1;
  }
  
  .btn-text {
    margin-right: 8px;
  }
  
  .btn-arrow {
    width: 18px;
    height: 18px;
    display: inline-block;
    vertical-align: middle;
    transition: transform 0.3s ease;
  }
  
  .btn-loader {
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  .loader-ring {
    width: 22px;
    height: 22px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-footer {
  margin-top: 32px;
  text-align: center;
}

.toggle-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.toggle-btn {
  background: none;
  border: none;
  color: #00d4ff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  margin-left: 4px;
  transition: all 0.3s ease;
  
  &:hover {
    color: #4de8ff;
    text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
  }
}
</style>
