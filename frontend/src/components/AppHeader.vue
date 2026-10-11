<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { state, logout } = useAuth()

function handleLogout(): void {
  logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <header class="bg-white border-b border-slate-200">
    <div class="mx-auto max-w-5xl px-4 h-14 flex items-center justify-between">
      <router-link
        :to="{ name: 'post-list' }"
        class="text-lg font-semibold text-slate-800 hover:text-sky-600"
      >
        SplitWay
      </router-link>
      <div class="flex items-center gap-3 text-sm">
        <span v-if="state.user" class="text-slate-600">
          当前用户：<span class="font-medium text-slate-800">{{ state.user.username }}</span>
        </span>
        <button
          type="button"
          class="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-600 hover:bg-slate-50"
          @click="handleLogout"
        >
          退出
        </button>
      </div>
    </div>
  </header>
</template>
