<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

import { useAuth } from '@/composables/useAuth'

type TabKey = 'login' | 'register'

const router = useRouter()
const route = useRoute()
const { login, register } = useAuth()

const activeTab = ref<TabKey>('login')
const submitting = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const isRegister = computed(() => activeTab.value === 'register')

const submitLabel = computed(() => {
  if (submitting.value) {
    return isRegister.value ? '注册中…' : '登录中…'
  }
  return isRegister.value ? '注册' : '登录'
})

/** 切换 Tab：清空错误与密码输入，避免把上一个表单的输入带过去。 */
function switchTab(tab: TabKey): void {
  if (activeTab.value === tab) {
    return
  }
  activeTab.value = tab
  errorMessage.value = ''
  form.password = ''
  form.confirmPassword = ''
}

/**
 * 从后端统一错误体 {"detail": {"code": "<码>", "message": "<中文说明>"}}
 * 中取出可展示的中文说明。
 */
function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = (detail as { message?: unknown }).message
      if (typeof message === 'string' && message) {
        return message
      }
    }
    if (typeof detail === 'string' && detail) {
      return detail
    }
  }
  return '请求失败，请稍后重试'
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''

  const username = form.username.trim()
  const password = form.password

  if (!username || !password) {
    errorMessage.value = '用户名和密码不能为空'
    return
  }
  if (isRegister.value && password !== form.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  submitting.value = true
  try {
    if (isRegister.value) {
      await register(username, password)
      // 注册成功后直接登录，省去用户再输一次密码。
      await login(username, password)
    } else {
      await login(username, password)
    }

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <div class="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 class="text-center text-2xl font-semibold tracking-tight">SplitWay · 分途</h1>
      <p class="mt-2 text-center text-sm text-slate-500">结伴出行，账目清清楚楚</p>

      <!-- Tab 切换 -->
      <div class="mt-6 grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1">
        <button
          type="button"
          class="rounded-md py-2 text-sm font-medium transition"
          :class="
            activeTab === 'login'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          "
          @click="switchTab('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="rounded-md py-2 text-sm font-medium transition"
          :class="
            activeTab === 'register'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          "
          @click="switchTab('register')"
        >
          注册
        </button>
      </div>

      <form class="mt-6 space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="username" class="mb-1 block text-sm font-medium text-slate-700">用户名</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            autocomplete="username"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            placeholder="请输入用户名"
          />
        </div>

        <div>
          <label for="password" class="mb-1 block text-sm font-medium text-slate-700">密码</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            placeholder="请输入密码"
          />
        </div>

        <div v-if="isRegister">
          <label for="confirm-password" class="mb-1 block text-sm font-medium text-slate-700">
            确认密码
          </label>
          <input
            id="confirm-password"
            v-model="form.confirmPassword"
            type="password"
            autocomplete="new-password"
            class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            placeholder="请再次输入密码"
          />
        </div>

        <p v-if="errorMessage" class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {{ errorMessage }}
        </p>

        <button
          type="submit"
          :disabled="submitting"
          class="w-full rounded-lg bg-slate-900 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {{ submitLabel }}
        </button>
      </form>
    </div>
  </div>
</template>
