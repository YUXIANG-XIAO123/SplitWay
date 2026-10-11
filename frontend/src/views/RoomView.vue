<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuth } from '@/composables/useAuth'
import { billsApi, roomsApi, settlementApi, toApiError } from '@/api'
import type { Bill, CreateBillPayload, Room, RoomMember, Settlement } from '@/api/types'
import { formatCents, formatNet, parseYuanToCents } from '@/utils/money'
import { formatDateTime } from '@/utils/format'
import { memberStatusClass, memberStatusLabel, roomStatusClass, roomStatusLabel } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const { state, isAuthenticated, loadMe } = useAuth()

const roomId = computed(() => Number(route.params.id))

const room = ref<Room | null>(null)
const members = ref<RoomMember[]>([])
const bills = ref<Bill[]>([])
const settlement = ref<Settlement | null>(null)

const loading = ref(false)
const pageError = ref('')
const actionError = ref('')
const actionInfo = ref('')
const busy = ref(false)

const amountInput = ref('')
const formError = ref('')

const form = reactive({
  payerId: null as number | null,
  participantMemberIds: [] as number[],
  note: '',
})

const myUserId = computed(() => state.user?.id ?? null)

const isHost = computed(
  () => room.value !== null && myUserId.value !== null && room.value.owner_id === myUserId.value,
)

const isSettled = computed(() => room.value?.status === 'settled')

const joinedMembers = computed(() => members.value.filter((m) => m.status === 'joined'))
const pendingMembers = computed(() => members.value.filter((m) => m.status === 'pending'))
const historyMembers = computed(() =>
  members.value.filter((m) => m.status === 'rejected' || m.status === 'left'),
)

/** 当前用户在该房间的成员记录（joined 才允许记账 / 退出） */
const myMembership = computed(() =>
  members.value.find((m) => m.user_id === myUserId.value) ?? null,
)

const myJoined = computed(() => myMembership.value?.status === 'joined')

/** 是否可新增账单：未结算 + 本人是 joined 成员 */
const canCreateBill = computed(() => !isSettled.value && myJoined.value)

async function ensureUser(): Promise<void> {
  if (isAuthenticated.value && state.user === null) {
    try {
      await loadMe()
    } catch {
      // 401 已由拦截器处理
    }
  }
}

async function loadAll(): Promise<void> {
  loading.value = true
  pageError.value = ''
  try {
    const [roomData, memberData, billData, settlementData] = await Promise.all([
      roomsApi.getRoom(roomId.value),
      roomsApi.listMembers(roomId.value),
      billsApi.listBills(roomId.value),
      settlementApi.getSettlement(roomId.value),
    ])
    room.value = roomData
    members.value = memberData
    bills.value = billData
    settlement.value = settlementData
    // 付款人默认设为本人（若本人是 joined 成员）
    if (form.payerId === null && myUserId.value !== null) {
      const mine = memberData.find((m) => m.user_id === myUserId.value && m.status === 'joined')
      if (mine) {
        form.payerId = myUserId.value
      }
    }
  } catch (error) {
    pageError.value = toApiError(error).message
  } finally {
    loading.value = false
  }
}

async function reloadMembers(): Promise<void> {
  members.value = await roomsApi.listMembers(roomId.value)
}

async function reloadBills(): Promise<void> {
  bills.value = await billsApi.listBills(roomId.value)
}

function memberName(member: RoomMember): string {
  return member.username ?? `用户#${member.user_id}`
}

function usernameOf(userId: number): string {
  return members.value.find((m) => m.user_id === userId)?.username ?? `用户#${userId}`
}

async function handleApprove(memberId: number): Promise<void> {
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await roomsApi.approveMember(roomId.value, memberId)
    await reloadMembers()
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

async function handleReject(memberId: number): Promise<void> {
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await roomsApi.rejectMember(roomId.value, memberId)
    await reloadMembers()
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

async function handleLeave(): Promise<void> {
  if (!window.confirm('确认退出该房间？退出后需重新申请加入。')) {
    return
  }
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await roomsApi.leaveRoom(roomId.value)
    await router.push({ name: 'post-list' })
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

/** 新增账单：金额唯一一次「元→分」换算发生在这里 */
async function submitBill(): Promise<void> {
  formError.value = ''
  actionError.value = ''
  actionInfo.value = ''

  const amountCents = parseYuanToCents(amountInput.value)
  if (amountCents === null) {
    formError.value = '金额需为正数且最多两位小数'
    return
  }
  if (form.participantMemberIds.length === 0) {
    formError.value = '请至少选择一名分摊成员'
    return
  }
  if (form.payerId === null) {
    formError.value = '请选择付款人'
    return
  }

  const payload: CreateBillPayload = {
    payer_id: form.payerId,
    amount_cents: amountCents,
    note: form.note.trim() || undefined,
    participant_member_ids: [...form.participantMemberIds],
  }

  busy.value = true
  try {
    await billsApi.createBill(roomId.value, payload)
    amountInput.value = ''
    form.note = ''
    await reloadBills()
  } catch (error) {
    formError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

async function removeBill(bill: Bill): Promise<void> {
  if (!window.confirm('确认删除该账单？')) {
    return
  }
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    await billsApi.deleteBill(roomId.value, bill.id)
    await reloadBills()
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

/** 触发结算（仅房主）。幂等：后端对已结算房间返回同一结果。 */
async function handleSettle(): Promise<void> {
  actionError.value = ''
  actionInfo.value = ''
  busy.value = true
  try {
    settlement.value = await settlementApi.settleRoom(roomId.value)
    await Promise.all([reloadBills(), reloadMembers()])
    room.value = await roomsApi.getRoom(roomId.value)
  } catch (error) {
    actionError.value = toApiError(error).message
  } finally {
    busy.value = false
  }
}

function participantNames(bill: Bill): string {
  if (!bill.shares || bill.shares.length === 0) {
    return '-'
  }
  return bill.shares.map((s) => s.username ?? usernameOf(s.user_id)).join('、')
}

onMounted(async () => {
  await ensureUser()
  await loadAll()
})
</script>

<template>
  <div class="min-h-full">
    <AppHeader />

    <main class="mx-auto max-w-5xl px-4 py-6">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <router-link
            v-if="room"
            :to="{ name: 'post-detail', params: { id: String(room.post_id) } }"
            class="text-sm text-sky-600 hover:underline"
          >
            ← 返回帖子
          </router-link>
          <h1 class="text-xl font-semibold text-slate-800 mt-1">
            房间 #{{ roomId }}
            <span
              v-if="room"
              class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium align-middle"
              :class="roomStatusClass(room.status)"
            >
              {{ roomStatusLabel(room.status) }}
            </span>
          </h1>
        </div>
      </div>

      <p v-if="loading" class="text-sm text-slate-500">加载中…</p>
      <p v-else-if="pageError" class="text-sm text-rose-600">{{ pageError }}</p>

      <p v-if="actionError" class="mb-3 text-sm text-rose-600">{{ actionError }}</p>
      <p v-if="actionInfo" class="mb-3 text-sm text-emerald-600">{{ actionInfo }}</p>

      <template v-if="!loading && !pageError && room">
        <!-- 成员区 -->
        <section class="rounded-2xl border border-slate-200 bg-white p-5 mb-6">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-lg font-semibold text-slate-800">成员</h2>
            <div class="text-xs text-slate-500">
              上限 {{ room.member_limit }} 人 · 已加入 {{ joinedMembers.length }} 人
            </div>
          </div>

          <ul class="divide-y divide-slate-100">
            <li
              v-for="member in members"
              :key="member.id"
              class="flex items-center justify-between py-3"
            >
              <div class="flex items-center gap-3">
                <span class="text-sm font-medium text-slate-800">{{ memberName(member) }}</span>
                <span
                  v-if="member.role === 'owner'"
                  class="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700"
                >
                  房主
                </span>
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="memberStatusClass(member.status)"
                >
                  {{ memberStatusLabel(member.status) }}
                </span>
              </div>

              <div v-if="isHost && member.status === 'pending'" class="flex gap-2">
                <button
                  type="button"
                  :disabled="busy"
                  class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
                  @click="handleApprove(member.id)"
                >
                  通过
                </button>
                <button
                  type="button"
                  :disabled="busy"
                  class="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-60"
                  @click="handleReject(member.id)"
                >
                  拒绝
                </button>
              </div>
            </li>
          </ul>

          <div v-if="!isHost && myJoined" class="mt-4">
            <button
              type="button"
              :disabled="busy"
              class="rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-60"
              @click="handleLeave"
            >
              退出房间
            </button>
          </div>
        </section>

        <!-- 记账区 -->
        <section class="rounded-2xl border border-slate-200 bg-white p-5 mb-6">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-lg font-semibold text-slate-800">账单</h2>
            <div class="text-xs text-slate-500">
              合计（计入）：{{ formatCents(bills.reduce((sum, b) => sum + b.amount_cents, 0)) }} 元
            </div>
          </div>

          <p v-if="bills.length === 0" class="text-sm text-slate-500 mb-4">暂无账单。</p>
          <div v-else class="overflow-x-auto mb-5">
            <table class="min-w-full text-sm">
              <thead>
                <tr class="text-left text-slate-500 border-b border-slate-200">
                  <th class="py-2 pr-4 font-medium">时间</th>
                  <th class="py-2 pr-4 font-medium">金额（元）</th>
                  <th class="py-2 pr-4 font-medium">付款人</th>
                  <th class="py-2 pr-4 font-medium">参与分摊</th>
                  <th class="py-2 pr-4 font-medium">备注</th>
                  <th v-if="isHost && !isSettled" class="py-2 pr-4 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="bill in bills" :key="bill.id" class="border-b border-slate-100">
                  <td class="py-2 pr-4 text-slate-600 whitespace-nowrap">
                    {{ formatDateTime(bill.created_at) }}
                  </td>
                  <td class="py-2 pr-4 font-medium text-slate-800">
                    {{ formatCents(bill.amount_cents) }}
                  </td>
                  <td class="py-2 pr-4 text-slate-700">
                    {{ bill.payer_username ?? usernameOf(bill.payer_id) }}
                  </td>
                  <td class="py-2 pr-4 text-slate-600">{{ participantNames(bill) }}</td>
                  <td class="py-2 pr-4 text-slate-500">{{ bill.note || '-' }}</td>
                  <td v-if="isHost && !isSettled" class="py-2 pr-4">
                    <button
                      type="button"
                      :disabled="busy"
                      class="text-rose-600 hover:underline disabled:opacity-60"
                      @click="removeBill(bill)"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <form
            v-if="canCreateBill"
            class="border-t border-slate-100 pt-4 space-y-3"
            @submit.prevent="submitBill"
          >
            <h3 class="text-sm font-semibold text-slate-700">新增账单</h3>
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">金额（元）</label>
                <input
                  v-model="amountInput"
                  type="text"
                  inputmode="decimal"
                  class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
                  placeholder="例如：100.00（最多两位小数）"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">付款人</label>
                <select
                  v-model.number="form.payerId"
                  class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
                >
                  <option :value="null">请选择（默认本人）</option>
                  <option v-for="member in joinedMembers" :key="member.id" :value="member.user_id">
                    {{ memberName(member) }}
                  </option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">参与分摊成员</label>
              <div class="flex flex-wrap gap-3">
                <label
                  v-for="member in joinedMembers"
                  :key="member.id"
                  class="inline-flex items-center gap-2 text-sm text-slate-700"
                >
                  <input
                    v-model="form.participantMemberIds"
                    type="checkbox"
                    :value="member.id"
                    class="rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  />
                  {{ memberName(member) }}
                </label>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">备注（可选）</label>
              <input
                v-model="form.note"
                type="text"
                class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
                placeholder="例如：晚餐 AA"
              />
            </div>

            <p v-if="formError" class="text-sm text-rose-600">{{ formError }}</p>

            <div class="flex justify-end">
              <button
                type="submit"
                :disabled="busy"
                class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-60"
              >
                {{ busy ? '提交中…' : '新增账单' }}
              </button>
            </div>
          </form>

          <p v-else-if="isSettled" class="border-t border-slate-100 pt-4 text-sm text-slate-500">
            房间已结算，账单不可新增或删除。
          </p>
          <p v-else class="border-t border-slate-100 pt-4 text-sm text-slate-500">
            仅已加入成员可新增账单。
          </p>
        </section>

        <!-- 结算区 -->
        <section class="rounded-2xl border border-slate-200 bg-white p-5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-lg font-semibold text-slate-800">结算</h2>
            <button
              v-if="isHost"
              type="button"
              :disabled="busy"
              class="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-60"
              @click="handleSettle"
            >
              {{ isSettled ? '重新查看结算结果' : '触发结算' }}
            </button>
          </div>

          <template v-if="settlement">
            <div class="mb-3 text-xs text-slate-500">
              结算时间：{{ formatDateTime(settlement.settled_at) }} · 总金额：{{
                formatCents(settlement.total_cents)
              }}
              元 ·
              <span :class="settlement.check.sum_share_equals_total ? 'text-emerald-600' : 'text-rose-600'">
                分摊校验：{{ settlement.check.sum_share_equals_total ? '通过' : '未通过' }}
              </span>
            </div>

            <div class="overflow-x-auto">
              <table class="min-w-full text-sm">
                <thead>
                  <tr class="text-left text-slate-500 border-b border-slate-200">
                    <th class="py-2 pr-4 font-medium">成员</th>
                    <th class="py-2 pr-4 font-medium">已付（元）</th>
                    <th class="py-2 pr-4 font-medium">应分摊（元）</th>
                    <th class="py-2 pr-4 font-medium">净额（元）</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in settlement.items" :key="item.member_id" class="border-b border-slate-100">
                    <td class="py-2 pr-4 text-slate-800">{{ item.username }}</td>
                    <td class="py-2 pr-4 text-slate-700">{{ formatCents(item.paid_cents) }}</td>
                    <td class="py-2 pr-4 text-slate-700">{{ formatCents(item.share_cents) }}</td>
                    <td
                      class="py-2 pr-4 font-medium"
                      :class="item.net_cents >= 0 ? 'text-emerald-600' : 'text-rose-600'"
                    >
                      {{ formatNet(item.net_cents) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="mt-2 text-xs text-slate-500">净额为正表示应收，为负表示应付。</p>
          </template>
          <p v-else class="text-sm text-slate-500">尚未结算。</p>
        </section>
      </template>
    </main>
  </div>
</template>
