import client from '@/api/client'

/**
 * 与后端 /api/auth/* 对齐的出入参类型。
 * 字段名严格遵循已冻结的接口契约（见 architecture.md §5.2），不得改动。
 */

/** 当前用户。后端只返回 id 与 username。 */
export interface User {
  id: number
  username: string
}

/** 注册 / 登录的入参。 */
export interface AuthCredentials {
  username: string
  password: string
}

/** 登录的返回体。token_type 固定为 'bearer'。 */
export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

/** POST /api/auth/register -> 201 {id, username} */
export async function register(payload: AuthCredentials): Promise<User> {
  const { data } = await client.post<User>('/auth/register', payload)
  return data
}

/** POST /api/auth/login -> 200 {access_token, token_type, user} */
export async function login(payload: AuthCredentials): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', payload)
  return data
}

/** GET /api/auth/me -> 200 {id, username}（依赖 Authorization 头，无身份入参） */
export async function fetchMe(): Promise<User> {
  const { data } = await client.get<User>('/auth/me')
  return data
}
