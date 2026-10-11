import { computed, reactive } from 'vue'
import * as authApi from '@/api/auth'
import { clearToken, getToken, setToken } from '@/api/token'
import type { User } from '@/api/types'

/**
 * 全局认证状态（单例）：只有"当前用户 + token"两项。
 * 架构 §7 D 已裁定不引入 Pinia，故用模块级 reactive 状态 + composable 暴露。
 */
interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
}

const state = reactive<AuthState>({
  user: null,
  token: getToken(),
  loading: false,
})

const isAuthenticated = computed(() => state.token !== null)

/** 登录：成功后写入 token 与用户信息 */
async function login(username: string, password: string): Promise<void> {
  const res = await authApi.login(username, password)
  setToken(res.access_token)
  state.token = res.access_token
  state.user = res.user
}

/** 注册：仅创建账号，不自动登录 */
async function register(username: string, password: string): Promise<void> {
  await authApi.register(username, password)
}

/** 拉取当前用户（页面刷新后恢复会话） */
async function loadMe(): Promise<void> {
  if (!state.token) {
    return
  }
  state.loading = true
  try {
    state.user = await authApi.fetchMe()
  } finally {
    state.loading = false
  }
}

/** 退出：清空内存与存储中的 token */
function logout(): void {
  clearToken()
  state.token = null
  state.user = null
}

export function useAuth() {
  return {
    state,
    isAuthenticated,
    login,
    register,
    loadMe,
    logout,
  }
}
