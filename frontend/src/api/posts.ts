import { http } from './client'
import type { CreatePostPayload, PartnerPost, PostDetail, PostListResponse } from './types'

/** GET /api/posts?status=open&page=1&size=20 → {items, total} */
export async function listPosts(params?: {
  status?: string
  page?: number
  size?: number
}): Promise<PostListResponse> {
  const { data } = await http.get<PostListResponse>('/posts', { params })
  // 防御：兼容后端直接返回数组的情形
  if (Array.isArray(data)) {
    const items = data as PartnerPost[]
    return { items, total: items.length }
  }
  return { items: data.items ?? [], total: data.total ?? data.items?.length ?? 0 }
}

/** GET /api/posts/{post_id} → 帖子 + 申请人列表 */
export async function getPost(postId: number): Promise<PostDetail> {
  const { data } = await http.get<PostDetail>(`/posts/${postId}`)
  return data
}

/** POST /api/posts → 201 帖子 */
export async function createPost(payload: CreatePostPayload): Promise<PartnerPost> {
  const { data } = await http.post<PartnerPost>('/posts', payload)
  return data
}

/** DELETE /api/posts/{post_id} → 204（仅帖主） */
export async function deletePost(postId: number): Promise<void> {
  await http.delete(`/posts/${postId}`)
}
