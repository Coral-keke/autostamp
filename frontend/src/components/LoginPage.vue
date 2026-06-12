<template>
  <div class="login-overlay">
    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
            <rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="12" cy="13" r="3.5" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 8h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h1>AutoStamp</h1>
        <p>自动盖章系统 · 安全登录</p>
      </div>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="input-group">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="3" y="11" width="18" height="11" rx="2"/>
            <path d="M7 11V7a5 5 0 0110 0v4"/>
          </svg>
          <input
            ref="pwdRef"
            v-model="password"
            type="password"
            placeholder="请输入访问密码"
            autocomplete="current-password"
            :disabled="loading"
          />
        </div>
        <p v-if="error" class="login-error">{{ error }}</p>
        <button type="submit" class="login-btn" :disabled="loading || !password">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '验证中...' : '登 录' }}
        </button>
      </form>
      <p class="login-hint">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
        默认密码：autostamp（请通过环境变量 STAMP_WEB_PASSWORD 修改）
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['authenticated'])

const password = ref('')
const loading = ref(false)
const error = ref('')
const pwdRef = ref(null)

onMounted(() => pwdRef.value?.focus())

async function handleLogin() {
  if (!password.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '密码错误')
    }
    const data = await res.json()
    localStorage.setItem('stamp_token', data.token)
    emit('authenticated', data.token)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-overlay {
  position: fixed; inset: 0; z-index: 9999;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
}
.login-card {
  width: 400px; padding: 48px 40px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  box-shadow: 0 25px 60px rgba(0,0,0,0.4);
}
.login-header { text-align: center; margin-bottom: 32px; }
.login-icon { color: #6366f1; margin-bottom: 12px; }
.login-header h1 { font-size: 24px; font-weight: 700; color: #f1f5f9; letter-spacing: -.5px; margin: 0 0 6px; }
.login-header p { font-size: 13px; color: #64748b; margin: 0; }

.login-form { display: flex; flex-direction: column; gap: 16px; }
.input-group {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  transition: border-color .2s;
}
.input-group:focus-within { border-color: #6366f1; }
.input-group svg { color: #64748b; flex-shrink: 0; }
.input-group input {
  flex: 1; border: none; background: transparent;
  color: #f1f5f9; font-size: 15px; outline: none;
  font-family: inherit;
}
.input-group input::placeholder { color: #475569; }

.login-error {
  color: #f87171; font-size: 13px; margin: 0; text-align: center;
}

.login-btn {
  width: 100%; padding: 12px;
  background: #6366f1; color: white;
  border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all .2s;
}
.login-btn:hover:not(:disabled) { background: #4f46e5; transform: translateY(-1px); box-shadow: 0 8px 25px rgba(99,102,241,0.3); }
.login-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.login-hint {
  margin-top: 24px; text-align: center;
  font-size: 12px; color: #475569;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
</style>
