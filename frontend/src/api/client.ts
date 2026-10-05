import axios from 'axios'
import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

/**
 * 未授权（HTTP 401）处理回调。
 *
 * 这里刻意不 import router / useAuth：一旦 client.ts 反向依赖路由或身份状态模块，
 * 就会形成 client -> router -> useAuth -> api/auth -> client 的循环依赖。
 * 因此改为由装配层（main.ts）在启动时通过 setUnauthorizedHandler 注入
 * 「清除 token 并跳转登录页」的实际逻辑。
 */
export type UnauthorizedHandler = () => void

/** 读取当前 token 的回调：同样通过注入避免在 client.ts 里重复维护存储 key。 */
export type TokenReader = () => string

let unauthorizedHandler: UnauthorizedHandler | null = null
let tokenReader: TokenReader = () => ''

/** 注册「401 未授权」的处理逻辑（由 main.ts 调用）。 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler
}

/** 注册 token 读取器（由 main.ts / useAuth 调用）。 */
export function setTokenReader(reader: TokenReader): void {
  tokenReader = reader
}

/** 全局唯一的 axios 实例；统一前缀 /api，开发由 Vite proxy、生产由 nginx 转发到后端。 */
const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：身份只来自 token。
// 这里只在请求头附加 Authorization，绝不把身份字段拼进查询参数或请求体。
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenReader()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// 响应拦截器：401 统一视为「未认证」（token 缺失 / 无效 / 过期），
// 触发回调清除 token 并跳回登录页；其余错误原样抛给调用方处理。
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      unauthorizedHandler?.()
    }
    return Promise.reject(error)
  },
)

export default client
