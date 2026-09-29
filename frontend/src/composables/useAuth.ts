import { computed, ref } from 'vue'

import { fetchMe as apiFetchMe, login as apiLogin, register as apiRegister } from '@/api/auth'
import type { User } from '@/api/auth'

/**
 * useAuth：当前用户与 token 的状态容器。
 *
 * 不引入 Pinia：本项目前端状态只有「当前用户 + token」两项，
 * 用模块级 ref 即可得到一个进程内单例，无需状态管理库。
 */

/** sessionStorage 中保存 token 的 key。 */
const TOKEN_STORAGE_KEY = 'splitway_token'

/**
 * token 存放位置的取舍：sessionStorage 而非 localStorage。
 *
 * localStorage 是持久化存储：关闭标签页/浏览器后 token 依然存在，等同「长期驻留」；
 * 一旦发生 XSS，攻击者可从任意同源页面读出这个长期有效的 token 并长期冒用身份。
 * sessionStorage 的生命周期与标签页绑定，标签页关闭即失效，显著缩小 token 的驻留窗口。
 * 代价：同一标签页内刷新仍保持登录；但关闭浏览器后需重新登录。
 * 取舍结论：V1 以「安全优先于便利」为准，故只用 sessionStorage，不用 localStorage。
 * 后续若改为 httpOnly Cookie 承载 token，可进一步消除「前端 JS 可读 token」的风险。
 */
const token = ref<string>(sessionStorage.getItem(TOKEN_STORAGE_KEY) ?? '')

/** 当前用户；未登录或尚未拉取时为 null。 */
const currentUser = ref<User | null>(null)

/** 是否已认证：以「内存中是否存在 token」为准，token 在刷新后从 sessionStorage 恢复。 */
const isAuthenticated = computed<boolean>(() => token.value.length > 0)

/** 写入 token，并同步 sessionStorage。传空串即清除。 */
function setToken(value: string): void {
  token.value = value
  if (value) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, value)
  } else {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY)
  }
}

/** 供 axios 实例（api/client.ts）读取 token，避免其直接依赖本模块。 */
export function readToken(): string {
  return token.value
}

/** 清除本地会话（token + 用户）。不负责跳转，跳转由装配层决定。 */
export function clearSession(): void {
  setToken('')
  currentUser.value = null
}

/** 登录：成功后写入 token 与用户信息。 */
async function login(username: string, password: string): Promise<User> {
  const result = await apiLogin({ username, password })
  setToken(result.access_token)
  currentUser.value = result.user
  return result.user
}

/** 注册：只创建账号，不自动登录（是否自动登录由调用方决定）。 */
async function register(username: string, password: string): Promise<User> {
  return apiRegister({ username, password })
}

/** 拉取当前用户（依赖 Authorization 头，由拦截器自动附加）。 */
async function fetchMe(): Promise<User> {
  const user = await apiFetchMe()
  currentUser.value = user
  return user
}

/** 退出登录：清除本地会话。 */
function logout(): void {
  clearSession()
}

/** 组合式函数出口。 */
export function useAuth() {
  return {
    token,
    currentUser,
    isAuthenticated,
    login,
    register,
    logout,
    fetchMe,
  }
}
