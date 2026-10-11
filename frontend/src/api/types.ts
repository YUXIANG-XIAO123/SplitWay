/**
 * 与架构文档 §5（已冻结接口契约）一一对应的类型定义。
 * 金额字段一律为整数分（amount_cents / paid_cents / share_cents / net_cents），
 * 全程不出现浮点数（架构 §3.1）。
 */

/** 用户（/api/auth/*） */
export interface User {
  id: number
  username: string
}

/** POST /api/auth/login 响应 */
export interface AuthTokenResponse {
  access_token: string
  token_type: string
  user: User
}

/** 搭子帖状态 */
export type PostStatus = 'open' | 'closed'

/** 搭子帖（§3.2 partner_posts） */
export interface PartnerPost {
  id: number
  owner_id: number
  owner_username?: string
  destination: string
  depart_date: string
  need_count: number
  note?: string | null
  status: PostStatus
  created_at: string
}

/** 成员状态机（§4.1） */
export type MemberStatus = 'pending' | 'joined' | 'rejected' | 'left'

/** 成员角色 */
export type MemberRole = 'owner' | 'member'

/** 房间成员（§3.2 room_members） */
export interface RoomMember {
  id: number
  room_id: number
  user_id: number
  username?: string
  status: MemberStatus
  role: MemberRole
  created_at: string
  updated_at?: string
}

/** 帖子详情中可见的申请人条目（§5.3：仅帖主可见明细） */
export interface PostApplicant {
  member_id: number
  user_id: number
  username?: string
  status: MemberStatus
}

/** GET /api/posts/{post_id} 出参：帖子 + 申请人列表 */
export interface PostDetail extends PartnerPost {
  applicants?: PostApplicant[]
  /** 帖子已创建的房间 id（用于跳转房间页 / 房间级申请），可能为 null */
  room_id?: number | null
}

/** GET /api/posts 出参 */
export interface PostListResponse {
  items: PartnerPost[]
  total: number
}

/** 房间状态 */
export type RoomStatus = 'open' | 'settled'

/** 房间（§3.2 rooms） */
export interface Room {
  id: number
  post_id: number
  owner_id: number
  owner_username?: string
  status: RoomStatus
  member_limit: number
  created_at: string
  /** 后端若返回当前用户在该房间的成员信息，可用于 UI 判断 */
  my_member_id?: number
  my_role?: MemberRole
}

/** 账单分摊明细（§3.2 bill_shares） */
export interface BillShare {
  member_id?: number
  user_id: number
  username?: string
  amount_cents: number
}

/** 账单（§3.2 bills + bill_shares） */
export interface Bill {
  id: number
  room_id: number
  payer_id: number
  payer_username?: string
  amount_cents: number
  note?: string | null
  created_at: string
  shares: BillShare[]
}

/** 结算明细行（§5.6） */
export interface SettlementItem {
  member_id: number
  user_id: number
  username: string
  paid_cents: number
  share_cents: number
  net_cents: number
}

/** 结算结果（§5.6） */
export interface Settlement {
  room_id: number
  settled_at: string
  items: SettlementItem[]
  total_cents: number
  check: { sum_share_equals_total: boolean }
}

/** POST /api/posts 入参 */
export interface CreatePostPayload {
  destination: string
  depart_date: string
  need_count: number
  note?: string
}

/** POST /api/rooms/{room_id}/bills 入参（§5.5） */
export interface CreateBillPayload {
  /** 付款人 user_id；省略时后端默认为操作者本人 */
  payer_id?: number
  amount_cents: number
  note?: string
  /** 参与分摊的成员 id 列表（room_members.id） */
  participant_member_ids: number[]
}
