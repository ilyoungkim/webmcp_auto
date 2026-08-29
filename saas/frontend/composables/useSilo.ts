// 사일로 언어 확인 — 백엔드 /api/silo-info/ 로 현재 사일로의 언어를 가져온다.
// en 사일로(8081)에서는 콘솔 UI가 영어로 표시되고, ko 사일로는 한국어로 표시된다.
export type SiloLang = 'ko' | 'en'

interface SiloState {
  lang: Ref<SiloLang>
  ready: Ref<boolean>
  t: (key: string, params?: Record<string, string | number>) => string
  load: () => Promise<void>
}

// ── 콘솔 UI 다국어 사전 ──────────────────────────────────────
// 위젯(webmcp-widget.js)의 I18N과 동일한 규격으로, 콘솔 페이지 문구를 담는다.
const MESSAGES: Record<SiloLang, Record<string, string>> = {
  ko: {
    // projects/new.vue
    'new.title': '새 프로젝트',
    'new.namePlaceholder': '프로젝트명 (예: OO병원)',
    'new.field.category': '업종 카테고리',
    'new.field.subtype': '세부 유형',
    'new.subtype.placeholder': '세부 유형을 선택하세요',
    'new.subtype.empty': '이 카테고리에 해당하는 유형이 없습니다.',
    'new.field.quickMenu': '이 유형에서 사용할 빠른메뉴 ({n}개)',
    'new.field.theme': '위젯 테마 선택',
    'new.next': '다음: 소스 페이지 선택',
    'new.fetchingUrls': 'URL 목록 가져오는 중...',
    'new.selectStep.desc': '{name} 사이트맵에서 검색된 Root URL에 가장 가까운 상위 30개 URL 중 크롤링할 페이지를 최대 10개 선택하세요.',
    'new.selectStep.selected': '선택됨: {n} / 10개',
    'new.selectStep.top10': '상위 10개 선택',
    'new.selectStep.clear': '전체 해제',
    'new.selectStep.back': '← 이전',
    'new.selectStep.create': '선택한 {n}개로 프로젝트 생성',
    'new.creating': '생성 중...',
    'new.err.urlAndType': 'URL과 도메인 유형을 입력해주세요.',
    'new.err.fetchUrls': 'URL 목록을 가져오지 못했습니다.',
    'new.err.maxPages': '최대 10개만 선택할 수 있습니다.',
    'new.err.minPages': '최소 1개 이상의 페이지를 선택해주세요.',
    'new.err.create': '생성 실패',
    // 업종 카테고리 (ko)
    'cat.hospital': '병원',
    'cat.law': '법률',
    'cat.edu': '교육및상담',
    'cat.company': '일반회사',
    'cat.etc': '기타',
    // projects/[id].vue — 주요 문구만
    'proj.status.queued': '예약',
    'proj.status.crawling': '진행중',
    'proj.status.generating': '진행중',
    'proj.status.completed': '완료',
    'proj.status.failed': '실패',
    'proj.backToList': '목록으로',
    'proj.btn.regenerate': '재생성',
    'proj.btn.edit': '수정',
    'proj.btn.delete': '삭제',
    'proj.edit.failMsg': '재생성하거나 문의 02-888-9999로 연락 주세요.',
    'proj.edit.note1': '이름과 URL은 변경할 수 없습니다. 도메인 유형과 위젯 테마만 변경할 수 있습니다.',
    'proj.edit.domainType': '도메인 유형',
    'proj.edit.theme': '위젯 테마',
    'proj.edit.note2': "도메인 유형 변경 후 '재생성' 버튼을 누르면 새 사이트맵 기반으로 다시 수집합니다. 테마는 저장 즉시 위젯에 반영됩니다.",
    'proj.edit.cancel': '취소',
    'proj.edit.save': '저장',
    'proj.edit.saving': '저장 중...',
    'proj.edit.deleteConfirm': "'{name}' 프로젝트를 삭제할까요?",
    'proj.sources.title': '수집된 소스 정보',
    'proj.btn.preview': '미리보기',
    'proj.qna.title': '빠른메뉴 - 자동화된 질문 및 답변',
    'proj.crawl.failed': '크롤링 실패',
    'proj.crawl.failedTitle': '크롤링 실패 ({n}개)',
    'proj.crawl.failedNote': '실패한 페이지는 재생성 시 다시 시도됩니다. 지속적으로 실패하면 사이트 구조(JS 렌더링, 로그인 등)를 확인해 주세요.',
    'proj.menuEdit.title': '빠른메뉴 질문 편집',
    'proj.menuEdit.locked': '빠른메뉴 질문 편집은 1회만 가능합니다. 이미 편집이 완료되어 더 이상 수정할 수 없습니다.',
    'proj.menuEdit.note': "질문을 수정한 뒤 '답변 재생성'을 누르면, 이미 수집된 소스를 기반으로 답변이 다시 생성됩니다. (재크롤링 없음 · 편집은 1회만 가능)",
    'proj.menuEdit.loading': '빠른메뉴 불러오는 중...',
    'proj.menuEdit.placeholder': '질문을 입력하세요',
    'proj.menuEdit.regenerating': '재생성 중...',
    'proj.menuEdit.edited': '편집 완료',
    'proj.menuEdit.regenerate': '답변 재생성',
    'proj.support.title': '고객센터 Q&A',
    'proj.support.note': '궁금한 점을 질문해 주세요. 관리자가 답변을 등록하면 확인할 수 있습니다.',
    'proj.support.placeholder': '질문 내용을 입력하세요 (2000자 이내)',
    'proj.support.submit': '질문 등록',
    'proj.support.submitting': '등록 중...',
    'proj.support.empty': '등록된 Q&A가 없습니다.',
    'proj.support.answered': '답변완료',
    'proj.support.pending': '답변대기',
    'proj.rerun.title': '재생성 소스 페이지 선택',
    'proj.rerun.fetching': '사이트맵에서 URL 목록을 가져오는 중...',
    'proj.rerun.requesting': '요청 중...',
    'proj.rerun.start': '선택한 {n}개로 재생성 시작',
    'common.loading': '불러오는 중...',
    'common.prev': '이전',
    'common.next': '다음',
  },
  en: {
    // projects/new.vue
    'new.title': 'New Project',
    'new.namePlaceholder': 'Project name (e.g., City Hospital)',
    'new.field.category': 'Industry Category',
    'new.field.subtype': 'Sub type',
    'new.subtype.placeholder': 'Select a sub type',
    'new.subtype.empty': 'No types in this category.',
    'new.field.quickMenu': 'Quick menus for this type ({n})',
    'new.field.theme': 'Widget Theme',
    'new.next': 'Next: Select source pages',
    'new.fetchingUrls': 'Fetching URLs...',
    'new.selectStep.desc': 'Select up to 10 pages to crawl from the top 30 URLs closest to the Root URL found in the {name} sitemap.',
    'new.selectStep.selected': 'Selected: {n} / 10',
    'new.selectStep.top10': 'Select top 10',
    'new.selectStep.clear': 'Clear all',
    'new.selectStep.back': '← Back',
    'new.selectStep.create': 'Create project with {n} pages',
    'new.creating': 'Creating...',
    'new.err.urlAndType': 'Please enter the URL and domain type.',
    'new.err.fetchUrls': 'Failed to fetch URL list.',
    'new.err.maxPages': 'You can select up to 10 pages.',
    'new.err.minPages': 'Please select at least 1 page.',
    'new.err.create': 'Failed to create project.',
    // 업종 카테고리 (en)
    'cat.hospital': 'Healthcare',
    'cat.law': 'Legal',
    'cat.edu': 'Education & Counseling',
    'cat.company': 'Company',
    'cat.etc': 'Others',
    // projects/[id].vue — 주요 문구만
    'proj.status.queued': 'Queued',
    'proj.status.crawling': 'In progress',
    'proj.status.generating': 'In progress',
    'proj.status.completed': 'Completed',
    'proj.status.failed': 'Failed',
    'proj.backToList': 'Back to list',
    'proj.btn.regenerate': 'Regenerate',
    'proj.btn.edit': 'Edit',
    'proj.btn.delete': 'Delete',
    'proj.edit.failMsg': 'Regenerate, or contact us at 02-888-9999.',
    'proj.edit.note1': 'Name and URL cannot be changed. Only domain type and widget theme can be changed.',
    'proj.edit.domainType': 'Domain type',
    'proj.edit.theme': 'Widget theme',
    'proj.edit.note2': "After changing the domain type, press 'Regenerate' to recollect based on the new sitemap. Theme changes apply to the widget immediately.",
    'proj.edit.cancel': 'Cancel',
    'proj.edit.save': 'Save',
    'proj.edit.saving': 'Saving...',
    'proj.edit.deleteConfirm': "Delete the project '{name}'?",
    'proj.sources.title': 'Collected sources',
    'proj.btn.preview': 'Preview',
    'proj.qna.title': 'Quick Menus - Automated Questions & Answers',
    'proj.crawl.failed': 'Crawl failed',
    'proj.crawl.failedTitle': 'Crawl failed ({n})',
    'proj.crawl.failedNote': 'Failed pages are retried on regeneration. If failures persist, check the site structure (JS rendering, login, etc.).',
    'proj.menuEdit.title': 'Edit Quick Menu Questions',
    'proj.menuEdit.locked': 'Quick menu questions can be edited only once. Editing has already been completed and cannot be changed.',
    'proj.menuEdit.note': "After editing questions, press 'Regenerate' to create new answers from the collected sources. (No re-crawling · editable once)",
    'proj.menuEdit.loading': 'Loading quick menus...',
    'proj.menuEdit.placeholder': 'Enter a question',
    'proj.menuEdit.regenerating': 'Regenerating...',
    'proj.menuEdit.edited': 'Edit completed',
    'proj.menuEdit.regenerate': 'Regenerate answers',
    'proj.support.title': 'Customer Center Q&A',
    'proj.support.note': 'Ask any questions. Answers will be posted by the administrator.',
    'proj.support.placeholder': 'Enter your question (max 2000 characters)',
    'proj.support.submit': 'Post question',
    'proj.support.submitting': 'Posting...',
    'proj.support.empty': 'No Q&A yet.',
    'proj.support.answered': 'Answered',
    'proj.support.pending': 'Pending',
    'proj.rerun.title': 'Select Source Pages for Regeneration',
    'proj.rerun.fetching': 'Fetching URL list from the sitemap...',
    'proj.rerun.requesting': 'Requesting...',
    'proj.rerun.start': 'Regenerate with {n} selected pages',
    'common.loading': 'Loading...',
    'common.prev': 'Prev',
    'common.next': 'Next',
  },
}

// ── 전역 공유 상태 ──────────────────────────────────────────
// 모듈 스코프에 cache를 두어 모든 컴포넌트가 같은 lang을 공유한다.
// (컴포넌트별 ref는 호출마다 새로 생성되어 페이지 간 동기화가 안 된다)
// Nuxt는 composable을 앱 인스턴스별로 캐시하므로 useState를 쓴다.
let _cached: SiloState | null = null

export function useSilo(): SiloState {
  // useState: SSR/클라이언트 간 공유 + 앱 인스턴스 싱글턴
  const lang = useState<SiloLang>('silo-lang', () => 'ko')
  const ready = useState<boolean>('silo-ready', () => false)

  const load = async () => {
    if (ready.value) return
    try {
      const config = useRuntimeConfig()
      const res: any = await $fetch('/api/silo-info/', { baseURL: config.public.apiBase, credentials: 'include' })
      if (res?.lang && ['ko', 'en'].includes(res.lang)) lang.value = res.lang
    } catch {
      // 실패 시 기본값(ko) 유지
    }
    ready.value = true
  }

  const t = (key: string, params?: Record<string, string | number>): string => {
    const table = MESSAGES[lang.value] || MESSAGES.ko
    let out = table[key] || MESSAGES.ko[key] || key
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        out = out.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      }
    }
    return out
  }

  return { lang, ready, t, load }
}