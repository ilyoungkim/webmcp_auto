<script setup lang="ts">
definePageMeta({ middleware: 'admin' })

interface User { id: number; email: string; name: string; role: string }
interface Project {
  id: number
  name: string
  url: string
  publicId: string
  userId: number
  userEmail: string
  domainTypeCode: string
  domainTypeName: string
  status: string
  enabled: boolean
}

const users = ref<User[]>([])
const projects = ref<Project[]>([])
const selectedUserId = ref<number | ''>('')
const loading = ref(false)
const filter = ref('')
const regenerating = ref<Record<number, boolean>>({})
const toggling = ref<Record<number, boolean>>({})
const message = ref('')

// 고객센터 Q&A 상태
const supportItems = ref<any[]>([])
const supportPage = ref(1)
const supportTotalPages = ref(1)
const supportTotal = ref(0)
const supportLoading = ref(false)
const answerDrafts = ref<Record<number, string>>({})
const answering = ref<Record<number, boolean>>({})
const expandedSupport = ref<Set<number>>(new Set())

const STATUS_LABELS: Record<string, string> = {
  queued: '예약',
  crawling: '진행중',
  generating: '진행중',
  completed: '완료',
  failed: '실패',
}

async function loadUsers() {
  users.value = await useApi('/api/admin/users/')
}

async function load() {
  if (selectedUserId.value === '') {
    projects.value = []
    supportItems.value = []
    return
  }
  loading.value = true
  try {
    projects.value = await useApi(`/api/admin/projects/?user_id=${selectedUserId.value}`)
  } finally {
    loading.value = false
  }
  loadSupport(1)
}

function selectUser() {
  filter.value = ''
  message.value = ''
  load()
}

// ── 고객센터 Q&A ────────────────────────────────────────────
async function loadSupport(page = 1) {
  if (selectedUserId.value === '') return
  supportLoading.value = true
  try {
    const res: any = await useApi(`/api/admin/support/?user_id=${selectedUserId.value}&page=${page}`)
    supportItems.value = res.items || []
    supportPage.value = res.page || 1
    supportTotalPages.value = res.totalPages || 1
    supportTotal.value = res.total || 0
    // 답변대기 질문은 기본적으로 펼쳐서 바로 답변할 수 있게 한다
    const s = new Set<number>()
    for (const t of supportItems.value) {
      if (t.status === 'pending') s.add(t.id)
    }
    expandedSupport.value = s
  } finally {
    supportLoading.value = false
  }
}

function toggleSupport(id: number) {
  const s = new Set(expandedSupport.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expandedSupport.value = s
}

async function submitAnswer(t: any) {
  const answer = (answerDrafts.value[t.id] || '').trim()
  if (!answer) {
    message.value = '답변 내용을 입력해주세요.'
    return
  }
  answering.value[t.id] = true
  message.value = ''
  try {
    const res = await useApi(`/api/admin/support/${t.id}/answer/`, {
      method: 'POST',
      body: { answer },
    })
    t.answer = res.answer
    t.status = res.status
    answerDrafts.value[t.id] = ''
    message.value = '답변이 등록되었습니다.'
  } catch (e: any) {
    message.value = e?.data?.detail || '답변 등록에 실패했습니다.'
  } finally {
    answering.value[t.id] = false
  }
}

function fmtSupportTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ko-KR', { hour12: false })
}

const filtered = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return projects.value
  return projects.value.filter(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      p.url.toLowerCase().includes(q) ||
      p.publicId.toLowerCase().includes(q),
  )
})

async function regenerate(p: Project) {
  if (!confirm(`'${p.name}' 프로젝트의 Q&A를 재생성하시겠습니까?`)) return
  message.value = ''
  regenerating.value[p.id] = true
  try {
    const res = await useApi(`/api/admin/projects/${p.id}/regenerate/`, { method: 'POST' })
    message.value = `'${p.name}' Q&A 재생성 완료 (${res.count ?? ''}건)`
  } catch (e: any) {
    message.value = e?.data?.detail || '재생성에 실패했습니다.'
  } finally {
    regenerating.value[p.id] = false
  }
}

async function toggleEnabled(p: Project) {
  const action = p.enabled ? '사용중지' : '사용재개'
  if (!confirm(`'${p.name}' 프로젝트를 ${action}하시겠습니까?`)) return
  message.value = ''
  toggling.value[p.id] = true
  try {
    const res = await useApi(`/api/admin/projects/${p.id}/toggle/`, { method: 'POST' })
    p.enabled = res.enabled
    message.value = `'${p.name}' ${res.enabled ? '사용재개' : '사용중지'} 완료`
  } catch (e: any) {
    message.value = e?.data?.detail || '상태 변경에 실패했습니다.'
  } finally {
    toggling.value[p.id] = false
  }
}

async function removeProject(p: Project) {
  if (!confirm(`'${p.name}' 프로젝트를 삭제하시겠습니까?\n삭제된 프로젝트는 복구할 수 없습니다.`)) return
  message.value = ''
  try {
    await useApi(`/api/admin/projects/${p.id}/`, { method: 'DELETE' })
    message.value = `'${p.name}' 삭제 완료`
    await load()
  } catch (e: any) {
    message.value = e?.data?.detail || '삭제에 실패했습니다.'
  }
}

onMounted(loadUsers)
</script>

<template>
  <main class="wrap">
    <header class="head">
      <NuxtLink to="/dashboard" class="back-link">&larr; 대시보드</NuxtLink>
      <h1>프로젝트 관리</h1>
      <div class="filters">
        <button class="btn" @click="loadUsers">새로고침</button>
      </div>
    </header>

    <!-- 계정 선택 -->
    <div class="user-select">
      <label class="field-label">계정 선택</label>
      <select v-model="selectedUserId" class="user-select-box" @change="selectUser">
        <option value="" disabled>계정을 선택하세요</option>
        <option v-for="u in users" :key="u.id" :value="u.id">
          {{ u.email }} {{ u.role === 'admin' ? '(관리자)' : '' }}
        </option>
      </select>
    </div>

    <template v-if="selectedUserId !== ''">
      <div class="list-bar">
        <span class="muted">선택한 계정의 프로젝트 {{ projects.length }}개</span>
        <input v-model="filter" class="search" placeholder="이름 / URL 검색" />
      </div>

      <p v-if="message" class="msg-line">{{ message }}</p>
      <p v-if="loading" class="muted">불러오는 중...</p>
      <p v-else-if="filtered.length === 0" class="muted">이 계정의 프로젝트가 없습니다.</p>

      <div v-else class="project-list">
        <div v-for="p in filtered" :key="p.id" class="project-card" :class="{ disabled: !p.enabled }">
          <div class="project-info">
            <span class="project-name">
              {{ p.name }}
              <span v-if="!p.enabled" class="badge stopped">사용중지</span>
            </span>
            <span class="project-url">{{ p.url }}</span>
            <span class="project-meta">
              <span class="badge">{{ p.domainTypeName || p.domainTypeCode }}</span>
              <span class="badge" :class="p.status">{{ STATUS_LABELS[p.status] || p.status }}</span>
            </span>
          </div>
          <div class="project-actions">
            <button class="btn primary" :disabled="regenerating[p.id]" @click="regenerate(p)">
              {{ regenerating[p.id] ? '재생성 중...' : 'Q&A 재생성' }}
            </button>
            <button class="btn" :disabled="toggling[p.id]" @click="toggleEnabled(p)">
              {{ toggling[p.id] ? '처리 중...' : (p.enabled ? '사용중지' : '사용재개') }}
            </button>
            <button class="btn danger" @click="removeProject(p)">삭제</button>
          </div>
        </div>
      </div>

      <!-- 고객센터 Q&A 게시판 -->
      <section class="support-section">
        <h2>고객센터 Q&A ({{ supportTotal }}건)</h2>
        <p class="note">이 계정의 사용자가 올린 질문에 답변을 등록할 수 있습니다.</p>

        <div v-if="supportLoading" class="muted">불러오는 중...</div>
        <div v-else-if="supportItems.length === 0" class="muted">등록된 Q&A가 없습니다.</div>
        <div v-else class="support-list">
          <div v-for="t in supportItems" :key="t.id" class="support-item" :class="t.status">
            <div class="support-head" @click="toggleSupport(t.id)">
              <span class="support-badge" :class="t.status">{{ t.status === 'answered' ? '답변완료' : '답변대기' }}</span>
              <span class="support-project">{{ t.projectName }}</span>
              <span class="support-question">{{ t.question }}</span>
              <span class="support-time">{{ fmtSupportTime(t.createdAt) }}</span>
              <span v-if="t.status === 'pending'" class="support-answer-hint">✏️ 답변하기</span>
            </div>

            <div v-if="expandedSupport.has(t.id)" class="support-detail">
              <div class="support-q-full">
                <span class="support-label">Q.</span>
                <p>{{ t.question }}</p>
              </div>

              <div v-if="t.answer" class="support-a-full">
                <span class="support-label">A.</span>
                <div class="support-a-body">
                  <p>{{ t.answer }}</p>
                  <span v-if="t.answeredAt" class="support-time">{{ fmtSupportTime(t.answeredAt) }}</span>
                </div>
              </div>

              <div class="support-answer-form">
                <textarea
                  v-model="answerDrafts[t.id]"
                  rows="3"
                  placeholder="답변 내용을 입력하세요"
                ></textarea>
                <div class="support-answer-actions">
                  <button class="btn primary" :disabled="answering[t.id]" @click="submitAnswer(t)">
                    {{ answering[t.id] ? '등록 중...' : (t.answer ? '답변 수정' : '답변 등록') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 페이지네이션 (10개/페이지) -->
        <div v-if="supportTotalPages > 1" class="pagination">
          <button class="page-btn" :disabled="supportPage <= 1" @click="loadSupport(supportPage - 1)">← 이전</button>
          <button
            v-for="p in supportTotalPages" :key="p"
            class="page-btn" :class="{ active: p === supportPage }"
            @click="loadSupport(p)"
          >{{ p }}</button>
          <button class="page-btn" :disabled="supportPage >= supportTotalPages" @click="loadSupport(supportPage + 1)">다음 →</button>
        </div>
      </section>
    </template>
    <p v-else class="muted hint">계정을 선택하면 해당 계정에서 만든 프로젝트 목록이 표시됩니다.</p>
  </main>
</template>

<style scoped>
.wrap { max-width: 860px; margin: 40px auto; padding: 0 24px; }
.head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.head h1 { margin: 0; font-size: 22px; flex: 1; }
.back-link { color: #0e7490; text-decoration: none; font-size: 13px; }
.filters { display: flex; gap: 8px; align-items: center; }
.field-label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.user-select { margin-bottom: 16px; }
.user-select-box { width: 100%; max-width: 400px; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.list-bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }
.search { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; min-width: 200px; }
.btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #111827; cursor: pointer; font-size: 13px; white-space: nowrap; }
.btn.primary { background: #0e7490; color: #fff; border-color: #0e7490; }
.btn:disabled { opacity: 0.5; cursor: default; }
.muted { color: #6b7280; font-size: 13px; }
.hint { margin-top: 12px; }
.msg-line { color: #047857; font-size: 13px; }

.project-list { display: flex; flex-direction: column; gap: 10px; }
.project-card { display: flex; justify-content: space-between; align-items: center; gap: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; padding: 12px 14px; }
.project-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.project-name { font-size: 15px; font-weight: 600; color: #111827; }
.project-url { font-size: 12px; color: #6b7280; word-break: break-all; }
.project-meta { display: flex; gap: 6px; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #f0f9ff; color: #0e7490; }
.badge.completed { background: #ecfdf5; color: #047857; }
.badge.failed { background: #fef2f2; color: #b91c1c; }
.badge.stopped { background: #f3f4f6; color: #6b7280; }
.project-actions { flex-shrink: 0; display: flex; gap: 6px; align-items: center; }
.btn.danger { color: #b91c1c; border-color: #fca5a5; }
.project-card.disabled { background: #f9fafb; opacity: 0.75; }
.project-card.disabled .project-name { color: #6b7280; }

/* 고객센터 Q&A 게시판 */
.support-section { margin-top: 32px; padding-top: 24px; border-top: 2px solid #e5e7eb; }
.support-section h2 { font-size: 18px; margin: 0 0 6px; }
.support-section .note { margin: 0 0 12px; color: #6b7280; font-size: 12px; }
.support-list { display: flex; flex-direction: column; gap: 10px; }
.support-item { border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; overflow: hidden; }
.support-item.answered { border-left: 4px solid #059669; }
.support-item.pending { border-left: 4px solid #d97706; }
.support-head { display: flex; align-items: center; gap: 10px; padding: 12px 14px; cursor: pointer; }
.support-head:hover { background: #f9fafb; }
.support-badge { flex-shrink: 0; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.support-badge.answered { background: #d1fae5; color: #065f46; }
.support-badge.pending { background: #fef3c7; color: #92400e; }
.support-project { flex-shrink: 0; font-size: 12px; font-weight: 600; color: #0e7490; }
.support-question { flex: 1; font-size: 13px; color: #111827; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.support-time { flex-shrink: 0; font-size: 11px; color: #9ca3af; }
.support-answer-hint { flex-shrink: 0; font-size: 12px; font-weight: 700; color: #0e7490; background: #e0f2fe; padding: 3px 10px; border-radius: 999px; }
.support-detail { padding: 12px 14px; border-top: 1px solid #f3f4f6; background: #fafafa; }
.support-q-full, .support-a-full { display: flex; gap: 8px; margin-bottom: 10px; }
.support-label { flex-shrink: 0; font-weight: 700; color: #0e7490; font-size: 14px; }
.support-q-full p, .support-a-body p { margin: 0; font-size: 13px; color: #374151; white-space: pre-wrap; word-break: break-all; }
.support-a-body { flex: 1; }
.support-answer-form textarea { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 13px; font-family: inherit; resize: vertical; }
.support-answer-actions { display: flex; justify-content: flex-end; margin-top: 8px; }

/* 페이지네이션 */
.pagination { display: flex; gap: 6px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
.page-btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.page-btn.active { background: #0e7490; color: #fff; border-color: #0e7490; }
.page-btn:disabled { opacity: 0.5; cursor: default; }
</style>