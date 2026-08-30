<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
interface SitemapItem {
  url: string
  title?: string
}

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const { t, lang, load: loadSilo, formatDate } = useSilo()
// SSR에서도 silo 언어를 로드해 첫 렌더부터 영어 UI가 나오도록 한다
await useAsyncData('silo-info', async () => { await loadSilo(); return true })
// lang은 useState ref — .value 접근 필요
const isEn = computed(() => (lang as any).value === 'en')
// en 사일로용 설치 가이드/약관 컴포넌트
import InstallGuideEn from './terms/InstallGuideEn.vue'
import TermsEn from './terms/TermsEn.vue'

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

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    queued: t('proj.status.queued'),
    crawling: t('proj.status.crawling'),
    generating: t('proj.status.generating'),
    completed: t('proj.status.completed'),
    failed: t('proj.status.failed'),
  }
  return map[s] || s
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
      alert(t('new.err.maxPages'))
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
    alert(t('new.err.minPages'))
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
  if (!confirm(t('proj.edit.deleteConfirm', { name: project.value?.name || '' }))) return
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
  return formatDate(iso)
}

onMounted(async () => {
  await loadSilo()
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
        <NuxtLink to="/dashboard" class="back-link">&larr; {{ t('proj.backToList') }}</NuxtLink>
        <h1>{{ project.name }}</h1>
      </div>
      <div class="actions">
        <span class="badge" :class="project.status">{{ statusLabel(project.status) }} {{ project.progress }}%</span>
        <span v-if="project.status === 'failed'" class="fail-msg">{{ t('proj.edit.failMsg') }}</span>
        <button class="btn" @click="openRerunModal">{{ t('proj.btn.regenerate') }}</button>
        <button class="btn" @click="startEdit">{{ t('proj.btn.edit') }}</button>
        <button class="btn danger" @click="removeProject">{{ t('proj.btn.delete') }}</button>
      </div>
    </header>

    <section v-if="editing" class="edit-panel">
      <p class="note">{{ t('proj.edit.note1') }}</p>
      <label>{{ t('proj.edit.domainType') }}
        <select v-model="editForm.domainTypeCode">
          <option v-for="dt in domainTypes" :key="dt.code" :value="dt.code">{{ dt.name }}</option>
        </select>
      </label>
      <label class="theme-edit-label">{{ t('proj.edit.theme') }}
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
      <p class="note">{{ t('proj.edit.note2') }}</p>
      <div class="edit-actions">
        <button class="btn" @click="editing = false">{{ t('proj.edit.cancel') }}</button>
        <button class="btn primary" :disabled="saving" @click="saveEdit">{{ saving ? t('proj.edit.saving') : t('proj.edit.save') }}</button>
      </div>
    </section>

    <section v-if="project.status === 'failed'" class="err">{{ project.errorMessage }}</section>

    <section v-if="project.status === 'completed'">
      <!-- 수집된 소스 정보 섹션 -->
      <h2>{{ t('proj.sources.title') }} ({{ project.sourceUrls?.length || 0 }})</h2>
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
          <h3>⚠️ {{ t('proj.crawl.failedTitle', { n: project.failedUrls.length }) }}</h3>
          <ul class="failed-list">
            <li v-for="(f, idx) in project.failedUrls" :key="'f' + idx">
              <span class="failed-url">{{ f.url }}</span>
              <span class="failed-err">{{ f.error || t('proj.crawl.failed') }}</span>
            </li>
          </ul>
          <p class="failed-note">{{ t('proj.crawl.failedNote') }}</p>
        </div>
      </div>

      <!-- 설치 및 사용 방법 (아코디언, 닫힌 상태) — 사일로 언어별 전환 -->
      <InstallGuideEn v-if="isEn" :project-id="id" />
      <details v-else class="install-accordion">
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
        <NuxtLink :to="`/preview/${id}`" class="btn primary">👁 {{ t('proj.btn.preview') }}</NuxtLink>
      </div>

      <h2>{{ t('proj.qna.title') }}</h2>

      <details v-for="(q, i) in qna" :key="i" class="qna-item">
        <summary><span class="q-marker">Q:</span> <b>{{ q.menuLabel }}</b> — {{ q.question }}</summary>
        <pre>{{ q.answerMd }}</pre>
      </details>

      <!-- 빠른메뉴 질문 편집 (가장 아래, 아코디언) -->
      <details class="menu-edit-accordion">
        <summary>✏️ {{ t('proj.menuEdit.title') }}</summary>
        <div class="menu-edit-card">
          <p v-if="menuEdited" class="note locked-note">{{ t('proj.menuEdit.locked') }}</p>
          <p v-else class="note">{{ t('proj.menuEdit.note') }}</p>

          <div v-if="menuLoading" class="menu-loading">{{ t('proj.menuEdit.loading') }}</div>

          <div v-else class="menu-edit-body">
            <div v-for="(m, i) in menuItems" :key="i" class="menu-edit-row">
              <label class="menu-label">{{ m.label }}</label>
              <input v-model="m.question" class="menu-question" :placeholder="t('proj.menuEdit.placeholder')" :disabled="menuEdited" />
            </div>

            <div class="menu-edit-actions">
              <button class="btn primary" :disabled="menuSaving || menuEdited" @click="regenerateMenus">
                {{ menuSaving ? t('proj.menuEdit.regenerating') : (menuEdited ? t('proj.menuEdit.edited') : t('proj.menuEdit.regenerate')) }}
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
      <h2>{{ t('proj.support.title') }}</h2>
      <p class="note">{{ t('proj.support.note') }}</p>

      <!-- 질문 등록 폼 -->
      <div class="support-form">
        <textarea v-model="supportQuestion" rows="3" :placeholder="t('proj.support.placeholder')" maxlength="2000"></textarea>
        <div class="support-form-actions">
          <span class="support-count">{{ supportQuestion.length }}/2000</span>
          <button class="btn primary" :disabled="supportSubmitting" @click="submitSupport">
            {{ supportSubmitting ? t('proj.support.submitting') : t('proj.support.submit') }}
          </button>
        </div>
        <p v-if="supportError" class="err">{{ supportError }}</p>
        <p v-if="supportSuccess" class="ok">{{ supportSuccess }}</p>
      </div>

      <!-- Q&A 목록 -->
      <div v-if="supportLoading" class="support-loading">{{ t('common.loading') }}</div>
      <div v-else-if="supportItems.length === 0" class="support-empty">{{ t('proj.support.empty') }}</div>
      <div v-else class="support-list">
        <div v-for="t in supportItems" :key="t.id" class="support-item" :class="{ answered: t.status === 'answered' }">
          <div class="support-q">
            <span class="support-badge" :class="t.status">{{ t.status === 'answered' ? t('proj.support.answered') : t('proj.support.pending') }}</span>
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
        <button class="page-btn" :disabled="supportPage <= 1" @click="supportPageBtn(supportPage - 1)">← {{ t('common.prev') }}</button>
        <button
          v-for="p in supportTotalPages" :key="p"
          class="page-btn" :class="{ active: p === supportPage }"
          @click="supportPageBtn(p)"
        >{{ p }}</button>
        <button class="page-btn" :disabled="supportPage >= supportTotalPages" @click="supportPageBtn(supportPage + 1)">{{ t('common.next') }} →</button>
      </div>
    </section>

    <!-- 이용약관 아코디언 — 사일로 언어별 전환 -->
    <TermsEn v-if="isEn" />
    <section v-else class="terms-section">
      <div class="terms-title">
        <h2>읽어볼 내용</h2>
        <p class="note">WebMCP AI 비서 서비스의 이용 조건 및 절차, 이용자와 서비스 제공자의 권리·의무, 책임사항을 규정합니다.</p>
      </div>

      <details class="terms-accordion">
        <summary>📋 이용약관</summary>
        <div class="terms-body">
          <h4>제1장 총칙</h4>
          <h4>제1조 (목적)</h4>
          <p>본 약관은 WebMCP AI 비서 서비스(이하 "서비스")가 제공하는 모든 서비스의 이용 조건 및 절차, 이용자와 서비스 제공자의 권리·의무·책임사항과 기타 필요한 사항을 규정함을 목적으로 합니다.</p>
          <h4>제2조 (용어의 정의)</h4>
          <p>본 약관에서 사용하는 용어의 정의는 다음과 같습니다.</p>
          <ul>
            <li><b>서비스</b> : WebMCP AI 비서가 제공하는 AI 기반 홈페이지 상담 위젯 및 관련 제반 기능</li>
            <li><b>이용자(회원)</b> : 본 약관에 동의하고, 프로젝트를 등록하여 서비스를 이용할 수 있는 권한을 부여받은 개인 또는 사업자</li>
            <li><b>프로젝트</b> : 이용자가 등록한 홈페이지 URL과 도메인 유형·테마 등을 포함한 AI 비서 생성 단위</li>
            <li><b>AI 비서(위젯)</b> : 이용자가 등록한 홈페이지에 설치되어 방문자와 대화하는 인공지능 챗봇</li>
          </ul>
          <h4>제3조 (약관의 효력과 변경)</h4>
          <ul>
            <li>본 약관은 서비스 이용 화면에 게시되고, 이용자가 프로젝트를 등록함으로써 그 효력이 발생합니다.</li>
            <li>서비스 제공자가 본 약관을 변경하는 경우, 적용 일자와 변경사항을 명시하여 적용 일자 7일 전에 이용자에게 공지하며, 공지와 동시에 그 효력이 발생합니다.</li>
            <li>변경된 약관을 공지하면서 거부 의사를 표시하지 않으면 약관 변경에 동의한 것으로 간주한다는 내용을 명확히 공지했음에도 이용자가 거부 의사표시를 하지 않은 경우, 이용자는 개정 약관에 동의한 것으로 봅니다.</li>
            <li>이용자가 변경된 약관에 동의하지 않을 때에는 서비스 이용을 중단하고 프로젝트를 삭제할 수 있습니다.</li>
          </ul>
          <h4>제4조 (약관 외 준칙)</h4>
          <p>본 약관에 명시되지 않는 사항이 관계 법령에 규정되어 있는 경우 그 규정을 따르며, 그렇지 않으면 일반적인 관례에 따릅니다.</p>

          <h4>제2장 서비스 이용</h4>
          <h4>제5조 (이용등록의 성립)</h4>
          <ul>
            <li>이용등록은 신청자가 온라인으로 서비스가 제공하는 등록 양식에서 요구하는 사항(홈페이지 URL, 이름 등)을 기록하여 등록을 완료하는 것으로 성립됩니다.</li>
            <li>서비스 제공자는 다음 각 호에 해당하는 이용등록에 대하여 등록을 거절하거나 프로젝트를 삭제할 수 있습니다.
              <ul>
                <li>다른 사람의 명의를 사용하여 신청한 경우</li>
                <li>등록 신청서의 내용을 허위로 기재한 경우</li>
                <li>사회의 안녕질서 또는 미풍양속을 저해할 목적으로 신청한 경우</li>
                <li>다른 사람의 서비스 이용을 방해하거나 정보를 도용하는 행위를 한 경우</li>
                <li>본 서비스를 이용하여 법령과 본 약관이 금지하는 행위를 하는 경우</li>
                <li>기타 서비스 제공자가 정한 이용신청요건이 미비된 경우</li>
              </ul>
            </li>
          </ul>
          <h4>제6조 (서비스 내용 및 이용)</h4>
          <ul>
            <li>이용자는 홈페이지 URL을 등록하면 서비스가 사이트를 크롤링하여 AI 비서 위젯을 자동 생성합니다.</li>
            <li>이용자는 도메인 유형과 위젯 테마를 변경할 수 있으며, 빠른메뉴 질문을 <b>1회</b> 편집할 수 있습니다.</li>
            <li>프로젝트는 계정당 최대 <b>5개</b>까지 생성할 수 있습니다.</li>
            <li>생성된 AI 비서 위젯은 이용자가 등록한 홈페이지에만 설치할 수 있습니다.</li>
          </ul>
          <h4>제7조 (AI 답변의 한계)</h4>
          <ul>
            <li>AI 비서의 답변은 대규모 언어 모델(LLM)이 생성한 것으로, <b>사실과 다를 수 있으며</b> 의학적·법률적·재정적 조언으로 간주해서는 안 됩니다.</li>
            <li>중요한 결정(진료, 법률, 투자 등)은 반드시 전문가와 상담하시기 바랍니다.</li>
            <li>AI 답변은 수집된 홈페이지 정보를 기반으로 생성되며, 홈페이지에 없는 정보는 정확하지 않을 수 있습니다.</li>
            <li>AI가 생성한 답변에 대하여 서비스 제공자는 정확성·완전성·질을 보장하지 않습니다.</li>
          </ul>
          <h4>제8조 (서비스의 이용시간 및 중지)</h4>
          <ul>
            <li>서비스 이용시간은 서비스 제공자의 업무상 또는 기술상 특별한 지장이 없는 한 연중무휴, 1일 24시간을 원칙으로 하며, 정기점검 등의 필요로 정한 날 또는 시간은 예외로 합니다.</li>
            <li>국가 비상사태, 정전, 서비스 설비 장애, 불가항력 등으로 서비스가 중단되거나 데이터가 손실된 경우, 서비스 제공자는 관련 책임을 부담하지 않습니다.</li>
            <li>서비스 제공자의 사정으로 서비스를 일시적으로 수정·변경·중단할 수 있으며, 이에 대하여 이용자 또는 제3자에게 어떠한 책임도 부담하지 않습니다.</li>
            <li>이용자가 본 약관을 위배한 경우, 서비스 제공자는 이용자의 서비스 사용을 제한하거나 중지할 수 있으며, 접속을 금지할 수 있습니다.</li>
          </ul>

          <h4>제3장 개인정보보호</h4>
          <h4>제9조 (개인정보의 수집)</h4>
          <ul>
            <li>서비스는 이용자의 이메일, 이름 등 최소한의 개인정보만 수집하며, 서비스 제공 목적으로만 사용합니다.</li>
            <li>이용자가 등록한 홈페이지의 콘텐츠는 AI 비서 답변 생성 목적으로만 사용됩니다.</li>
          </ul>
          <h4>제10조 (개인정보의 이용·제공)</h4>
          <ul>
            <li>서비스 제공자는 이용자의 동의 없이 개인정보를 제3자에게 제공하지 않으며, 법률의 규정에 따라 국가기관의 요구가 있거나 범죄 수사상의 목적 등 관계 법령에서 정한 절차에 따른 요청이 있는 경우 이에 따를 수 있습니다.</li>
            <li>AI 채팅 과정에서 입력된 질문은 서비스 품질 개선을 위해 저장될 수 있습니다.</li>
          </ul>
          <h4>제11조 (개인정보의 관리·보호)</h4>
          <ul>
            <li>이용자는 개인정보의 열람·정정·삭제를 요청할 권리가 있으며, 서비스 제공자는 관련 법령에 따라 이를 안전하게 보호합니다.</li>
            <li>이용자는 자신의 계정 정보 및 AI 비서 사용과 관련된 정보를 안전하게 관리할 책임이 있으며, 타인에게 비밀을 누설해서는 안 됩니다. 서비스 사용 종료 시에는 정확히 로그아웃하고 웹 브라우저 창을 닫아야 합니다.</li>
            <li>이용자의 정보가 부정하게 사용되었다는 사실을 발견한 경우 즉시 서비스 제공자에게 신고하여야 하며, 신고하지 않음으로 인한 책임은 이용자 본인에게 있습니다.</li>
          </ul>

          <h4>제4장 의무 및 책임</h4>
          <h4>제12조 (서비스 제공자의 의무)</h4>
          <ul>
            <li>서비스 제공자는 법령과 본 약관이 금지하거나 미풍양속에 반하는 행위를 하지 않으며, 지속적이고 안정적으로 서비스를 제공하기 위해 노력할 의무가 있습니다.</li>
            <li>약관 변경사항의 공지 또는 이용자에 대한 통지가 필요한 경우 해당 절차를 성실히 준수하여 수행합니다.</li>
            <li>서비스 제공자는 이용자가 본 약관을 위배했다고 판단되면 서비스와 관련된 정보를 이용자의 동의 없이 삭제할 수 있습니다.</li>
          </ul>
          <h4>제13조 (이용자의 의무 및 서비스 이용제한)</h4>
          <ul>
            <li>이용자가 제공한 정보의 내용이 허위인 것으로 판명되거나, 그러하다고 의심할 만한 합리적인 사유가 발생하면 서비스 제공자는 이용자의 서비스 사용을 일부 또는 전부 중지할 수 있으며, 이로 인해 발생하는 불이익에 대한 책임을 부담하지 않습니다.</li>
            <li>이용자가 서비스를 통하여 게시·전송·입수한 모든 형태의 정보에 대하여는 이용자가 모든 책임을 부담하며, 서비스 제공자는 어떠한 책임도 부담하지 않습니다.</li>
            <li>이용자는 본 서비스를 통하여 다음 각 호의 행위를 하지 않습니다.
              <ul>
                <li>타인의 아이디와 인증수단을 도용하는 행위</li>
                <li>저속·음란·모욕적·위협적이거나 타인의 프라이버시를 침해할 수 있는 내용을 전송·게시하는 행위</li>
                <li>서비스를 통하여 전송된 내용의 출처를 위장하는 행위</li>
                <li>법률·약관에 의하여 이용할 수 없는 내용을 게시·전송하는 행위</li>
                <li>타인의 특허·상표·영업비밀·저작권 등 지적 재산권을 침해하는 행위</li>
                <li>서비스의 승인을 받지 아니한 광고·판촉물·정크메일 등 다른 형태의 권유를 전송하는 행위</li>
                <li>다른 이용자의 개인정보를 수집 또는 저장하는 행위</li>
              </ul>
            </li>
            <li>이용자는 서비스의 사전 승낙 없이 서비스를 이용하여 어떠한 영리 행위도 할 수 없습니다.</li>
            <li>이용자는 서비스를 이용하여 얻은 정보를 서비스 제공자의 사전 승낙 없이 복사·복제·변경·번역·출판·방송 기타의 방법으로 사용하거나 이를 타인에게 제공할 수 없습니다.</li>
          </ul>
          <h4>제14조 (자동화된 도구 사용 등 금지 행위)</h4>
          <ul>
            <li>사전 허락 없이 자동화된 도구(매크로, 스크래핑 등)를 이용하여 서비스의 기능을 우회하거나 무력화하는 행위</li>
            <li>IP를 지속적으로 변경하며 서비스에 접속하거나 접속을 우회하는 행위</li>
            <li>서비스의 안정적인 운영에 지장을 주거나 줄 우려가 있는 일체의 행위</li>
            <li>금지된 행위로 인한 개인정보 오남용·유출사고, 서비스 지연 또는 중단 등이 발생할 경우 관계 법령에 따른 처벌 및 책임을 질 수 있습니다.</li>
          </ul>
          <h4>제15조 (지식재산권)</h4>
          <ul>
            <li>서비스를 통해 제공되는 소프트웨어·이미지·로고·디자인·서비스 명칭·상표 등과 관련된 지적 재산권 및 기타 권리는 서비스 제공자에게 있습니다.</li>
            <li>이용자는 서비스 제공자가 명시적으로 승인한 경우를 제외하고는 이를 무단 복제·수정·배포·판매·양도하거나 제3자에게 제공할 수 없습니다.</li>
          </ul>
          <h4>제16조 (양도금지)</h4>
          <p>이용자는 서비스의 이용 권한, 기타 이용등록 상의 지위를 타인에게 양도 및 증여할 수 없으며, 이를 담보로 제공할 수 없습니다.</p>
          <h4>제17조 (손해배상 및 면책)</h4>
          <ul>
            <li>서비스 제공자는 고의로 행한 범죄행위를 제외하고, 무료로 제공되는 서비스와 관련하여 이용자에게 발생한 손해에 대하여 책임을 부담하지 않습니다.</li>
            <li>서비스 제공자는 서비스에 표출된 어떠한 의견이나 정보에 대해 확신이나 대표할 의무가 없으며, 이용자가 서비스에 담긴 정보에 의존해 얻은 이득이나 입은 손해에 대한 책임이 없습니다.</li>
            <li>이용자 간 또는 이용자와 제3자 간에 서비스를 매개로 하여 발생하는 거래나 분쟁에 대하여 서비스 제공자는 어떠한 책임도 부담하지 않습니다.</li>
            <li>천재지변, 시스템 점검 등 불가항력적 사유로 서비스가 중단될 수 있습니다.</li>
          </ul>
          <h4>제18조 (준거법 및 관할법원)</h4>
          <p>서비스 제공자와 이용자 간에 발생한 서비스 이용에 관한 분쟁에 대하여는 대한민국 법을 적용하며, 본 분쟁으로 인한 소는 대한민국의 법원에 제기합니다.</p>
        </div>
      </details>

      <details class="terms-accordion">
        <summary>🤖 AI 이용고지</summary>
        <div class="terms-body">
          <h4>AI기본법상 사전 고지와 결과물 표시</h4>
          <p>AI기본법 제31조는 생성형 AI 관련 투명성 의무를 두 단계로 구분합니다.</p>
          <p>먼저 생성형 AI를 이용한 제품이나 서비스를 제공하려는 인공지능사업자는 해당 제품·서비스가 생성형 AI에 기반해 운용된다는 사실을 이용자에게 <b>사전에 고지</b>해야 합니다.</p>
          <p>이와 별도로 생성형 AI 또는 이를 이용한 서비스가 만든 결과물에는 해당 결과물이 생성형 AI에 의해 생성됐다는 사실을 <b>표시</b>해야 합니다.</p>
          <p>특히 실제와 구분하기 어려운 음성·이미지·영상은 이용자가 AI 생성물임을 명확하게 인식할 수 있는 방식으로 고지하거나 표시해야 합니다.</p>
          <p>본 서비스는 본 저작물(또는 기사/글)의 일부 또는 전체는 인공지능(AI) 기술을 활용하여 데이터를 수집 및 초안을 작성하거나 편집 보조를 받아 제작되었습니다. 타인의 저작권을 침해하지 않는 범위 내에서 정당하게 기술을 활용하였으며, 이에 따른 고지 의무를 성실히 이행합니다.</p>

          <h4>본 서비스의 AI 모델</h4>
          <ul>
            <li>본 서비스(WebMCP AI 비서)는 AI 기반 상담 위젯으로, 답변 생성에 <b>Google Gemini</b>와 <b>OpenAI OSS-120B</b>를 사용합니다.</li>
            <li>실시간 채팅 및 사이트 요약에는 <b>Google Gemini</b>가, Q&A 배치 생성에는 <b>OpenAI OSS-120B</b>가 사용됩니다.</li>
            <li>AI 비서가 생성한 모든 답변은 <b>AI가 생성한 결과물</b>임을 인지하고 이용하시기 바랍니다.</li>
          </ul>

          <h4>AI 이용 주의사항</h4>
          <ul>
            <li>AI 비서의 답변은 대규모 언어 모델(LLM)이 생성한 것으로, <b>사실과 다를 수 있으며</b> 의학적·법률적·재정적 조언으로 간주해서는 안 됩니다.</li>
            <li>중요한 결정(진료, 법률, 투자 등)은 반드시 전문가와 상담하시기 바랍니다.</li>
            <li>AI 답변은 수집된 홈페이지 정보를 기반으로 생성되며, 홈페이지에 없는 정보는 정확하지 않을 수 있습니다.</li>
            <li>AI가 생성한 답변으로 인한 손해에 대해 서비스 제공자는 책임을 지지 않습니다.</li>
            <li>AI 답변 품질은 사용량·모델 상태에 따라 달라질 수 있으며, 서비스는 이를 보장하지 않습니다.</li>
            <li>AI가 생성한 결과물은 실제와 구분하기 어려울 수 있으므로, 중요한 정보는 반드시 원본 출처에서 확인하시기 바랍니다.</li>
          </ul>
        </div>
      </details>

      <details class="terms-accordion">
        <summary>🔒 개인정보처리방침</summary>
        <div class="terms-body">
          <h4>1. 개인정보의 처리 목적</h4>
          <p>WebMCP AI 비서 서비스(이하 "서비스")는 다음의 목적을 위하여 개인정보를 처리하고 있으며, 다음의 목적 이외의 용도로는 이용하지 않습니다.</p>
          <ul>
            <li>고객 가입의사 확인, 고객에 대한 서비스 제공에 따른 본인 식별·인증, 회원자격 유지·관리</li>
            <li>AI 비서 위젯 생성·운영, 고객 문의 및 상담 응대</li>
            <li>서비스 품질 개선 및 이용 통계 분석</li>
          </ul>

          <h4>2. 개인정보의 처리 및 보유 기간</h4>
          <p>① 서비스는 정보주체로부터 개인정보를 수집할 때 동의 받은 개인정보 보유·이용기간 또는 법령에 따른 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>
          <p>② 구체적인 개인정보 처리 및 보유 기간은 다음과 같습니다.</p>
          <ul>
            <li>회원 가입 및 관리 : 이메일, 이름 등 회원 정보</li>
            <li>보유 기간 : 회원 탈퇴 시, 즉시 삭제</li>
            <li>고객 문의 : 문의 접수 후 2년 간 보관 (단, 관계 법령이 정한 시점까지 보존)</li>
          </ul>

          <h4>3. 정보주체와 법정대리인의 권리·의무 및 그 행사방법</h4>
          <p>이용자는 개인정보주체로서 다음과 같은 권리를 행사할 수 있습니다.</p>
          <ul>
            <li>개인정보 열람요구</li>
            <li>오류 등이 있을 경우 정정 요구</li>
            <li>삭제요구</li>
            <li>처리정지 요구</li>
          </ul>

          <h4>4. 처리하는 개인정보의 항목</h4>
          <p>서비스는 다음의 개인정보 항목을 처리하고 있습니다.</p>
          <ul>
            <li><b>회원 가입 시</b> : 이메일, 이름 (수집목적: 회원관리 및 서비스 제공, 보유기간: 회원 탈퇴 또는 동의철회 시 지체없이 파기)</li>
            <li><b>고객 문의 시</b> : 이름, 이메일, 문의사항 (수집목적: 고객문의 및 상담요청에 대한 회신, 보유기간: 문의 접수 후 2년)</li>
            <li><b>AI 채팅 이용 시</b> : 채팅 질문 내용 (수집목적: AI 답변 생성 및 서비스 품질 개선, 보유기간: 서비스 품질 개선 목적 달성 시 파기)</li>
          </ul>
          <p>서비스는 만 14세 미만 아동의 개인정보를 보호하기 위하여 회원가입은 만 14세 이상만 가능하도록 함으로써 아동의 개인정보를 수집하지 않습니다.</p>

          <h4>5. 개인정보의 파기</h4>
          <p>서비스는 원칙적으로 개인정보 처리목적이 달성된 경우에는 지체없이 해당 개인정보를 파기합니다.</p>
          <ul>
            <li><b>파기절차</b> : 이용자가 입력한 정보는 목적 달성 후 별도의 DB에 옮겨져 내부 방침 및 기타 관련 법령에 따라 일정기간 저장된 후 혹은 즉시 파기됩니다. 이 때, DB로 옮겨진 개인정보는 법률에 의한 경우가 아니고서는 다른 목적으로 이용되지 않습니다.</li>
            <li><b>파기기한</b> : 이용자의 개인정보는 보유기간이 경과된 경우에는 보유기간의 종료일로부터 5일 이내에, 처리 목적 달성·서비스 폐지·사업 종료 등 그 개인정보가 불필요하게 되었을 때에는 처리가 불필요한 것으로 인정되는 날로부터 5일 이내에 파기합니다.</li>
          </ul>

          <h4>6. 개인정보 자동 수집 장치의 설치·운영 및 거부에 관한 사항</h4>
          <p>① 서비스는 개별적인 맞춤서비스를 제공하기 위해 이용정보를 저장하고 수시로 불러오는 '쿠키(cookie)'를 사용합니다.</p>
          <p>② 쿠키는 웹사이트를 운영하는데 이용되는 서버가 이용자의 컴퓨터 브라우저에게 보내는 소량의 정보이며 이용자들의 PC 컴퓨터 내의 하드디스크에 저장되기도 합니다.</p>
          <ul>
            <li>가. 쿠키의 사용 목적 : 이용자가 방문한 각 서비스와 웹 사이트들에 대한 방문 및 이용형태, 보안접속 여부 등을 파악하여 이용자에게 최적화된 정보 제공을 위해 사용됩니다.</li>
            <li>나. 쿠키의 설치·운영 및 거부 : 웹브라우저 상단의 도구 &gt; 인터넷 옵션 &gt; 개인정보 메뉴의 옵션 설정을 통해 쿠키 저장을 거부할 수 있습니다.</li>
            <li>다. 쿠키 저장을 거부할 경우 맞춤형 서비스 이용에 어려움이 발생할 수 있습니다.</li>
          </ul>

          <h4>7. 개인정보 보호책임자</h4>
          <p>① 서비스는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만처리 및 피해구제 등을 위하여 아래와 같이 개인정보 보호책임자를 지정하고 있습니다.</p>
          <ul>
            <li><b>개인정보 보호책임자</b> : 이장원 / 직책: 상무 / 연락처: 02-752-0719</li>
          </ul>
          <p>② 서비스 이용 시 발생한 모든 개인정보 보호 관련 문의, 불만처리, 피해구제 등에 관한 사항을 개인정보 보호책임자에게 문의하실 수 있으며, 서비스는 정보주체의 문의에 대해 지체 없이 답변 및 처리해 드릴 것입니다.</p>

          <h4>8. 개인정보 처리방침 변경</h4>
          <p>이 개인정보처리방침은 시행일로부터 적용되며, 법령 및 방침에 따른 변경내용의 추가, 삭제 및 정정이 있는 경우에는 변경사항의 시행 7일 전부터 공지사항을 통하여 고지할 것입니다.</p>

          <h4>9. 개인정보의 안전성 확보 조치</h4>
          <p>서비스는 개인정보보호법 제29조에 따라 다음과 같이 안전성 확보에 필요한 기술적·관리적 및 물리적 조치를 하고 있습니다.</p>
          <ul>
            <li><b>개인정보 취급 직원의 최소화 및 교육</b> : 개인정보를 취급하는 직원을 지정하고 담당자에 한정시켜 최소화하여 개인정보를 관리하는 대책을 시행하고 있습니다.</li>
            <li><b>해킹 등에 대비한 기술적 대책</b> : 해킹이나 컴퓨터 바이러스 등에 의한 개인정보 유출 및 훼손을 막기 위하여 보안프로그램을 설치하고 주기적인 갱신·점검을 하며 외부로부터 접근이 통제된 구역에 시스템을 설치하고 기술적·물리적으로 감시 및 차단하고 있습니다.</li>
            <li><b>개인정보의 암호화</b> : 이용자의 개인정보는 비밀번호가 암호화되어 저장 및 관리되고 있어 본인만이 알 수 있으며, 중요한 데이터는 파일 및 전송 데이터를 암호화하거나 파일 잠금 기능을 사용하는 등의 별도 보안기능을 사용하고 있습니다.</li>
            <li><b>접속기록의 보관 및 위변조 방지</b> : 개인정보처리시스템에 접속한 기록을 최소 6개월 이상 보관·관리하고 있으며, 접속 기록이 위변조 및 도난·분실되지 않도록 보안기능을 사용하고 있습니다.</li>
            <li><b>개인정보에 대한 접근 제한</b> : 개인정보를 처리하는 데이터베이스시스템에 대한 접근권한의 부여·변경·말소를 통하여 개인정보에 대한 접근통제를 위한 필요한 조치를 하고 있으며, 침입차단시스템을 이용하여 외부로부터의 무단 접근을 통제하고 있습니다.</li>
          </ul>

          <h4>10. 정보주체의 권익침해에 대한 구제방법</h4>
          <p>아래의 기관은 서비스 제공자와는 별개의 기관으로서, 서비스의 자체적인 개인정보 불만처리·피해구제 결과에 만족하지 못하시거나 보다 자세한 도움이 필요하시면 문의하여 주시기 바랍니다.</p>
          <ul>
            <li><b>개인정보 침해신고센터</b> (한국인터넷진흥원 운영) : privacy.kisa.or.kr / (국번없이) 118</li>
            <li><b>개인정보 분쟁조정위원회</b> : www.kopico.go.kr / (국번없이) 1833-6972</li>
            <li><b>대검찰청 사이버범죄수사단</b> : 02-3480-3573 (www.spo.go.kr)</li>
            <li><b>경찰청 사이버안전국</b> : 182 (http://cyberbureau.police.go.kr)</li>
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
          <h3>{{ t('proj.rerun.title') }}</h3>
          <button class="close-btn" @click="rerunModalOpen = false">&times;</button>
        </header>

        <p class="modal-desc">{{ t('new.selectStep.desc', { name: project?.name || '' }) }}</p>

        <div v-if="loadingUrls" class="modal-loading">
          {{ t('proj.rerun.fetching') }}
        </div>

        <div v-else class="modal-body">
          <div class="select-bar">
            <span>{{ t('new.selectStep.selected', { n: selectedUrls.length }) }}</span>
            <div class="bar-actions">
              <button class="btn sm" @click="selectAllTop10">{{ t('new.selectStep.top10') }}</button>
              <button class="btn sm" @click="clearSelection">{{ t('new.selectStep.clear') }}</button>
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
          <button class="btn" @click="rerunModalOpen = false">{{ t('proj.edit.cancel') }}</button>
          <button class="btn primary" :disabled="submittingRerun || selectedUrls.length === 0" @click="submitRerun">
            {{ submittingRerun ? t('proj.rerun.requesting') : t('proj.rerun.start', { n: selectedUrls.length }) }}
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
.terms-title { margin-bottom: 4px; }
.terms-title h2 { font-size: 18px; margin: 0 0 4px; color: #111827; }
.terms-title .note { font-size: 12px; color: #6b7280; }
.terms-accordion { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; background: #fafafa; }
.terms-accordion summary { cursor: pointer; font-weight: 600; font-size: 14px; color: #111827; }
.terms-accordion summary:hover { color: #0e7490; }
.terms-body { margin-top: 10px; display: flex; flex-direction: column; gap: 10px; }
.terms-body h4 { font-size: 13px; color: #374151; margin: 0; }
.terms-body p { font-size: 13px; color: #4b5563; line-height: 1.7; margin: 0; }
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
