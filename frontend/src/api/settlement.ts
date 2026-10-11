import { http, isAxiosError } from './client'
import type { Settlement } from './types'

/**
 * GET /api/rooms/{room_id}/settlement
 * @returns 结算结果；未结算时后端返回 404，这里规整为 null（不视为错误）。
 */
export async function getSettlement(roomId: number): Promise<Settlement | null> {
  try {
    const { data } = await http.get<Settlement>(`/rooms/${roomId}/settlement`)
    return data
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/** POST /api/rooms/{room_id}/settlement → 200 结算结果（仅房主；幂等，重复调用返回同一结果） */
export async function settleRoom(roomId: number): Promise<Settlement> {
  const { data } = await http.post<Settlement>(`/rooms/${roomId}/settlement`)
  return data
}
