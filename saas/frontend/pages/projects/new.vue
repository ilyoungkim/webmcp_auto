<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface DomainType { id: number; code: string; name: string; icon: string; category: string; menus: { label: string }[] }
interface SitemapItem { url: string; title?: string }

const name = ref('')
const url = ref('')
const code = ref('')
const theme = ref('blue_sky')
const types = ref<DomainType[]>([])
const error = ref('')

// 상위 카테고리 정의 (순서대로 표시)
const categories = [
  { key: 'hospital', label: '병원', icon: '🏥' },
  { key: 'law', label: '법률', icon: '⚖️' },
  { key: 'edu', label: '교육및상담', icon: '🎓' },
  { key: 'company', label: '일반회사', icon: '🏢' },
  { key: 'etc', label: '기타', icon: '📦' },
]
const selectedCategory = ref('')

// 선택된 카테고리의 세부 유형 목록
const subTypes = computed(() => types.value.filter(t => t.category === selectedCategory.value))

// 선택된 세부 유형 객체
const selectedType = computed(() => types.value.find(t => t.code === code.value))

// 카테고리 선택 시 세부 유형 초기화
function selectCategory(key: string) {
  selectedCategory.value = key
  code.value = ''
}

// 위젯 테마 목록 (백엔드 core/themes.py 와 동일)
const themes = [
  { code: 'blue_sky', label: 'Blue Sky', primary: '#0284c7', bg: '#f0f9ff' },
  { code: 'red_orange', label: 'Red Orange', primary: '#dc2626', bg: '#fff7ed' },
  { code: 'white_snow', label: 'White Snow', primary: '#334155', bg: '#f8fafc' },
  { code: 'banana_pink', label: 'Banana Pink', primary: '#db2777', bg: '#fdf2f8' },
  { code: 'black_neon', label: 'Black Neon', primary: '#22d3ee', bg: '#0b0f19' },
]

// URL 선택 단계 상태
const step = ref<'form' | 'select'>('form')
const loadingUrls = ref(false)
const sitemapItems = ref<SitemapItem[]>([])
const selectedUrls = ref<string[]>([])
const submitting = ref(false)

onMounted(async () => {
  types.value = await useApi('/api/domain-types/')
})

async function fetchUrls() {
  error.value = ''
  if (!url.value || !code.value) {
    error.value = 'URL과 도메인 유형을 입력해주세요.'
    return
  }
  loadingUrls.value = true
  sitemapItems.value = []
  selectedUrls.value = []
  try {
    const res: any = await useApi(`/api/projects/sitemap-urls/?url=${encodeURIComponent(url.value)}`)
    if (res.items && Array.isArray(res.items)) {
      sitemapItems.value = res.items
    } else if (res.urls && Array.isArray(res.urls)) {
      sitemapItems.value = res.urls.map((u: string) => ({ url: u, title: '' }))
    }
    // 기본으로 상위 최대 10개 선택
    selectedUrls.value = sitemapItems.value.slice(0, 10).map(item => item.url)
    step.value = 'select'
  } catch (e: any) {
    error.value = e?.data?.detail || 'URL 목록을 가져오지 못했습니다.'
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

function backToForm() {
  step.value = 'form'
}

async function submit() {
  error.value = ''
  if (selectedUrls.value.length === 0) {
    alert('최소 1개 이상의 페이지를 선택해주세요.')
    return
  }
  submitting.value = true
  try {
    const p = await useApi('/api/projects/', {
      method: 'POST',
      body: { name: name.value, url: url.value, domainTypeCode: code.value, selectedUrls: selectedUrls.value, theme: theme.value },
    })
    navigateTo(`/projects/${p.id}`)
  } catch (e: any) {
    error.value = e?.data?.detail || '생성 실패'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="wrap">
    <h1>새 프로젝트</h1>

    <!-- 1단계: 기본 정보 입력 -->
    <form v-if="step === 'form'" @submit.prevent="fetchUrls">
      <input v-model="name" placeholder="프로젝트명 (예: OO병원)" required />
      <input v-model="url" type="url" placeholder="https://example.com" required />

      <!-- 1) 상위 카테고리 선택 -->
      <label class="field-label">업종 카테고리</label>
      <div class="cards">
        <button
          v-for="c in categories" :key="c.key" type="button"
          :class="{ active: selectedCategory === c.key }" @click="selectCategory(c.key)"
        >
          <span class="icon">{{ c.icon }}</span>
          <b>{{ c.label }}</b>
        </button>
      </div>

      <!-- 2) 세분화 유형 드롭다운 -->
      <label v-if="selectedCategory" class="field-label">세부 유형</label>
      <select v-if="selectedCategory" v-model="code" class="sub-select">
        <option value="" disabled>세부 유형을 선택하세요</option>
        <option v-for="t in subTypes" :key="t.code" :value="t.code">
          {{ t.icon }} {{ t.name }}
        </option>
      </select>
      <p v-if="selectedCategory && subTypes.length === 0" class="muted">이 카테고리에 해당하는 유형이 없습니다.</p>

      <!-- 3) 선택된 유형의 빠른메뉴 미리보기 -->
      <div v-if="selectedType" class="menu-preview">
        <label class="field-label">이 유형에서 사용할 빠른메뉴 ({{ selectedType.menus.length }}개)</label>
        <ul class="menu-list">
          <li v-for="m in selectedType.menus" :key="m.label" class="menu-item">
            <span class="menu-badge">{{ m.label }}</span>
            <span class="menu-question">{{ m.question }}</span>
          </li>
        </ul>
      </div>

      <div class="theme-section">
        <label class="theme-title">위젯 테마 선택</label>
        <div class="theme-cards">
          <button
            v-for="t in themes" :key="t.code" type="button"
            class="theme-card" :class="{ active: theme === t.code }"
            :style="{ '--primary': t.primary, '--bg': t.bg }"
            @click="theme = t.code"
          >
            <span class="theme-swatch"></span>
            <b>{{ t.label }}</b>
          </button>
        </div>
      </div>

      <button type="submit" :disabled="!code || loadingUrls">
        {{ loadingUrls ? 'URL 목록 가져오는 중...' : '다음: 소스 페이지 선택' }}
      </button>
      <p v-if="error" class="err">{{ error }}</p>
    </form>

    <!-- 2단계: 소스 페이지 선택 -->
    <div v-else class="select-step">
      <p class="desc">
        <b>{{ name }}</b> 사이트맵에서 검색된 <b>Root URL에 가장 가까운 상위 30개 URL</b> 중 크롤링할 페이지를 <b>최대 10개</b> 선택하세요.
      </p>

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

      <div class="actions">
        <button class="btn" @click="backToForm">← 이전</button>
        <button class="btn primary" :disabled="submitting || selectedUrls.length === 0" @click="submit">
          {{ submitting ? '생성 중...' : `선택한 ${selectedUrls.length}개로 프로젝트 생성` }}
        </button>
      </div>
      <p v-if="error" class="err">{{ error }}</p>
    </div>
  </main>
</template>

<style>
.wrap { max-width: 640px; margin: 48px auto; padding: 0 24px; }
form input[type=text], form input[type=url], button[type=submit] { width: 100%; padding: 10px; margin: 6px 0; box-sizing: border-box; }
.field-label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin: 14px 0 6px; }
.cards { display: flex; gap: 12px; margin: 6px 0; flex-wrap: wrap; }
.cards button { flex: 1; min-width: 100px; padding: 16px; border: 2px solid #e5e7eb; border-radius: 10px; background: #fff; cursor: pointer; display: flex; flex-direction: column; gap: 4px; }
.cards button.active { border-color: #0e7490; background: #f0f9ff; }
.icon { font-size: 24px; }
.sub-select { width: 100%; padding: 10px; margin: 6px 0; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.muted { color: #6b7280; font-size: 13px; }

/* 빠른메뉴 미리보기 */
.menu-preview { margin: 14px 0 4px; }
.menu-list { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-direction: column; gap: 8px; }
.menu-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; }
.menu-badge { flex-shrink: 0; font-size: 12px; font-weight: 700; color: #0e7490; background: #e0f2fe; padding: 3px 10px; border-radius: 999px; }
.menu-question { font-size: 13px; color: #374151; }

/* 테마 선택 */
.theme-section { margin: 16px 0 8px; }
.theme-title { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 8px; }
.theme-cards { display: flex; gap: 10px; flex-wrap: wrap; }
.theme-card { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border: 2px solid #e5e7eb; border-radius: 10px; background: #fff; cursor: pointer; font-size: 13px; }
.theme-card.active { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 25%, transparent); }
.theme-swatch { width: 22px; height: 22px; border-radius: 50%; background: linear-gradient(135deg, var(--primary) 50%, var(--bg) 50%); border: 1px solid #e5e7eb; }

.err { color: #b91c1c; }
.desc { font-size: 13px; color: #4b5563; margin: 0 0 12px; }
.select-bar { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding-bottom: 6px; border-bottom: 1px solid #f3f4f6; margin-bottom: 8px; }
.bar-actions { display: flex; gap: 6px; }
.url-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; max-height: 560px; overflow-y: auto; }
.url-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border: 1px solid #f3f4f6; border-radius: 6px; cursor: pointer; font-size: 12px; }
.url-item:hover { background: #f9fafb; border-color: #e5e7eb; }
.url-item.selected { background: #f0f9ff; border-color: #bae6fd; }
.url-num { color: #9ca3af; font-size: 11px; width: 16px; text-align: right; }
.url-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.url-title { font-weight: 600; color: #1f2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.url-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: monospace; color: #6b7280; font-size: 11px; }
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #111827; cursor: pointer; font-size: 13px; }
.btn.sm { padding: 4px 8px; font-size: 12px; }
.btn.primary { background: #0e7490; color: #fff; border-color: #0e7490; }
.btn:disabled { opacity: 0.5; cursor: default; }
</style>
