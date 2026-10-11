// API 层统一出口：各业务模块 + axios 实例 + 通用类型/错误工具。
export * as authApi from './auth'
export * as postsApi from './posts'
export * as roomsApi from './rooms'
export * as billsApi from './bills'
export * as settlementApi from './settlement'

export { http, toApiError, isAxiosError } from './client'
export type { ApiError } from './client'
export * from './types'
