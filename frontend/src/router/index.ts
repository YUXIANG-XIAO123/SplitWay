import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getToken } from '@/api/token'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'post-list',
    component: () => import('@/views/PostListView.vue'),
  },
  {
    path: '/posts/:id',
    name: 'post-detail',
    component: () => import('@/views/PostDetailView.vue'),
  },
  {
    path: '/rooms/:id',
    name: 'room',
    component: () => import('@/views/RoomView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'post-list' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/** 登录守卫：非公开页面在无 token 时重定向到登录页，并带上回跳地址。 */
router.beforeEach((to) => {
  const authenticated = getToken() !== null
  if (!to.meta.public && !authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && authenticated) {
    return { name: 'post-list' }
  }
  return true
})

export default router
