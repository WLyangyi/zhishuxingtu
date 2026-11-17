<template>
  <div class="login atlas-grid">
    <StarField :density="110" class="login__stars" />
    <div class="login__outline outline-word" aria-hidden="true">OBSERVATORY</div>

    <section class="login__brand">
      <header class="login__mark">
        <BrandMark class="login__mark-icon" />
        <span class="login__wordmark">知枢星图</span>
        <span class="readout login__mark-kicker">DEEP SPACE OBSERVATORY</span>
      </header>

      <div class="login__hero">
        <h1 class="login__headline">
          连接知识，<br />
          <span class="login__headline-gold">点亮思维。</span>
        </h1>
        <p class="readout login__coords">RA 05H 35M · DEC −05° 23′ · 你的坐标</p>
      </div>

      <ConstellationArt variant="login" :width="360" :height="200" class="login__constellation" />

      <ul class="login__features">
        <li v-for="(feature, index) in features" :key="feature.title" class="login__feature">
          <span class="readout login__feature-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="login__feature-title">{{ feature.title }}</span>
          <span class="login__feature-line" aria-hidden="true" />
          <span class="login__feature-desc">{{ feature.description }}</span>
        </li>
      </ul>
    </section>

    <section class="login__panel">
      <div class="login__card">
        <BrandMark class="login__card-mark" />
        <h2 class="login__card-title">{{ isRegister ? '建立观测账号' : '回到知枢星图' }}</h2>
        <p class="login__card-subtitle">
          {{ isRegister ? '从今天起，让每条思考都有坐标。' : '今夜的星空已经就位，继续你的巡夜。' }}
        </p>

        <form class="login__form" @submit.prevent="handleSubmit">
          <AppInput
            v-model="username"
            label="用户名"
            placeholder="请输入用户名"
            autocomplete="username"
            :disabled="loading"
          />

          <AppInput
            v-model="password"
            label="密码"
            :type="showPassword ? 'text' : 'password'"
            placeholder="请输入密码"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            :disabled="loading"
          >
            <template #suffix>
              <button
                type="button"
                class="login__eye"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" :size="14" :stroke-width="1.8" />
                <Eye v-else :size="14" :stroke-width="1.8" />
              </button>
            </template>
          </AppInput>

          <AppInput
            v-if="isRegister"
            v-model="confirmPassword"
            label="确认密码"
            :type="showPassword ? 'text' : 'password'"
            placeholder="再次输入密码"
            autocomplete="new-password"
            :disabled="loading"
          />

          <p v-if="error" class="login__error" role="alert">{{ error }}</p>

          <AppButton type="submit" block :loading="loading" size="lg" class="login__submit">
            {{ isRegister ? '创建账号' : '进入观测台 →' }}
          </AppButton>
        </form>

        <button type="button" class="login__switch" @click="switchMode">
          {{ isRegister ? '已有账号？返回登录' : '还没有账号？创建账号' }}
        </button>

        <span class="readout login__footer">ZHISHU OBSERVATORY · SINCE 2026</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import StarField from '@/components/domain/StarField.vue'
import ConstellationArt from '@/components/domain/ConstellationArt.vue'
import BrandMark from '@/components/layout/BrandMark.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppButton from '@/components/ui/AppButton.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)

const features = [
  { title: '知识图谱', description: '以星图方式看见知识的关联' },
  { title: '双向链接', description: '让每条思考都连成星座' },
  { title: 'Agentic 检索', description: '混合检索 + 三查反思，答案有据可循' }
]

function switchMode() {
  isRegister.value = !isRegister.value
  error.value = ''
  confirmPassword.value = ''
}

async function handleSubmit() {
  error.value = ''

  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }

  if (isRegister.value) {
    if (password.value.length < 8) {
      error.value = '密码长度至少 8 位'
      return
    }
    if (password.value !== confirmPassword.value) {
      error.value = '两次输入的密码不一致'
      return
    }
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await authStore.register(username.value.trim(), password.value)
    }
    await authStore.login(username.value.trim(), password.value)
    router.push('/')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  position: relative;
  display: flex;
  min-height: 100vh;
  background: var(--bg);
  overflow: hidden;
}

.login__stars {
  opacity: 0.9;
}

.login__outline {
  left: -2vw;
  bottom: -3vh;
  font-size: clamp(120px, 18vw, 260px);
  opacity: 0.55;
}

.login__brand {
  position: relative;
  z-index: 1;
  flex: 1.15;
  display: flex;
  flex-direction: column;
  padding: 34px 48px 28px;
  min-width: 0;
}

.login__mark {
  display: flex;
  align-items: center;
  gap: 10px;
}

.login__mark-icon {
  width: 26px;
  height: 26px;
  flex: none;
}

.login__wordmark {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.login__mark-kicker {
  margin-left: 6px;
}

.login__hero {
  margin-top: auto;
  margin-bottom: 30px;
  max-width: 620px;
}

.login__headline {
  font-family: var(--font-display);
  font-size: clamp(44px, 5.2vw, 72px);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.045em;
  color: var(--text);
}

.login__headline-gold {
  color: var(--gold);
}

.login__coords {
  margin-top: 22px;
  font-size: 10px;
  color: var(--t3);
}

.login__constellation {
  position: absolute;
  right: 8%;
  bottom: 27%;
  opacity: 0.75;
  pointer-events: none;
}

.login__features {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--line);
}

.login__feature {
  display: grid;
  grid-template-columns: 34px 120px 1fr auto;
  align-items: center;
  gap: 16px;
  height: 44px;
  border-bottom: 1px solid var(--line);
  transition: transform var(--d-base) var(--ease-out);
}

.login__feature:hover {
  transform: translateX(6px);
}

.login__feature-index {
  color: var(--gold);
}

.login__feature-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}

.login__feature-line {
  height: 1px;
  background: var(--line);
}

.login__feature-desc {
  font-size: 11px;
  color: var(--t3);
  text-align: right;
}

.login__panel {
  position: relative;
  z-index: 1;
  flex: 0.85;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  border-left: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 72%, transparent);
}

.login__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 330px;
  text-align: center;
}

.login__card-mark {
  width: 30px;
  height: 30px;
  margin-bottom: 18px;
}

.login__card-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.login__card-subtitle {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--t3);
}

.login__form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  margin-top: 28px;
  text-align: left;
}

.login__eye {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--t3);
}

.login__eye:hover {
  color: var(--text);
}

.login__error {
  font-size: 11px;
  color: var(--danger);
  line-height: 1.5;
}

.login__submit {
  margin-top: 4px;
}

.login__switch {
  margin-top: 18px;
  font-size: 11px;
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.login__switch:hover {
  color: var(--gold);
}

.login__footer {
  margin-top: 40px;
  font-size: 9px;
  color: var(--t3);
}

@media (max-width: 900px) {
  .login__brand {
    display: none;
  }

  .login__panel {
    flex: 1;
    border-left: 0;
    padding: 32px 22px;
  }

  .login__card {
    max-width: 360px;
  }
}
</style>
