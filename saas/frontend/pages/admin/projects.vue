<script setup lang="ts">
definePageMeta({ middleware: 'admin' })

interface User {
  id: number; email: string; name: string; role: string
  phone1: string; phone2: string
  monthlyPrice: number | null; monthlyCurrency: string
  billingCompany: string
  defaultCurrency: string; defaultPrice: number
}
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

// 테넌트(프로젝트)별 LLM 설정
const llmOpen = ref<Set<number>>(new Set())
const llmLoading = ref<Record<number, boolean>>({})
const llmSaving = ref<Record<number, boolean>>({})
const llmData = ref<Record<number, any>>({})
const llmDrafts = ref<Record<number, any>>({})
const llmTesting = ref<Record<number, boolean>>({})
const llmTestResult = ref<Record<number, { ok: boolean; message: string }>>({})

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

// ── 사용자별 결제 금액/연락처 관리 (엔터프라이즈 요금 설정) ──
const payingFor = ref<number | null>(null)   // 편집 중인 userId
const payForm = ref({ phone1: '', phone2: '', monthlyPrice: '', monthlyCurrency: '' })
const paySaving = ref(false)
const payMessage = ref<Record<number, string>>({})

function fmtPrice(amount: number, currency: string): string {
  if (currency === 'KRW') return `${Math.round(amount).toLocaleString()}원`
  if (currency === 'USD') return `$${amount}`
  return `${amount} ${currency}`
}

function userPriceLabel(u: User): string {
  if (u.monthlyPrice !== null && u.monthlyPrice !== undefined) {
    return `${fmtPrice(u.monthlyPrice, u.monthlyCurrency)} (엔터프라이즈)`
  }
  return `${fmtPrice(u.defaultPrice, u.defaultCurrency)} (기본)`
}

function openPaying(u: User) {
  payingFor.value = payingFor.value === u.id ? null : u.id
  payMessage.value = {}
  payForm.value = {
    phone1: u.phone1 || '',
    phone2: u.phone2 || '',
    monthlyPrice: u.monthlyPrice !== null ? String(u.monthlyPrice) : '',
    monthlyCurrency: u.monthlyCurrency || u.defaultCurrency,
  }
}

async function savePaying(u: User) {
  paySaving.value = true
  payMessage.value = { ...payMessage.value, [u.id]: '' }
  try {
    const raw = (payForm.value.monthlyPrice || '').trim()
    await useApi(`/api/admin/users/${u.id}/`, {
      method: 'PATCH',
      body: {
        phone1: payForm.value.phone1,
        phone2: payForm.value.phone2,
        // 빈 값 → 기본 요금으로 복귀, 숫자 → 엔터프라이즈 금액
        monthlyPrice: raw === '' ? null : Number(raw),
        monthlyCurrency: payForm.value.monthlyCurrency,
      },
    })
    payMessage.value = { ...payMessage.value, [u.id]: '저장 완료' }
    await loadUsers()
  } catch (e: any) {
    payMessage.value = { ...payMessage.value, [u.id]: e?.data?.detail || '저장에 실패했습니다.' }
  } finally {
    paySaving.value = false
  }
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

// ── 테넌트(프로젝트)별 Gemini 설정 ─────────────────────────
function toggleLlm(p: Project) {
  const s = new Set(llmOpen.value)
  if (s.has(p.id)) {
    s.delete(p.id)
  } else {
    s.add(p.id)
    loadLlm(p)
  }
  llmOpen.value = s
}

async function loadLlm(p: Project) {
  llmLoading.value[p.id] = true
  try {
    const res = await useApi(`/api/admin/projects/${p.id}/llm/`)
    llmData.value[p.id] = res
    llmDrafts.value[p.id] = {
      geminiApiKey: res.geminiApiKey || '',
      geminiModel: res.geminiModel || '',
    }
  } catch (e: any) {
    message.value = e?.data?.detail || 'LLM 설정을 불러오지 못했습니다.'
  } finally {
    llmLoading.value[p.id] = false
  }
}

async function resetLlm(p: Project) {
  if (!confirm(`'${p.name}' 프로젝트의 LLM 설정을 초기화해 전역(.env) 값을 사용하도록 되돌리시겠습니까?`)) return
  llmSaving.value[p.id] = true
  message.value = ''
  try {
    await useApi(`/api/admin/projects/${p.id}/llm/`, {
      method: 'PATCH',
      body: {
        geminiApiKey: '',
        geminiModel: '',
      },
    })
    message.value = `'${p.name}' LLM 설정이 전역 기본값으로 초기화되었습니다.`
    await loadLlm(p)
  } catch (e: any) {
    message.value = e?.data?.detail || 'LLM 설정 초기화에 실패했습니다.'
  } finally {
    llmSaving.value[p.id] = false
  }
}

async function testLlm(p: Project) {
  llmTesting.value[p.id] = true
  llmTestResult.value[p.id] = { ok: false, message: '테스트 중...' }
  try {
    const draft = llmDrafts.value[p.id] || {}
    const res = await useApi(`/api/admin/projects/${p.id}/llm/test/`, {
      method: 'POST',
      body: {
        geminiApiKey: (draft.geminiApiKey || '').trim(),
        geminiModel: (draft.geminiModel || '').trim(),
      },
    })
    llmTestResult.value[p.id] = {
      ok: true,
      message: `연결 성공 (${res.model}) — 응답: ${res.reply} (적용됨)`,
    }
    // 테스트 성공 시 적용되었으므로 저장된 값 갱신
    await loadLlm(p)
  } catch (e: any) {
    llmTestResult.value[p.id] = {
      ok: false,
      message: e?.data?.error || e?.data?.detail || '테스트에 실패했습니다.',
    }
  } finally {
    llmTesting.value[p.id] = false
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
        <a href="/admin/profile" class="btn-link">⚙️ 관리자 프로필</a>
        <button class="btn" @click="loadUsers">새로고침</button>
      </div>
    </header>

    <!-- 계정 선택 -->
    <div class="user-select">
      <label class="field-label">계정 선택</label>
      <select v-model="selectedUserId" class="user-select-box" @change="selectUser">
        <option value="" disabled>계정을 선택하세요</option>
        <option v-for="u in users" :key="u.id" :value="u.id">
          {{ u.email }} {{ u.role === 'admin' ? '(관리자)' : '' }} — {{ userPriceLabel(u) }}
        </option>
      </select>

      <!-- 사용자별 요금/연락처 관리 -->
      <details class="pay-details">
        <summary class="pay-summary">💰 사용자별 결제 금액 / 연락처 설정</summary>
        <div class="pay-list">
          <div v-for="u in users" :key="u.id" class="pay-item">
            <div class="pay-row">
              <span class="pay-email">{{ u.email }}{{ u.role === 'admin' ? ' (관리자)' : '' }}</span>
              <span class="pay-price" :class="{ enterprise: u.monthlyPrice !== null }">{{ userPriceLabel(u) }}</span>
              <span class="pay-phone muted">{{ [u.phone1, u.phone2].filter(Boolean).join(' · ') || '연락처 없음' }}</span>
              <button class="btn" @click="openPaying(u)">{{ payingFor === u.id ? '닫기' : '수정' }}</button>
            </div>

            <div v-if="payingFor === u.id" class="pay-form">
              <div class="pay-form-grid">
                <label class="field-label">전화번호 1
                  <input v-model="payForm.phone1" placeholder="02-888-9999" />
                </label>
                <label class="field-label">전화번호 2
                  <input v-model="payForm.phone2" placeholder="010-1234-5678" />
                </label>
                <label class="field-label">월 결제 금액 (비우면 기본 요금)
                  <div class="price-input-row">
                    <input v-model="payForm.monthlyPrice" type="number" min="0" step="0.01" :placeholder="String(u.defaultPrice)" />
                    <select v-model="payForm.monthlyCurrency" class="cur-select">
                      <option value="KRW">KRW(원)</option>
                      <option value="USD">USD($)</option>
                    </select>
                  </div>
                </label>
              </div>
              <p class="pay-hint">기본 요금: {{ fmtPrice(u.defaultPrice, u.defaultCurrency) }} / 월 — 숫자를 입력하면 엔터프라이즈 요금이 적용됩니다.</p>
              <div class="pay-actions">
                <span v-if="payMessage[u.id]" class="msg-line">{{ payMessage[u.id] }}</span>
                <button class="btn primary" :disabled="paySaving" @click="savePaying(u)">
                  {{ paySaving ? '저장 중...' : '저장' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </details>
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
            <button class="btn" @click="toggleLlm(p)">⚙ LLM 설정</button>
            <button class="btn danger" @click="removeProject(p)">삭제</button>
          </div>

          <!-- 테넌트별 Gemini 설정 패널 -->
          <div v-if="llmOpen.has(p.id)" class="llm-panel">
            <div v-if="llmLoading[p.id]" class="muted">LLM 설정 불러오는 중...</div>
            <template v-else-if="llmData[p.id]">
              <div class="llm-panel-head">
                <h3>LLM 설정 — {{ p.name }}</h3>
                <span class="muted">비워두면 전역(.env) 값을 사용합니다. (OpenRouter는 .env 로만 관리)</span>
              </div>
              <div class="llm-grid">
                <div class="llm-field">
                  <label class="field-label">Gemini API Key</label>
                  <input v-model="llmDrafts[p.id].geminiApiKey" type="password" placeholder="전역 값 사용" class="llm-input" />
                </div>
                <div class="llm-field">
                  <label class="field-label">Gemini 모델</label>
                  <input v-model="llmDrafts[p.id].geminiModel" :placeholder="'기본: ' + (llmData[p.id]?.defaults?.geminiModel || '')" class="llm-input" />
                </div>
                <div class="llm-field">
                  <label class="field-label">Gemini 키 테스트 후 적용</label>
                  <div class="llm-test-row">
                    <button class="btn primary" :disabled="llmTesting[p.id]" @click="testLlm(p)">
                      {{ llmTesting[p.id] ? '테스트 중...' : '🔌 테스트 후 적용' }}
                    </button>
                    <span v-if="llmTestResult[p.id]" class="llm-test-result" :class="llmTestResult[p.id].ok ? 'ok' : 'fail'">
                      {{ llmTestResult[p.id].message }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="llm-actions">
                <button class="btn" :disabled="llmSaving[p.id]" @click="resetLlm(p)">전역 값으로 초기화</button>
              </div>
            </template>
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
.btn-link { color: #0e7490; text-decoration: none; font-size: 13px; font-weight: 600; padding: 6px 10px; }
.field-label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.user-select { margin-bottom: 16px; }
.user-select-box { width: 100%; max-width: 400px; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }

/* 사용자별 결제 금액/연락처 관리 */
.pay-details { margin-top: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.pay-summary { padding: 10px 14px; cursor: pointer; font-size: 13px; font-weight: 600; color: #374151; }
.pay-summary:hover { background: #f9fafb; }
.pay-list { padding: 0 14px 14px; display: flex; flex-direction: column; gap: 8px; }
.pay-item { border: 1px solid #f3f4f6; border-radius: 6px; padding: 8px 10px; }
.pay-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pay-email { font-size: 13px; font-weight: 600; color: #111827; min-width: 180px; }
.pay-price { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #f0f9ff; color: #0e7490; }
.pay-price.enterprise { background: #fffbeb; color: #92400e; }
.pay-phone { font-size: 12px; }
.pay-form { margin-top: 10px; padding: 10px; background: #f9fafb; border-radius: 6px; }
.pay-form-grid { display: grid; grid-template-columns: 1fr 1fr 1.4fr; gap: 10px; }
.pay-form-grid input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; width: 100%; }
.price-input-row { display: flex; gap: 6px; }
.price-input-row input { flex: 1; }
.cur-select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }
.pay-hint { margin: 8px 0 0; font-size: 11px; color: #9ca3af; }
.pay-actions { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 8px; }
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

/* 테넌트별 LLM 설정 */
.llm-panel { border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; background: #fafafa; padding: 14px; margin-top: -10px; margin-bottom: 10px; }
.llm-panel-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.llm-panel-head h3 { margin: 0; font-size: 15px; color: #111827; }
.llm-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
.llm-field { display: flex; flex-direction: column; gap: 4px; }
.llm-input { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; font-family: inherit; }
.llm-test-row { display: flex; align-items: center; gap: 10px; }
.llm-test-result { font-size: 12px; word-break: break-all; }
.llm-test-result.ok { color: #047857; }
.llm-test-result.fail { color: #b91c1c; }
.llm-actions { display: flex; gap: 8px; margin-top: 14px; }

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