import axios, {
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { clearToken, getToken } from './token'

/**
 * 全局 axios 实例。
 * - baseURL 固定为 `/api`：开发经 Vite 代理，生产经 nginx 反代，两者都保持同源，
 *   正常路径下不触发跨域。
 * - 请求拦截器：自动带上 `Authorization: Bearer <token>`。身份一律由后端从 token 解析，
 *   前端不拼接、不传递任何身份参数（PRD P0-3 / 架构 §5.1）。
 * - 响应拦截器：401 视为未认证 → 清 token 并跳登录页。
 */
export const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

/** 后端统一业务错误体：{"detail": {"code": "...", "message": "..."}} */
export interface ApiError {
  code: string
  message: string
  status?: number
}

/** 把任意异常规整为可展示的错误对象（含 FastAPI 422 的结构化 detail）。 */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail: unknown = error.response?.data?.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const d = detail as { code?: unknown; message?: unknown }
      return {
        code: String(d.code ?? ''),
        message: String(d.message ?? '请求失败'),
        status,
      }
    }
    // FastAPI 422 的 detail 是数组，这里取第一条的 msg；否则回退到通用文案。
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown }
      return { code: 'validation_error', message: String(first.msg ?? '入参校验失败'), status }
    }
    if (typeof detail === 'string') {
      return { code: '', message: detail, status }
    }
    return { code: '', message: error.message || '网络请求失败', status }
  }
  if (error instanceof Error) {
    return { code: '', message: error.message }
  }
  return { code: '', message: '未知错误' }
}

export { isAxiosError } from 'axios'
