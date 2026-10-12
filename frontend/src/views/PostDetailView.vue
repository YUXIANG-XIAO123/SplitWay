<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuth } from '@/composables/useAuth'
import { postsApi, roomsApi, toApiError } from '@/api'
import type { PostDetail } from '@/api/types'
import { formatDate } from '@/utils/format'
import { memberStatusClass, memberStatusLabel, postStatusClass, postStatusLabel } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const { state, isAuthenticated, loadMe } = useAuth()

const postId = computed(() => Number(route.params.id))

const post = ref<PostDetail | null>(null)
const loading = ref(false)
const pageError = ref('')
const actionError = ref('')
const actionInfo = ref('')
const busy = ref(false)

const isOwner = computed(
  () => post.value !== null && state.user !== null && post.value.owner_id === state.user.id,
)

const roomId = computed(() => post.value?.room_id ?? null)

const pendingApplicants = computed(
  () => (post.value?.applicants ?? []).filter((a) => a.status === 'pending'),
)

const otherApplicants = computed(
  () => (post.value?.applicants ?? []).filter((a) => a.status !== 'pending'),
)

/** 当前用户是否已是该房间成员（用于禁用"申请加入"） */
const alreadyMember = computed(() => {
  if (state.user === null) {
    return false
  }
  return (post.value?.applicants ?? []).some(
    (a) => a.user_id === state.user!.id && (a.status === 'pending' || a.status === 'joined'),
  )
})

async function ensureUser(): Promise<void> {
  if (isAuthenticated.value && state.user === null) {
    try {
      await loadMe()
    } catch {
      // 401 已由拦截器处理
    }
  }
}

async function loadPost(): Promise<void> {
  loading.value = true
  pageError.value = ''
  try {
    post.value = await postsApi.getPost(postId.value)
  } catch (error) {
    pageError.value = toApiError(error).message
  } finally {
    loading.value = false
  }
}

/** 帖主：基于本帖创建房间，成功后进入房间页并成为房主 */
async function handleCreateRoom(): Promise<void> {
  if (post.value === null) {
    return
  }
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    const room = await roomsApi.createRoom(post.value.id)
    await router.push({ name: 'room', params: { id: String(room.id) } })
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

/** 非帖主：对帖子对应的房间发起加入申请（房间级接口） */
async function handleApply(): Promise<void> {
  if (roomId.value === null) {
    actionError.value = '房主尚未创建房间，暂无法申请加入'
    return
  }
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await roomsApi.requestJoin(roomId.value)
    actionInfo.value = '已提交申请，等待房主审批'
    await loadPost()
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

async function handleApprove(memberId: number): Promise<void> {
  if (roomId.value === null) {
    return
  }
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await roomsApi.approveMember(roomId.value, memberId)
    await loadPost()
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

async function handleReject(memberId: number): Promise<void> {
  if (roomId.value === null) {
    return
  }
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await roomsApi.rejectMember(roomId.value, memberId)
    await loadPost()
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

function goRoom(): void {
  if (roomId.value !== null) {
    router.push({ name: 'room', params: { id: String(roomId.value) } })
  }
}

onMounted(async () => {
  await ensureUser()
  await loadPost()
})
</script>

<template>
  <div class="min-h-full">
    <AppHeader />

    <main class="mx-auto max-w-3xl px-4 py-6">
      <router-link
        :to="{ name: 'post-list' }"
        class="inline-block mb-4 text-sm text-sky-600 hover:underline"
      >
        ← 返回列表
      </router-link>

      <p v-if="loading" class="text-sm text-slate-500">加载中…</p>
      <p v-else-if="pageError" class="text-sm text-rose-600">{{ pageError }}</p>

      <template v-else-if="post">
        <div class="rounded-2xl border border-slate-200 bg-white p-6">
          <div class="flex items-start justify-between gap-4">
            <h1 class="text-2xl font-bold text-slate-800">{{ post.destination }}</h1>
            <span
              class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
              :class="postStatusClass(post.status)"
            >
              {{ postStatusLabel(post.status) }}
            </span>
          </div>

          <dl class="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
            <div>
              <dt class="text-slate-500">出发日期</dt>
              <dd class="text-slate-800">{{ formatDate(post.depart_date) }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">需求人数</dt>
              <dd class="text-slate-800">{{ post.need_count }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">发起人</dt>
              <dd class="text-slate-800">{{ post.owner_username ?? post.owner_id }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">房间</dt>
              <dd class="text-slate-800">
                {{ roomId !== null ? `已创建（#${roomId}）` : '尚未创建' }}
              </dd>
            </div>
          </dl>

          <p v-if="post.note" class="mt-4 text-sm text-slate-600 whitespace-pre-wrap">
            {{ post.note }}
          </p>

          <p v-if="actionError" class="mt-4 text-sm text-rose-600">{{ actionError }}</p>
          <p v-if="actionInfo" class="mt-4 text-sm text-emerald-600">{{ actionInfo }}</p>

          <div class="mt-5 flex flex-wrap gap-3">
            <template v-if="isOwner">
              <template v-if="roomId === null">
                <button
                  type="button"
                  :disabled="busy"
                  class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-60"
                  @click="handleCreateRoom"
                >
                  创建房间
                </button>
                <span class="self-center text-sm text-slate-500">
                  创建房间后，其他人才有「申请加入」的入口
                </span>
              </template>
              <button
                v-else
                type="button"
                class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700"
                @click="goRoom"
              >
                进入房间
              </button>
            </template>

            <template v-else>
              <button
                type="button"
                :disabled="busy || roomId === null || alreadyMember"
                class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-60 disabled:cursor-not-allowed"
                @click="handleApply"
              >
                {{ alreadyMember ? '已提交申请' : '申请加入' }}
              </button>
              <span v-if="roomId === null" class="text-sm text-slate-500 self-center">
                房主尚未创建房间
              </span>
            </template>
          </div>
        </div>

        <section v-if="isOwner" class="mt-6">
          <h2 class="text-lg font-semibold text-slate-800 mb-3">申请人</h2>
          <p v-if="(post.applicants ?? []).length === 0" class="text-sm text-slate-500">
            暂无申请人。
          </p>
          <ul v-else class="space-y-2">
            <li
              v-for="applicant in [...pendingApplicants, ...otherApplicants]"
              :key="applicant.member_id"
              class="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
            >
              <div class="flex items-center gap-3">
                <span class="text-sm text-slate-800">
                  {{ applicant.username ?? `用户#${applicant.user_id}` }}
                </span>
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="memberStatusClass(applicant.status)"
                >
                  {{ memberStatusLabel(applicant.status) }}
                </span>
              </div>

              <div v-if="applicant.status === 'pending'" class="flex gap-2">
                <button
                  type="button"
                  :disabled="busy || roomId === null"
                  class="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
                  @click="handleApprove(applicant.member_id)"
                >
                  通过
                </button>
                <button
                  type="button"
                  :disabled="busy || roomId === null"
                  class="rounded-lg border border-rose-200 px-3 py-1.5 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-60"
                  @click="handleReject(applicant.member_id)"
                >
                  拒绝
                </button>
              </div>
            </li>
          </ul>
          <p v-if="roomId === null" class="mt-2 text-xs text-slate-500">
            需先创建房间后才能审批申请。
          </p>
        </section>
      </template>
    </main>
  </div>
</template>
