<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'

const { state, isAuthenticated, loadMe } = useAuth()

// 页面刷新后：token 仍在 sessionStorage，但用户信息在内存里会丢；
// 这里补一次 /auth/me，恢复当前用户，供路由守卫与页面判断"我是不是帖主/房主"。
onMounted(async () => {
  if (isAuthenticated.value && state.user === null) {
    try {
      await loadMe()
    } catch {
      // 401 已由响应拦截器处理（清 token、跳登录）
    }
  }
})
</script>

<template>
  <router-view />
</template>
