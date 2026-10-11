import type { MemberStatus, PostStatus, RoomStatus } from '@/api/types'

/** 搭子帖状态中文标签 */
export function postStatusLabel(status: PostStatus): string {
  return status === 'open' ? '招募中' : '已关闭'
}

/** 帖子状态对应的 Tailwind 徽章样式 */
export function postStatusClass(status: PostStatus): string {
  return status === 'open'
    ? 'bg-emerald-100 text-emerald-700'
    : 'bg-slate-200 text-slate-600'
}

/** 房间状态中文标签 */
export function roomStatusLabel(status: RoomStatus): string {
  return status === 'open' ? '进行中' : '已结算'
}

/** 房间状态对应的 Tailwind 徽章样式 */
export function roomStatusClass(status: RoomStatus): string {
  return status === 'open'
    ? 'bg-sky-100 text-sky-700'
    : 'bg-amber-100 text-amber-700'
}

/** 成员状态中文标签 */
export function memberStatusLabel(status: MemberStatus): string {
  const map: Record<MemberStatus, string> = {
    pending: '申请中',
    joined: '已加入',
    rejected: '已拒绝',
    left: '已退出',
  }
  return map[status]
}

/** 成员状态对应的 Tailwind 徽章样式 */
export function memberStatusClass(status: MemberStatus): string {
  const map: Record<MemberStatus, string> = {
    pending: 'bg-amber-100 text-amber-700',
    joined: 'bg-emerald-100 text-emerald-700',
    rejected: 'bg-rose-100 text-rose-700',
    left: 'bg-slate-200 text-slate-600',
  }
  return map[status]
}
