<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuth } from '@/composables/useAuth'

// 占位页：仅用于验证「登录守卫 + 身份态」是否生效（对应验收 C5）。
// 该页面将由 Issue #8「找搭子列表页」替换，届时删除本文件中的占位内容。
const router = useRouter()
const { currentUser, logout } = useAuth()

function handleLogout(): void {
  logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen">
    <header
      class="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4"
    >
      <span class="text-lg font-semibold tracking-tight">SplitWay · 分途</span>
      <div class="flex items-center gap-4">
        <span class="text-sm text-slate-600">
          {{ currentUser ? currentUser.username : '未登录' }}
        </span>
        <button
          type="button"
          class="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-100"
          @click="handleLogout"
        >
          退出登录
        </button>
      </div>
    </header>

    <main class="mx-auto max-w-2xl px-6 py-12">
      <h1 class="text-xl font-semibold">首页占位</h1>
      <p class="mt-3 text-sm leading-6 text-slate-600">
        此页受登录守卫保护，只有携带有效 token 的用户才能访问。当前为占位内容，
        将由 Issue #8「找搭子列表页」替换。
      </p>
    </main>
  </div>
</template>
