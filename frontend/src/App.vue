<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import { useAuth } from '@/composables/useAuth'

const { isAuthenticated, currentUser, fetchMe, logout } = useAuth()

// 刷新页面后 token 仍在 sessionStorage，但内存中的用户信息为空。
// 这里用 GET /api/auth/me 补齐用户信息；若 token 已失效（401），
// 响应拦截器会触发清会话与跳登录，这里再兜底调用一次 logout。
onMounted(async () => {
  if (isAuthenticated.value && !currentUser.value) {
    try {
      await fetchMe()
    } catch {
      logout()
    }
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <RouterView />
  </div>
</template>
