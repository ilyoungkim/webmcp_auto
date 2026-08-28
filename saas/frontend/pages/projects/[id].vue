<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
interface SitemapItem {
  url: string
  title?: string
}

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const project = ref<any>(null)
const qna = ref<any[]>([])
const snippet = ref('')
const editing = ref(false)
const editForm = ref({ name: '', url: '', domainTypeCode: '', theme: 'blue_sky' })
const saving = ref(false)
const domainTypes = ref<any[]>([])

// 위젯 테마 목록 (백엔드 core/themes.py 와 동일)
const themes = [
  { code: 'blue_sky', label: 'Blue Sky', primary: '#0284c7', bg: '#f0f9ff' },
  { code: 'red_orange', label: 'Red Orange', primary: '#dc2626', bg: '#fff7ed' },
  { code: 'white_snow', label: 'White Snow', primary: '#334155', bg: '#f8fafc' },
  { code: 'banana_pink', label: 'Banana Pink', primary: '#db2777', bg: '#fdf2f8' },
  { code: 'black_neon', label: 'Black Neon', primary: '#22d3ee', bg: '#0b0f19' },
]

// 빠른메뉴 질문 편집 상태
const menuItems = ref<any[]>([])
const menuLoading = ref(false)
const menuSaving = ref(false)
const menuError = ref('')
const menuSuccess = ref('')
const menuEdited = ref(false) // 1회 편집 완료 여부 (잠금)

// 재생성 소스 선택 모달 상태
const rerunModalOpen = ref(false)
const sitemapItems = ref<SitemapItem[]>([])
const selectedUrls = ref<string[]>([])
const loadingUrls = ref(false)
const submittingRerun = ref(false)
let timer: any

// 고객센터 Q&A 게시판 상태
const supportItems = ref<any[]>([])
const supportPage = ref(1)
const supportTotalPages = ref(1)
const supportTotal = ref(0)
const supportLoading = ref(false)
const supportQuestion = ref('')
const supportSubmitting = ref(false)
const supportError = ref('')
const supportSuccess = ref('')

const STATUS_LABELS: Record<string, string> = {
  queued: '예약',
  crawling: '진행중',
  generating: '진행중',
  completed: '완료',
  failed: '실패',
}

function statusLabel(s: string): string {
  return STATUS_LABELS[s] || s
}

async function load() {
  project.value = await useApi(`/api/projects/${id}/`)
  snippet.value = project.value.installSnippet
  if (project.value.status === 'completed') {
    clearInterval(timer)
    qna.value = await useApi(`/api/projects/${id}/qna/`)
    loadMenus()
  }
}

async function loadMenus() {
  menuLoading.value = true
  menuError.value = ''
  try {
    const res: any = await useApi(`/api/projects/${id}/menus/`)
    menuItems.value = res.menus || []
    menuEdited.value = !!res.edited
  } catch (e: any) {
    menuError.value = e?.data?.detail || '빠른메뉴를 불러오지 못했습니다.'
  } finally {
    menuLoading.value = false
  }
}

async function regenerateMenus() {
  menuSaving.value = true
  menuError.value = ''
  menuSuccess.value = ''
  try {
    const res: any = await useApi(`/api/projects/${id}/menus/regenerate/`, {
      method: 'POST',
      body: { menus: menuItems.value.map(m => ({ label: m.label, question: m.question })) },
    })
    menuItems.value = res.menus || menuItems.value
    qna.value = await useApi(`/api/projects/${id}/qna/`)
    menuEdited.value = true // 1회 편집 완료 → 잠금
    menuSuccess.value = '빠른메뉴 질문/답변이 재생성되었습니다. (편집은 1회만 가능합니다)'
  } catch (e: any) {
    menuError.value = e?.data?.detail || '재생성에 실패했습니다.'
  } finally {
    menuSaving.value = false
  }
}

function startEdit() {
  editForm.value = {
    name: project.value.name,
    url: project.value.url,
    domainTypeCode: project.value.domainTypeCode,
    theme: project.value.theme || 'blue_sky',
  }
  editing.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    // 이름/URL은 변경 불가 — 도메인 유형과 테마만 전송
    project.value = await useApi(`/api/projects/${id}/`, {
      method: 'PATCH',
      body: {
        domainTypeCode: editForm.value.domainTypeCode,
        theme: editForm.value.theme,
      },
    })
    snippet.value = project.value.installSnippet
    editing.value = false
  } finally {
    saving.value = false
  }
}

async function openRerunModal() {
  rerunModalOpen.value = true
  loadingUrls.value = true
  sitemapItems.value = []
  selectedUrls.value = []
  try {
    const res: any = await useApi(`/api/projects/${id}/sitemap-urls/`)
    if (res.items && Array.isArray(res.items)) {
      sitemapItems.value = res.items
    } else if (res.urls && Array.isArray(res.urls)) {
      sitemapItems.value = res.urls.map((u: string) => ({ url: u, title: '' }))
    } else {
      sitemapItems.value = [{ url: project.value?.url, title: '' }]
    }
    selectedUrls.value = sitemapItems.value.slice(0, 10).map(item => item.url)
  } catch {
    sitemapItems.value = [{ url: project.value?.url, title: '' }]
    selectedUrls.value = [project.value?.url]
  } finally {
    loadingUrls.value = false
  }
}

function toggleUrl(u: string) {
  const idx = selectedUrls.value.indexOf(u)
  if (idx >= 0) {
    selectedUrls.value.splice(idx, 1)
  } else {
    if (selectedUrls.value.length >= 10) {
      alert('최대 10개까지만 선택할 수 있습니다.')
      return
    }
    selectedUrls.value.push(u)
  }
}

function selectAllTop10() {
  selectedUrls.value = sitemapItems.value.slice(0, 10).map(item => item.url)
}

function clearSelection() {
  selectedUrls.value = []
}

async function submitRerun() {
  if (selectedUrls.value.length === 0) {
    alert('최소 1개 이상의 페이지를 선택해주세요.')
    return
  }
  submittingRerun.value = true
  try {
    await useApi(`/api/projects/${id}/rerun/`, {
      method: 'POST',
      body: { selectedUrls: selectedUrls.value },
    })
    rerunModalOpen.value = false
    await load()
    timer = setInterval(load, 1500)
  } finally {
    submittingRerun.value = false
  }
}

async function removeProject() {
  if (!confirm(`'${project.value?.name}' 프로젝트를 삭제할까요?`)) return
  await useApi(`/api/projects/${id}/`, { method: 'DELETE' })
  router.push('/dashboard')
}

// ── 고객센터 Q&A 게시판 ─────────────────────────────────────
async function loadSupport(page = 1) {
  supportLoading.value = true
  supportError.value = ''
  try {
    const res: any = await useApi(`/api/projects/${id}/support/?page=${page}`)
    supportItems.value = res.items || []
    supportPage.value = res.page || 1
    supportTotalPages.value = res.totalPages || 1
    supportTotal.value = res.total || 0
  } catch (e: any) {
    supportError.value = e?.data?.detail || 'Q&A 목록을 불러오지 못했습니다.'
  } finally {
    supportLoading.value = false
  }
}

async function submitSupport() {
  const q = supportQuestion.value.trim()
  if (!q) {
    supportError.value = '질문 내용을 입력해주세요.'
    return
  }
  supportSubmitting.value = true
  supportError.value = ''
  supportSuccess.value = ''
  try {
    await useApi(`/api/projects/${id}/support/`, {
      method: 'POST',
      body: { question: q },
    })
    supportQuestion.value = ''
    supportSuccess.value = '질문이 등록되었습니다. 관리자가 답변을 달면 확인할 수 있습니다.'
    await loadSupport(1)
  } catch (e: any) {
    supportError.value = e?.data?.detail || '질문 등록에 실패했습니다.'
  } finally {
    supportSubmitting.value = false
  }
}

function supportPageBtn(p: number) {
  loadSupport(p)
}

function fmtSupportTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ko-KR', { hour12: false })
}

onMounted(async () => {
  domainTypes.value = await useApi('/api/domain-types/')
  load()
  loadSupport()
  timer = setInterval(load, 1500)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <main v-if="project" class="wrap">
    <header>
      <div class="title-area">
        <NuxtLink to="/dashboard" class="back-link">&larr; 목록으로</NuxtLink>
        <h1>{{ project.name }}</h1>
      </div>
      <div class="actions">
        <span class="badge" :class="project.status">{{ statusLabel(project.status) }} {{ project.progress }}%</span>
        <span v-if="project.status === 'failed'" class="fail-msg">재생성하거나 문의 02-888-9999로 연락 주세요.</span>
        <button class="btn" @click="openRerunModal">
          재생성
        </button>
        <button class="btn" @click="startEdit">수정</button>
        <button class="btn danger" @click="removeProject">삭제</button>
      </div>
    </header>

    <p class="plan-note">📌 내 프로젝트는 <b>최대 5개</b>까지 생성할 수 있습니다.</p>

    <section v-if="editing" class="edit-panel">
      <p class="note">이름과 URL은 변경할 수 없습니다. 도메인 유형과 위젯 테마만 변경할 수 있습니다.</p>
      <label>도메인 유형
        <select v-model="editForm.domainTypeCode">
          <option v-for="dt in domainTypes" :key="dt.code" :value="dt.code">{{ dt.name }}</option>
        </select>
      </label>
      <label class="theme-edit-label">위젯 테마
        <div class="theme-cards">
          <button
            v-for="t in themes" :key="t.code" type="button"
            class="theme-card" :class="{ active: editForm.theme === t.code }"
            :style="{ '--primary': t.primary, '--bg': t.bg }"
            @click="editForm.theme = t.code"
          >
            <span class="theme-swatch"></span>
            <b>{{ t.label }}</b>
          </button>
        </div>
      </label>
      <p class="note">도메인 유형 변경 후 <b>'재생성'</b> 버튼을 누르면 새 사이트맵 기반으로 다시 수집합니다. 테마는 저장 즉시 위젯에 반영됩니다.</p>
      <div class="edit-actions">
        <button class="btn" @click="editing = false">취소</button>
        <button class="btn primary" :disabled="saving" @click="saveEdit">{{ saving ? '저장 중...' : '저장' }}</button>
      </div>
    </section>

    <section v-if="project.status === 'failed'" class="err">{{ project.errorMessage }}</section>

    <section v-if="project.status === 'completed'">
      <!-- 수집된 소스 정보 섹션 -->
      <h2>수집된 소스 정보 ({{ project.sourceUrls?.length || 0 }}개 페이지)</h2>
      <div class="source-card">
        <ul class="source-url-list">
          <li v-for="(u, idx) in project.sourceUrls" :key="idx">
            <span class="url-num">{{ idx + 1 }}.</span>
            <div class="source-content">
              <span v-if="u.title" class="source-title">{{ u.title }}</span>
              <a :href="u.url || u" target="_blank" rel="noopener noreferrer" class="source-link">{{ u.url || u }}</a>
            </div>
          </li>
        </ul>

        <!-- 실패한 페이지 안내 -->
        <div v-if="project.failedUrls?.length" class="failed-card">
          <h3>⚠️ 크롤링 실패 ({{ project.failedUrls.length }}개)</h3>
          <ul class="failed-list">
            <li v-for="(f, idx) in project.failedUrls" :key="'f' + idx">
              <span class="failed-url">{{ f.url }}</span>
              <span class="failed-err">{{ f.error || '크롤링 실패' }}</span>
            </li>
          </ul>
          <p class="failed-note">실패한 페이지는 재생성 시 다시 시도됩니다. 지속적으로 실패하면 사이트 구조(JS 렌더링, 로그인 등)를 확인해 주세요.</p>
        </div>
      </div>

      <!-- 설치 및 사용 방법 (아코디언, 닫힌 상태) -->
      <details class="install-accordion">
        <summary>📦 설치 및 사용 방법</summary>
        <div class="install-body">
          <p class="note">아래 <b>5개 파일</b>을 홈페이지 서버에 업로드하고, 설치할 페이지의 <code>&lt;/body&gt;</code> 직전에 스크립트를 추가하면 AI 비서 위젯이 표시됩니다.</p>

          <h3>1단계: 파일 업로드 (호스팅 서버)</h3>
          <ol class="install-steps">
            <li><b>⬇ 다운로드</b> 버튼으로 <code>bundle.zip</code>을 받아 압축을 해제합니다.</li>
            <li>FTP/SFTP 또는 호스팅 파일 관리자로 홈페이지 루트(<code>public_html</code>, <code>www</code>, <code>html</code>)에 <b>5개 파일</b>을 모두 업로드합니다.</li>
            <li>업로드 후 브라우저에서 <code>https://도메인/webmcp-config.js</code>에 접근해 설정 내용이 보이는지 확인합니다.</li>
          </ol>

          <h3>2단계: HTML 편집 (위젯 삽입)</h3>
          <ol class="install-steps">
            <li>홈페이지 관리자 도구 또는 HTML 에디터로 해당 페이지의 HTML 소스를 엽니다.</li>
            <li><code>&lt;/body&gt;</code> 태그 <b>직전</b>에 아래 코드를 붙여넣습니다.</li>
          </ol>
          <pre><code>&lt;!-- WebMCP AI 위젯 --&gt;
&lt;script src="webmcp-config.js"&gt;&lt;/script&gt;
&lt;script src="webmcp.js"&gt;&lt;/script&gt;
&lt;link rel="stylesheet" href="widget.css" /&gt;
&lt;script src="widget.js"&gt;&lt;/script&gt;</code></pre>
          <p class="note">💡 파일을 하위 폴더(예: <code>/widget/</code>)에 업로드했다면 <code>src</code> 경로를 <code>widget/webmcp-config.js</code>처럼 해당 경로로 수정하세요.</p>

          <h3>3단계: 설정 변경 (선택)</h3>
          <ul class="install-steps">
            <li><code>webmcp-config.js</code>의 <code>window.WebMCPConfig</code> 값을 수정해 제목·색상·빠른메뉴 질문을 조정할 수 있습니다.</li>
            <li>수정 후 저장하면 새로고침 시 즉시 반영됩니다.</li>
          </ul>

          <h3>사용 방법</h3>
          <ul class="install-steps">
            <li>우하단 💬 버튼을 클릭해 채팅창을 엽니다.</li>
            <li>빠른 메뉴(퀵 질문) 버튼을 누르면 자동으로 질문이 입력됩니다.</li>
            <li>직접 질문을 입력해도 됩니다. 답변은 수집된 사이트 정보를 기반으로 생성됩니다.</li>
            <li>⚙️ 동작 방식에서 AI 비서의 안내 및 주의사항을 확인할 수 있습니다.</li>
          </ul>

          <div class="install-download">
            <a :href="`/api/projects/${id}/download/bundle.zip`" class="btn primary">⬇ 다운로드 (bundle.zip)</a>
          </div>
        </div>
      </details>

      <!-- 미리보기 버튼 -->
      <div class="action-buttons">
        <NuxtLink :to="`/preview/${id}`" class="btn primary">👁 미리보기</NuxtLink>
      </div>

      <h2>빠른메뉴 - 자동화된 질문 및 답변</h2>

      <details v-for="(q, i) in qna" :key="i" class="qna-item">
        <summary><span class="q-marker">Q:</span> <b>{{ q.menuLabel }}</b> — {{ q.question }}</summary>
        <pre>{{ q.answerMd }}</pre>
      </details>

      <!-- 빠른메뉴 질문 편집 (가장 아래, 아코디언) -->
      <details class="menu-edit-accordion">
        <summary>✏️ 빠른메뉴 질문 편집</summary>
        <div class="menu-edit-card">
          <p v-if="menuEdited" class="note locked-note">🔒 빠른메뉴 질문 편집은 <b>1회만</b> 가능합니다. 이미 편집이 완료되어 더 이상 수정할 수 없습니다.</p>
          <p v-else class="note">질문을 수정한 뒤 <b>'답변 재생성'</b>을 누르면, 이미 수집된 소스를 기반으로 답변이 다시 생성됩니다. (재크롤링 없음 · 편집은 1회만 가능)</p>

          <div v-if="menuLoading" class="menu-loading">빠른메뉴 불러오는 중...</div>

          <div v-else class="menu-edit-body">
            <div v-for="(m, i) in menuItems" :key="i" class="menu-edit-row">
              <label class="menu-label">{{ m.label }}</label>
              <input v-model="m.question" class="menu-question" placeholder="질문을 입력하세요" :disabled="menuEdited" />
            </div>

            <div class="menu-edit-actions">
              <button class="btn primary" :disabled="menuSaving || menuEdited" @click="regenerateMenus">
                {{ menuSaving ? '재생성 중...' : (menuEdited ? '편집 완료' : '답변 재생성') }}
              </button>
            </div>
            <p v-if="menuError" class="err">{{ menuError }}</p>
            <p v-if="menuSuccess" class="ok">{{ menuSuccess }}</p>
          </div>
        </div>
      </details>
    </section>

    <!-- 고객센터 Q&A 게시판 -->
    <section class="support-section">
      <h2>고객센터 Q&A</h2>
      <p class="note">궁금한 점을 질문해 주세요. 관리자가 답변을 등록하면 확인할 수 있습니다.</p>

      <!-- 질문 등록 폼 -->
      <div class="support-form">
        <textarea v-model="supportQuestion" rows="3" placeholder="질문 내용을 입력하세요 (2000자 이내)" maxlength="2000"></textarea>
        <div class="support-form-actions">
          <span class="support-count">{{ supportQuestion.length }}/2000</span>
          <button class="btn primary" :disabled="supportSubmitting" @click="submitSupport">
            {{ supportSubmitting ? '등록 중...' : '질문 등록' }}
          </button>
        </div>
        <p v-if="supportError" class="err">{{ supportError }}</p>
        <p v-if="supportSuccess" class="ok">{{ supportSuccess }}</p>
      </div>

      <!-- Q&A 목록 -->
      <div v-if="supportLoading" class="support-loading">불러오는 중...</div>
      <div v-else-if="supportItems.length === 0" class="support-empty">등록된 Q&A가 없습니다.</div>
      <div v-else class="support-list">
        <div v-for="t in supportItems" :key="t.id" class="support-item" :class="{ answered: t.status === 'answered' }">
          <div class="support-q">
            <span class="support-badge" :class="t.status">{{ t.status === 'answered' ? '답변완료' : '답변대기' }}</span>
            <span class="support-question">{{ t.question }}</span>
            <span class="support-time">{{ fmtSupportTime(t.createdAt) }}</span>
          </div>
          <div v-if="t.answer" class="support-a">
            <span class="support-a-label">A.</span>
            <div class="support-a-body">
              <p>{{ t.answer }}</p>
              <span v-if="t.answeredAt" class="support-time">{{ fmtSupportTime(t.answeredAt) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 페이지네이션 (10개/페이지) -->
      <div v-if="supportTotalPages > 1" class="pagination">
        <button class="page-btn" :disabled="supportPage <= 1" @click="supportPageBtn(supportPage - 1)">← 이전</button>
        <button
          v-for="p in supportTotalPages" :key="p"
          class="page-btn" :class="{ active: p === supportPage }"
          @click="supportPageBtn(p)"
        >{{ p }}</button>
        <button class="page-btn" :disabled="supportPage >= supportTotalPages" @click="supportPageBtn(supportPage + 1)">다음 →</button>
      </div>
    </section>

    <!-- 이용 약관 아코디언 -->
    <section class="terms-section">
      <details class="terms-accordion">
        <summary>📋 사용자 권리</summary>
        <div class="terms-body">
          <ul>
            <li>회원은 본 서비스에서 제공하는 AI 비서 위젯을 자신의 홈페이지에 설치·운영할 권리가 있습니다.</li>
            <li>회원은 생성된 프로젝트의 정보(이름, URL, 도메인 유형, 위젯 테마)를 확인하고, 도메인 유형과 위젯 테마를 변경할 수 있습니다.</li>
            <li>회원은 빠른메뉴 질문을 <b>1회</b> 편집할 수 있으며, 고객센터 Q&A를 통해 문의할 권리가 있습니다.</li>
            <li>회원은 언제든지 본 서비스 이용을 중단하고 프로젝트를 삭제할 수 있습니다.</li>
            <li>회원은 본인의 개인정보 열람·정정·삭제를 요청할 권리가 있습니다.</li>
          </ul>
        </div>
      </details>

      <details class="terms-accordion">
        <summary>⚠️ LLM 사용 주의사항</summary>
        <div class="terms-body">
          <ul>
            <li>AI 비서의 답변은 대규모 언어 모델(LLM)이 생성한 것으로, <b>사실과 다를 수 있으며</b> 의학적·법률적·재정적 조언으로 간주해서는 안 됩니다.</li>
            <li>중요한 결정(진료, 법률, 투자 등)은 반드시 전문가와 상담하시기 바랍니다.</li>
            <li>AI 답변은 수집된 홈페이지 정보를 기반으로 생성되며, 홈페이지에 없는 정보는 정확하지 않을 수 있습니다.</li>
            <li>AI가 생성한 답변으로 인한 손해에 대해 서비스 제공자는 책임을 지지 않습니다.</li>
            <li>AI 답변 품질은 사용량·모델 상태에 따라 달라질 수 있으며, 서비스는 이를 보장하지 않습니다.</li>
          </ul>
        </div>
      </details>

      <details class="terms-accordion">
        <summary>🔒 개인정보보호</summary>
        <div class="terms-body">
          <ul>
            <li>본 서비스는 회원의 이메일, 이름 등 최소한의 개인정보만 수집하며, 서비스 제공 목적으로만 사용합니다.</li>
            <li>회원의 홈페이지에서 수집된 콘텐츠는 AI 비서 답변 생성 목적으로만 사용됩니다.</li>
            <li>회원의 개인정보는 동의 없이 제3자에게 제공되지 않으며, 관련 법령에 따라 안전하게 보호됩니다.</li>
            <li>회원은 언제든지 개인정보 처리에 대한 문의 및 삭제를 요청할 수 있습니다.</li>
            <li>AI 채팅 과정에서 입력된 질문은 서비스 품질 개선을 위해 저장될 수 있습니다.</li>
          </ul>
        </div>
      </details>

      <details class="terms-accordion">
        <summary>✅ 프로그램 사용동의</summary>
        <div class="terms-body">
          <ul>
            <li>본 서비스(WebMCP AI 비서)를 사용함으로써 아래 내용에 동의한 것으로 간주됩니다.</li>
            <li>회원은 본 서비스의 위젯을 불법적이거나 부적절한 목적으로 사용해서는 안 됩니다.</li>
            <li>회원은 본 서비스의 소스코드·콘텐츠를 무단 복제·배포·수정할 수 없습니다.</li>
            <li>회원은 AI 비서를 통해 생성된 답변에 대해 책임을 지며, 이를 악용해서는 안 됩니다.</li>
            <li>서비스 제공자는 천재지변, 시스템 점검 등 불가항력적 사유로 서비스가 중단될 수 있습니다.</li>
            <li>본 약관은 서비스 정책 변경에 따라 사전 고지 후 변경될 수 있습니다.</li>
          </ul>
        </div>
      </details>
    </section>

    <!-- 재생성 소스 선택 모달 -->
    <div v-if="rerunModalOpen" class="modal-overlay" @click.self="rerunModalOpen = false">
      <div class="modal-card">
        <header class="modal-header">
          <h3>재생성 소스 페이지 선택</h3>
          <button class="close-btn" @click="rerunModalOpen = false">&times;</button>
        </header>

        <p class="modal-desc">
          <b>{{ project?.name }}</b> 사이트맵에서 검색된 <b>Root URL에 가장 가까운 상위 30개 URL</b> 중 크롤링할 페이지를 <b>최대 10개</b> 선택하세요.
        </p>

        <div v-if="loadingUrls" class="modal-loading">
          사이트맵에서 URL 목록을 가져오는 중...
        </div>

        <div v-else class="modal-body">
          <div class="select-bar">
            <span>선택됨: <b>{{ selectedUrls.length }}</b> / 10개</span>
            <div class="bar-actions">
              <button class="btn sm" @click="selectAllTop10">상위 10개 선택</button>
              <button class="btn sm" @click="clearSelection">전체 해제</button>
            </div>
          </div>

          <ul class="url-list">
            <li v-for="(item, idx) in sitemapItems" :key="idx" class="url-item" :class="{ selected: selectedUrls.includes(item.url) }" @click="toggleUrl(item.url)">
              <input type="checkbox" :checked="selectedUrls.includes(item.url)" @click.stop="toggleUrl(item.url)" />
              <span class="url-num">{{ idx + 1 }}</span>
              <div class="url-content">
                <span v-if="item.title" class="url-title">{{ item.title }}</span>
                <span class="url-text" :title="item.url">{{ item.url }}</span>
              </div>
            </li>
          </ul>
        </div>

        <footer class="modal-footer">
          <button class="btn" @click="rerunModalOpen = false">취소</button>
          <button class="btn primary" :disabled="submittingRerun || selectedUrls.length === 0" @click="submitRerun">
            {{ submittingRerun ? '요청 중...' : `선택한 ${selectedUrls.length}개로 재생성 시작` }}
          </button>
        </footer>
      </div>
    </div>
  </main>
</template>

<style>
.wrap { max-width: 720px; margin: 48px auto; padding: 0 24px; }
header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.title-area { display: flex; flex-direction: column; gap: 4px; }
.title-area h1 { margin: 0; }
.back-link { font-size: 13px; color: #6b7280; text-decoration: none; }
.back-link:hover { color: #111827; }
.actions { display: flex; gap: 8px; align-items: center; }
.badge { color: #0e7490; font-size: 13px; padding: 3px 10px; background: #f0f9ff; border-radius: 9999px; }
.badge.failed { color: #b91c1c; background: #fef2f2; }
.badge.completed { color: #047857; background: #ecfdf5; }
.fail-msg { color: #b91c1c; font-size: 13px; }
pre { background: #f3f4f6; padding: 12px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }
.err { color: #b91c1c; }
.btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #111827; cursor: pointer; font-size: 13px; }
.btn.sm { padding: 4px 8px; font-size: 12px; }
.btn.primary { background: #0e7490; color: #fff; border-color: #0e7490; }
.btn.danger { color: #b91c1c; border-color: #fca5a5; }
.btn:disabled { opacity: 0.5; cursor: default; }
.edit-panel { margin: 16px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; display: flex; flex-direction: column; gap: 10px; background: #fafafa; }
.edit-panel label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.edit-panel input, .edit-panel select { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; background: #fff; }
.edit-actions { display: flex; justify-content: flex-end; gap: 8px; }
.note { margin: 0; color: #6b7280; font-size: 12px; }

/* 테마 선택 (수정 폼) */
.theme-edit-label { gap: 8px !important; }
.theme-cards { display: flex; gap: 8px; flex-wrap: wrap; }
.theme-card { display: flex; align-items: center; gap: 6px; padding: 8px 12px; border: 2px solid #e5e7eb; border-radius: 8px; background: #fff; cursor: pointer; font-size: 12px; }
.theme-card.active { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 25%, transparent); }
.theme-swatch { width: 18px; height: 18px; border-radius: 50%; background: linear-gradient(135deg, var(--primary) 50%, var(--bg) 50%); border: 1px solid #e5e7eb; }

/* 수집된 소스 카드 */
.source-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; }
.source-url-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.source-url-list li { display: flex; gap: 8px; font-size: 13px; }
.source-content { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.source-title { font-weight: 600; color: #1f2937; font-family: inherit; }
.source-link { color: #0e7490; text-decoration: none; word-break: break-all; font-family: monospace; font-size: 12px; }
.source-link:hover { text-decoration: underline; }

/* 실패한 페이지 카드 */
.failed-card { margin-top: 14px; padding: 12px 14px; border: 1px solid #fca5a5; border-radius: 8px; background: #fef2f2; }
.failed-card h3 { margin: 0 0 8px; font-size: 13px; color: #b91c1c; }
.failed-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.failed-list li { display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
.failed-url { color: #b91c1c; font-family: monospace; word-break: break-all; }
.failed-err { color: #7f1d1d; font-size: 11px; }
.failed-note { margin: 8px 0 0; font-size: 11px; color: #7f1d1d; }

/* 설치 코드 아코디언 */
.install-accordion { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; background: #fafafa; }
.install-accordion summary { cursor: pointer; font-weight: 600; font-size: 14px; color: #111827; }
.install-body { margin-top: 12px; }
.install-body h3 { font-size: 13px; margin: 14px 0 6px; color: #374151; }
.install-steps { margin: 0; padding-left: 20px; font-size: 13px; color: #4b5563; line-height: 1.7; }
.install-steps code { background: #f3f4f6; padding: 1px 4px; border-radius: 4px; font-size: 12px; }
.install-download { display: flex; justify-content: center; margin-top: 16px; padding-top: 14px; border-top: 1px solid #e5e7eb; }
.install-download .btn { padding: 12px 24px; font-size: 14px; text-decoration: none; }

/* 미리보기 / 다운로드 버튼 */
.action-buttons { display: flex; gap: 8px; margin: 16px 0; }
.action-buttons .btn { padding: 10px 16px; font-size: 14px; text-decoration: none; }

/* Q&A */
.qna-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; background: #fff; }
.qna-item summary { cursor: pointer; font-size: 13px; color: #111827; list-style: none; }
.qna-item summary::-webkit-details-marker { display: none; }
.qna-item summary::marker { content: ''; }
.q-marker { font-weight: 700; color: #2563eb; margin-right: 4px; }

/* 빠른메뉴 질문 편집 */
.menu-edit-accordion { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin-top: 16px; background: #fafafa; }
.menu-edit-accordion summary { cursor: pointer; font-weight: 600; font-size: 14px; color: #111827; }
.menu-edit-card { margin-top: 10px; }
.menu-edit-card .note { margin: 0 0 10px; }
.menu-edit-card .locked-note { color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 8px 10px; }
.menu-loading { color: #6b7280; font-size: 13px; padding: 8px 0; }
.menu-edit-body { display: flex; flex-direction: column; gap: 8px; }
.menu-edit-row { display: flex; align-items: center; gap: 10px; }
.menu-label { font-size: 13px; font-weight: 600; color: #374151; width: 90px; flex-shrink: 0; }
.menu-question { flex: 1; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }
.menu-question:disabled { background: #f3f4f6; color: #6b7280; cursor: not-allowed; }
.menu-edit-actions { display: flex; justify-content: flex-end; margin-top: 6px; }
.ok { color: #047857; font-size: 13px; margin: 6px 0 0; }

/* 모달 스타일 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.modal-card { background: #fff; border-radius: 12px; width: 640px; max-width: 90vw; max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e5e7eb; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 600; }
.close-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #6b7280; }
.modal-desc { padding: 12px 20px 0 20px; font-size: 13px; color: #4b5563; margin: 0; }
.modal-loading { padding: 40px 20px; text-align: center; color: #6b7280; font-size: 14px; }
.modal-body { padding: 12px 20px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 8px; }
.select-bar { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding-bottom: 6px; border-bottom: 1px solid #f3f4f6; }
.bar-actions { display: flex; gap: 6px; }
.url-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; max-height: 560px; overflow-y: auto; }
.url-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border: 1px solid #f3f4f6; border-radius: 6px; cursor: pointer; font-size: 12px; }
.url-item:hover { background: #f9fafb; border-color: #e5e7eb; }
.url-item.selected { background: #f0f9ff; border-color: #bae6fd; }
.url-num { color: #9ca3af; font-size: 11px; width: 16px; text-align: right; }
.url-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.url-title { font-weight: 600; color: #1f2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.url-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: monospace; color: #6b7280; font-size: 11px; }
.modal-footer { padding: 12px 20px; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 8px; }

/* 고객센터 Q&A 게시판 */
.support-section { margin-top: 32px; padding-top: 24px; border-top: 2px solid #e5e7eb; }
.support-section h2 { font-size: 18px; margin: 0 0 6px; }

/* 프로젝트 생성 한도 안내 */
.plan-note { margin: 12px 0 0; padding: 10px 14px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; font-size: 13px; color: #0c4a6e; }
.plan-note b { color: #0369a1; }

/* 이용 약관 아코디언 */
.terms-section { margin-top: 40px; padding-top: 24px; border-top: 2px solid #e5e7eb; display: flex; flex-direction: column; gap: 10px; }
.terms-accordion { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; background: #fafafa; }
.terms-accordion summary { cursor: pointer; font-weight: 600; font-size: 14px; color: #111827; }
.terms-accordion summary:hover { color: #0e7490; }
.terms-body { margin-top: 10px; }
.terms-body ul { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }
.terms-body li { font-size: 13px; color: #4b5563; line-height: 1.6; }
.terms-body b { color: #1f2937; }
.support-form { margin: 12px 0 20px; }
.support-form textarea { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; font-family: inherit; resize: vertical; }
.support-form-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.support-count { font-size: 12px; color: #9ca3af; }
.support-loading, .support-empty { color: #6b7280; font-size: 13px; padding: 16px 0; }
.support-list { display: flex; flex-direction: column; gap: 12px; }
.support-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; background: #fff; }
.support-item.answered { border-left: 4px solid #059669; }
.support-item:not(.answered) { border-left: 4px solid #d97706; }
.support-q { display: flex; align-items: flex-start; gap: 10px; }
.support-badge { flex-shrink: 0; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.support-badge.answered { background: #d1fae5; color: #065f46; }
.support-badge.pending { background: #fef3c7; color: #92400e; }
.support-question { flex: 1; font-size: 14px; color: #111827; word-break: break-all; }
.support-time { flex-shrink: 0; font-size: 11px; color: #9ca3af; }
.support-a { display: flex; gap: 10px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f3f4f6; }
.support-a-label { flex-shrink: 0; font-weight: 700; color: #059669; font-size: 14px; }
.support-a-body { flex: 1; }
.support-a-body p { margin: 0 0 4px; font-size: 13px; color: #374151; white-space: pre-wrap; word-break: break-all; }

/* 페이지네이션 */
.pagination { display: flex; gap: 6px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
.page-btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.page-btn.active { background: #0e7490; color: #fff; border-color: #0e7490; }
.page-btn:disabled { opacity: 0.5; cursor: default; }
</style>
