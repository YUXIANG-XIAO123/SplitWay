import { http } from './client'
import type { Bill, CreateBillPayload } from './types'

/** 把可能是数组或 {items:[]} 的响应规整为数组 */
function toArray(data: Bill[] | { items?: Bill[] } | null | undefined): Bill[] {
  if (Array.isArray(data)) {
    return data
  }
  return data?.items ?? []
}

/** GET /api/rooms/{room_id}/bills → 账单列表（含分摊） */
export async function listBills(roomId: number): Promise<Bill[]> {
  const { data } = await http.get<Bill[] | { items: Bill[] }>(`/rooms/${roomId}/bills`)
  return toArray(data)
}

/** POST /api/rooms/{room_id}/bills → 201 账单 + 分摊明细（仅 joined 成员；已结算 409） */
export async function createBill(roomId: number, payload: CreateBillPayload): Promise<Bill> {
  const { data } = await http.post<Bill>(`/rooms/${roomId}/bills`, payload)
  return data
}

/** DELETE /api/rooms/{room_id}/bills/{bill_id} → 204（仅房主；已结算 409） */
export async function deleteBill(roomId: number, billId: number): Promise<void> {
  await http.delete(`/rooms/${roomId}/bills/${billId}`)
}
