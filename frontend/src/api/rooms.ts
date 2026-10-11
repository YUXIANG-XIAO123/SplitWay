import { http } from './client'
import type { Room, RoomMember } from './types'

/** 把可能是数组或 {items:[]} 的响应规整为数组 */
function toArray<T>(data: T[] | { items?: T[] } | null | undefined): T[] {
  if (Array.isArray(data)) {
    return data
  }
  return data?.items ?? []
}

/** POST /api/rooms {post_id} → 201 房间（仅帖主） */
export async function createRoom(postId: number): Promise<Room> {
  const { data } = await http.post<Room>('/rooms', { post_id: postId })
  return data
}

/** GET /api/rooms → 我参与的房间列表 */
export async function listMyRooms(): Promise<Room[]> {
  const { data } = await http.get<Room[] | { items: Room[] }>('/rooms')
  return toArray<Room>(data)
}

/** GET /api/rooms/{room_id} → 房间详情（仅 joined/owner 成员，否则 403） */
export async function getRoom(roomId: number): Promise<Room> {
  const { data } = await http.get<Room>(`/rooms/${roomId}`)
  return data
}

/** GET /api/rooms/{room_id}/members → 成员列表 */
export async function listMembers(roomId: number): Promise<RoomMember[]> {
  const { data } = await http.get<RoomMember[] | { items: RoomMember[] }>(
    `/rooms/${roomId}/members`,
  )
  return toArray<RoomMember>(data)
}

/** POST /api/rooms/{room_id}/join-requests → 201 成员记录(pending)，重复申请 409 */
export async function requestJoin(roomId: number): Promise<RoomMember> {
  const { data } = await http.post<RoomMember>(`/rooms/${roomId}/join-requests`)
  return data
}

/** POST /api/rooms/{room_id}/members/{member_id}/approve → 200（仅房主，否则 403） */
export async function approveMember(roomId: number, memberId: number): Promise<void> {
  await http.post(`/rooms/${roomId}/members/${memberId}/approve`)
}

/** POST /api/rooms/{room_id}/members/{member_id}/reject → 200（仅房主，否则 403） */
export async function rejectMember(roomId: number, memberId: number): Promise<void> {
  await http.post(`/rooms/${roomId}/members/${memberId}/reject`)
}

/** POST /api/rooms/{room_id}/leave → 200（仅本人） */
export async function leaveRoom(roomId: number): Promise<void> {
  await http.post(`/rooms/${roomId}/leave`)
}
