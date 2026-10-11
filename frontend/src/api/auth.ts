import { http } from './client'
import type { AuthTokenResponse, User } from './types'

/** POST /api/auth/register → 201 {id, username} */
export async function register(username: string, password: string): Promise<User> {
  const { data } = await http.post<User>('/auth/register', { username, password })
  return data
}

/** POST /api/auth/login → 200 {access_token, token_type, user} */
export async function login(username: string, password: string): Promise<AuthTokenResponse> {
  const { data } = await http.post<AuthTokenResponse>('/auth/login', { username, password })
  return data
}

/** GET /api/auth/me → 200 {id, username} */
export async function fetchMe(): Promise<User> {
  const { data } = await http.get<User>('/auth/me')
  return data
}
