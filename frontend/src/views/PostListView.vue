<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuth } from '@/composables/useAuth'
import { postsApi, toApiError } from '@/api'
import type { PartnerPost } from '@/api/types'
import { formatDate } from '@/utils/format'
import { postStatusClass, postStatusLabel } from '@/utils/labels'

const router = useRouter()
const { state, isAuthenticated, loadMe } = useAuth()

const posts = ref<PartnerPost[]>([])
const total = ref(0)
const loading = ref(false)
const listError = ref('')

const showForm = ref(false)
const submitting = ref(false)
const formError = ref('')
/** 刚发布成功的帖子；用于提示帖主"下一步去创建房间"。 */
const createdPost = ref<PartnerPost | null>(null)

const form = reactive({
  destination: '',
  depart_date: '',
  need_count: 2,
  note: '',
})

const myUserId = computed(() => state.user?.id ?? null)

async function ensureUser(): Promise<void> {
  if (isAuthenticated.value && state.user === null) {
    try {
      await loadMe()
    } catch {
      // 401 已由拦截器处理
    }
  }
}

async function loadPosts(): Promise<void> {
  loading.value = true
  listError.value = ''
  try {
    const res = await postsApi.listPosts({ status: 'open', page: 1, size: 50 })
    posts.value = res.items
    total.value = res.total
  } catch (error) {
    listError.value = toApiError(error).message
  } finally {
    loading.value = false
  }
}

function openDetail(post: PartnerPost): void {
  createdPost.value = null
  router.push({ name: 'post-detail', params: { id: String(post.id) } })
}

/** 发帖成功后直达详情页，引导帖主创建房间。 */
function goCreateRoom(): void {
  const post = createdPost.value
  if (post === null) {
    return
  }
  createdPost.value = null
  router.push({ name: 'post-detail', params: { id: String(post.id) } })
}

function resetForm(): void {
  form.destination = ''
  form.depart_date = ''
  form.need_count = 2
  form.note = ''
}

async function submitPost(): Promise<void> {
  formError.value = ''
  if (form.destination.trim().length === 0) {
    formError.value = '请输入目的地'
    return
  }
  if (form.depart_date.length === 0) {
    formError.value = '请选择出发日期'
    return
  }
  if (!Number.isInteger(form.need_count) || form.need_count < 2) {
    formError.value = '需求人数需为不小于 2 的整数'
    return
  }

  submitting.value = true
  try {
    const created = await postsApi.createPost({
      destination: form.destination.trim(),
      depart_date: form.depart_date,
      need_count: form.need_count,
      note: form.note.trim() || undefined,
    })
    resetForm()
    showForm.value = false
    await loadPosts()
    // 发帖只是第一步：必须由帖主创建房间，其他人才有「申请加入」的入口。
    createdPost.value = created
  } catch (error) {
    formError.value = toApiError(error).message
  } finally {
    submitting.value = false
  }
}

async function removePost(post: PartnerPost): Promise<void> {
  if (!window.confirm(`确认删除帖子「${post.destination}」？`)) {
    return
  }
  try {
    await postsApi.deletePost(post.id)
    await loadPosts()
  } catch (error) {
    listError.value = toApiError(error).message
  }
}

onMounted(async () => {
  await ensureUser()
  await loadPosts()
})
</script>

<template>
  <div class="min-h-full">
    <AppHeader />

    <main class="mx-auto max-w-5xl px-4 py-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="text-xl font-semibold text-slate-800">找搭子</h1>
          <p class="text-sm text-slate-500">共 {{ total }} 条招募中的帖子</p>
        </div>
        <button
          type="button"
          class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700"
          @click="showForm = !showForm"
        >
          {{ showForm ? '收起' : '发布搭子帖' }}
        </button>
      </div>

      <form
        v-if="showForm"
        class="mb-6 rounded-2xl border border-slate-200 bg-white p-5 space-y-4"
        @submit.prevent="submitPost"
      >
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">目的地</label>
            <input
              v-model="form.destination"
              type="text"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
              placeholder="例如：云南大理"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">出发日期</label>
            <input
              v-model="form.depart_date"
              type="date"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">需求人数</label>
            <input
              v-model.number="form.need_count"
              type="number"
              min="2"
              step="1"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">备注（可选）</label>
            <input
              v-model="form.note"
              type="text"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
              placeholder="行程偏好、预算等"
            />
          </div>
        </div>

        <p v-if="formError" class="text-sm text-rose-600">{{ formError }}</p>

        <div class="flex justify-end">
          <button
            type="submit"
            :disabled="submitting"
            class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-60"
          >
            {{ submitting ? '发布中…' : '确认发布' }}
          </button>
        </div>
      </form>

      <div
        v-if="createdPost"
        class="mb-4 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3"
      >
        <p class="text-sm leading-relaxed text-amber-900">
          帖子已发布，但还差一步 ——
          <strong>需要你进入帖子详情点「创建房间」，其他人才有「申请加入」的入口。</strong>
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
            @click.stop="goCreateRoom"
          >
            去创建房间
          </button>
          <button
            type="button"
            class="rounded-lg border border-amber-300 px-4 py-2 text-sm text-amber-800 hover:bg-amber-100"
            @click.stop="createdPost = null"
          >
            知道了
          </button>
        </div>
      </div>

      <p v-if="listError" class="mb-4 text-sm text-rose-600">{{ listError }}</p>
      <p v-if="loading" class="text-sm text-slate-500">加载中…</p>
      <p v-else-if="posts.length === 0" class="text-sm text-slate-500">暂无帖子。</p>

      <ul class="space-y-3">
        <li
          v-for="post in posts"
          :key="post.id"
          class="rounded-2xl border border-slate-200 bg-white p-4 hover:border-sky-300 hover:shadow-sm transition cursor-pointer"
          @click="openDetail(post)"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <h2 class="text-base font-semibold text-slate-800 truncate">
                  {{ post.destination }}
                </h2>
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="postStatusClass(post.status)"
                >
                  {{ postStatusLabel(post.status) }}
                </span>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
                <span>出发日期：{{ formatDate(post.depart_date) }}</span>
                <span>需求人数：{{ post.need_count }}</span>
                <span>发起人：{{ post.owner_username ?? post.owner_id }}</span>
              </div>
              <p v-if="post.note" class="mt-2 text-sm text-slate-500 line-clamp-2">
                {{ post.note }}
              </p>
            </div>

            <button
              v-if="myUserId !== null && post.owner_id === myUserId"
              type="button"
              class="shrink-0 rounded-lg border border-rose-200 px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50"
              @click.stop="removePost(post)"
            >
              删除
            </button>
          </div>
        </li>
      </ul>
    </main>
  </div>
</template>
