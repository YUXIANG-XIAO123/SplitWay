import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { useAuth } from '@/composables/useAuth'
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/LoginView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true },
  },
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    // 未匹配路径兜底：重定向到首页（再由守卫决定是否跳登录页）。
    path: '/:pathMatch(.*)*',
    redirect: { name: 'home' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局前置守卫：
//   - 未登录访问受保护路由 -> 跳 /login，并带上 redirect 以便登录后回到原页面；
//   - 已登录访问 /login -> 跳首页。
router.beforeEach((to) => {
  const { isAuthenticated } = useAuth()
  const isPublic = to.meta.public === true

  if (!isPublic && !isAuthenticated.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (isPublic && isAuthenticated.value) {
    return { name: 'home' }
  }
  return true
})

export default router
