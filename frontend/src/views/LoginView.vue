<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { toApiError } from '@/api/client'

type Mode = 'login' | 'register'

const router = useRouter()
const route = useRoute()
const { login, register } = useAuth()

const mode = ref<Mode>('login')
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const form = reactive({
  username: '',
  password: '',
  confirm: '',
})

const isRegister = computed(() => mode.value === 'register')

function switchMode(next: Mode): void {
  mode.value = next
  errorMessage.value = ''
  successMessage.value = ''
  form.password = ''
  form.confirm = ''
}

function validate(): string | null {
  if (form.username.trim().length < 1) {
    return '请输入用户名'
  }
  if (form.password.length < 1) {
    return '请输入密码'
  }
  if (isRegister.value && form.password !== form.confirm) {
    return '两次输入的密码不一致'
  }
  return null
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  successMessage.value = ''
  const invalid = validate()
  if (invalid) {
    errorMessage.value = invalid
    return
  }

  submitting.value = true
  try {
    if (isRegister.value) {
      await register(form.username.trim(), form.password)
      successMessage.value = '注册成功，请登录'
      mode.value = 'login'
      form.password = ''
      form.confirm = ''
    } else {
      await login(form.username.trim(), form.password)
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
      await router.replace(redirect)
    }
  } catch (error) {
    errorMessage.value = toApiError(error).message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-full flex items-center justify-center px-4 py-12">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-slate-800">SplitWay</h1>
        <p class="mt-2 text-sm text-slate-500">找搭子 · 建房间 · 记账 · 结算</p>
      </div>

      <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div class="grid grid-cols-2 text-center border-b border-slate-200">
          <button
            type="button"
            class="py-3 text-sm font-medium transition-colors"
            :class="
              mode === 'login'
                ? 'text-sky-600 bg-sky-50'
                : 'text-slate-500 hover:text-slate-700'
            "
            @click="switchMode('login')"
          >
            登录
          </button>
          <button
            type="button"
            class="py-3 text-sm font-medium transition-colors"
            :class="
              mode === 'register'
                ? 'text-sky-600 bg-sky-50'
                : 'text-slate-500 hover:text-slate-700'
            "
            @click="switchMode('register')"
          >
            注册
          </button>
        </div>

        <form class="p-6 space-y-4" @submit.prevent="handleSubmit">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1" for="username">
              用户名
            </label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              autocomplete="username"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-sky-400"
              placeholder="请输入用户名"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1" for="password">
              密码
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-sky-400"
              placeholder="请输入密码"
            />
          </div>

          <div v-if="isRegister">
            <label class="block text-sm font-medium text-slate-700 mb-1" for="confirm">
              确认密码
            </label>
            <input
              id="confirm"
              v-model="form.confirm"
              type="password"
              autocomplete="new-password"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-sky-400"
              placeholder="请再次输入密码"
            />
          </div>

          <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>
          <p v-if="successMessage" class="text-sm text-emerald-600">{{ successMessage }}</p>

          <button
            type="submit"
            :disabled="submitting"
            class="w-full rounded-lg bg-sky-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-sky-700 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {{ submitting ? '处理中…' : isRegister ? '注册' : '登录' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
