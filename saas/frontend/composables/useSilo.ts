// 사일로 언어 확인 — 백엔드 /api/silo-info/ 로 현재 사일로의 언어를 가져온다.
// en 사일로(8081)에서는 콘솔 UI가 영어로 표시되고, ko 사일로는 한국어로 표시된다.
export type SiloLang = 'ko' | 'en'

interface SiloState {
  lang: Ref<SiloLang>
  ready: Ref<boolean>
  supportPhone: Ref<string>
  t: (key: string, params?: Record<string, string | number>) => string
  load: () => Promise<void>
}

// ── 콘솔 UI 다국어 사전 ──────────────────────────────────────
// 위젯(webmcp-widget.js)의 I18N과 동일한 규격으로, 콘솔 페이지 문구를 담는다.
const MESSAGES: Record<SiloLang, Record<string, string>> = {
  ko: {
    // 공통 / 레이아웃
    'common.logout': '로그아웃',
    // 랜딩/인증
    'index.tagline': 'URL만 입력하면 AI 비서 위젯이 자동 생성됩니다.',
    'index.cta': '무료로 시작하기',
    'login.title': '로그인',
    'login.email': '이메일',
    'login.password': '비밀번호',
    'login.submit': '로그인',
    'login.signupLink': '회원가입',
    'login.failed': '로그인 실패',
    'signup.title': '회원가입',
    'signup.name': '이름',
    'signup.pwPlaceholder': '비밀번호 (8자 이상)',
    'signup.submit': '가입',
    'signup.failed': '가입 실패',
    'preview.liveTag': '위젯 실시간 미리보기',
    // 대시보드
    'dash.title': '내 프로젝트',
    'dash.adminProjects': '프로젝트 관리',
    'dash.errorReports': '오류 신고',
    'dash.newProject': '새 프로젝트',
    'dash.myAccount': '내 계정',
    'dash.changePw': '비밀번호 변경',
    'dash.planNote': '📌 내 프로젝트는 최대 5개까지 생성할 수 있습니다.',
    'dash.pw.current': '현재 비밀번호',
    'dash.pw.new': '새 비밀번호',
    'dash.pw.newPlaceholder': '8자 이상',
    'dash.pw.confirm': '새 비밀번호 확인',
    'dash.pw.confirmPlaceholder': '새 비밀번호 다시 입력',
    'dash.pw.mismatch': '새 비밀번호가 일치하지 않습니다.',
    'dash.pw.tooShort': '새 비밀번호는 8자 이상이어야 합니다.',
    'dash.pw.changed': '비밀번호가 변경되었습니다.',
    'dash.pw.failed': '비밀번호 변경에 실패했습니다.',
    'dash.pw.changing': '변경 중...',
    'dash.pw.nameLabel': '이름',
    'dash.empty': '등록된 프로젝트가 없습니다.',
    // 프로필 (/profile, /admin/profile)
    'prof.title': '내 프로필',
    'prof.adminTitle': '관리자 프로필',
    'prof.section.account': '계정 정보',
    'prof.section.contact': '연락처',
    'prof.section.billing': '결제 정보',
    'prof.section.support': '문의 연락처 (사이트 대표)',
    'prof.email': '아이디(이메일)',
    'prof.emailNote': '아이디(이메일)는 변경할 수 없습니다.',
    'prof.name': '이름',
    'prof.role': '권한',
    'prof.plan': '플랜',
    'prof.phone1': '대표 전화번호',
    'prof.phone2': '보조 전화번호 (선택)',
    'prof.phoneHint': '오류 안내·고객 문의 시 사용됩니다.',
    'prof.billing.company': '회사명',
    'prof.billing.contact': '결제 담당자',
    'prof.billing.email': '결제 이메일',
    'prof.billing.address': '결제 주소',
    'prof.billing.note': '결제 비고',
    'prof.billing.amount': '월 결제 금액',
    'prof.billing.default': '기본 요금: {price} {currency} / 월',
    'prof.billing.enterprise': '엔터프라이즈 요금이 적용되었습니다.',
    'prof.billing.enterpriseNote': '엔터프라이즈 요금은 관리자가 설정합니다.',
    'prof.billing.gateway': '결제 수단',
    'prof.billing.gatewayPrep': '| PayPal / Stripe 연동 준비 중입니다. 카드 정보는 아직 입력하지 마세요.',
    'prof.supportPhone': '대표 연락처',
    'prof.supportPhoneNote': '위젯 오류 안내 문구에 노출되는 번호입니다. (기본: {default})',
    'prof.save': '저장',
    'prof.saving': '저장 중...',
    'prof.saved': '프로필이 저장되었습니다.',
    'prof.loadFailed': '프로필을 불러오지 못했습니다.',
    'prof.backToDash': '← 대시보드',
    'prof.backToAdmin': '← 관리 화면',
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
    'proj.edit.failMsg': '재생성하거나 문의 {phone}로 연락 주세요.',
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
    // 관리자 페이지 (/admin/projects, /admin/chat-errors)
    'admin.projects.title': '프로젝트 관리',
    'admin.projects.adminProfile': '관리자 프로필',
    'admin.projects.refresh': '새로고침',
    'admin.projects.selectAccount': '계정 선택',
    'admin.projects.selectPlaceholder': '계정을 선택하세요',
    'admin.projects.admin': '(관리자)',
    'admin.projects.phone1': '전화번호 1',
    'admin.projects.phone2': '전화번호 2',
    'admin.projects.monthlyPrice': '월 결제 금액 (비우면 또는 0이면 기본 요금)',
    'admin.projects.pricePlaceholder': '0 = 기본 요금',
    'admin.projects.priceHint': '기본 요금: {price} / 월 — 1 이상을 입력하면 엔터프라이즈 요금, 비우거나 0을 입력하면 기본 요금이 적용됩니다.',
    'admin.projects.save': '저장',
    'admin.projects.saving': '저장 중...',
    'admin.projects.saved': '저장 완료',
    'admin.projects.saveFailed': '저장에 실패했습니다.',
    'admin.projects.noPhone': '연락처 없음',
    'admin.projects.enterprise': '엔터프라이즈',
    'admin.projects.default': '기본',
    'admin.projects.projectsCount': '선택한 계정의 프로젝트 {n}개',
    'admin.projects.searchPlaceholder': '이름 / URL 검색',
    'admin.projects.noProjects': '이 계정의 프로젝트가 없습니다.',
    'admin.projects.stopped': '사용중지',
    'admin.projects.regenerate': 'Q&A 재생성',
    'admin.projects.regenerating': '재생성 중...',
    'admin.projects.disable': '사용중지',
    'admin.projects.enable': '사용재개',
    'admin.projects.processing': '처리 중...',
    'admin.projects.llmSettings': 'LLM 설정',
    'admin.projects.delete': '삭제',
    'admin.projects.llmLoading': 'LLM 설정 불러오는 중...',
    'admin.projects.llmNote': '비워두면 전역(.env) 값을 사용합니다. (OpenRouter는 .env 로만 관리)',
    'admin.projects.geminiKey': 'Gemini API Key',
    'admin.projects.geminiModel': 'Gemini 모델',
    'admin.projects.geminiTest': 'Gemini 키 테스트 후 적용',
    'admin.projects.testing': '테스트 중...',
    'admin.projects.testApply': '테스트 후 적용',
    'admin.projects.resetGlobal': '전역 값으로 초기화',
    'admin.projects.regenerateConfirm': "'{name}' 프로젝트의 Q&A를 재생성하시겠습니까?",
    'admin.projects.regenerateDone': "'{name}' Q&A 재생성 완료 ({n}건)",
    'admin.projects.regenerateFailed': '재생성에 실패했습니다.',
    'admin.projects.toggleConfirm': "'{name}' 프로젝트를 {action}하시겠습니까?",
    'admin.projects.toggleDone': "'{name}' {action} 완료",
    'admin.projects.toggleFailed': '상태 변경에 실패했습니다.',
    'admin.projects.deleteConfirm': "'{name}' 프로젝트를 삭제하시겠습니까?\n삭제된 프로젝트는 복구할 수 없습니다.",
    'admin.projects.deleteDone': "'{name}' 삭제 완료",
    'admin.projects.deleteFailed': '삭제에 실패했습니다.',
    'admin.projects.llmResetConfirm': "'{name}' 프로젝트의 LLM 설정을 초기화해 전역(.env) 값을 사용하도록 되돌리시겠습니까?",
    'admin.projects.llmResetDone': "'{name}' LLM 설정이 전역 기본값으로 초기화되었습니다.",
    'admin.projects.llmLoadFailed': 'LLM 설정을 불러오지 못했습니다.',
    'admin.projects.llmResetFailed': 'LLM 설정 초기화에 실패했습니다.',
    'admin.projects.llmTestOk': '연결 성공 ({model}) — 응답: {reply} (적용됨)',
    'admin.projects.llmTestFailed': '테스트에 실패했습니다.',
    'admin.projects.supportTitle': '고객센터 Q&A ({n}건)',
    'admin.projects.supportNote': '이 계정의 사용자가 올린 질문에 답변을 등록할 수 있습니다.',
    'admin.projects.supportEmpty': '등록된 Q&A가 없습니다.',
    'admin.projects.answerPlaceholder': '답변 내용을 입력하세요',
    'admin.projects.answerSubmit': '답변 등록',
    'admin.projects.answerEdit': '답변 수정',
    'admin.projects.answerSubmitting': '등록 중...',
    'admin.projects.answerRequired': '답변 내용을 입력해주세요.',
    'admin.projects.answerDone': '답변이 등록되었습니다.',
    'admin.projects.answerFailed': '답변 등록에 실패했습니다.',
    'admin.projects.answered': '답변완료',
    'admin.projects.pending': '답변대기',
    'admin.projects.answerHint': '답변하기',
    'admin.projects.selectHint': '계정을 선택하면 해당 계정에서 만든 프로젝트 목록이 표시됩니다.',
    // 관리자 — 챗 오류 신고
    'admin.errors.title': '챗 오류 신고',
    'admin.errors.all': '전체',
    'admin.errors.new': '신규',
    'admin.errors.read': '확인됨',
    'admin.errors.resolved': '해결됨',
    'admin.errors.empty': '신고된 오류가 없습니다.',
    'admin.errors.project': '프로젝트',
    'admin.errors.question': '질문',
    'admin.errors.detail': '오류 상세',
    // 적용 매뉴얼 (/manual)
    'manual.title': '적용 매뉴얼',
    'manual.recommended': '1. 권장 설치 (호스팅 1줄)',
    'manual.bundle': '2. 자체 호스팅 번들',
    'manual.bundleDesc': 'bundle.zip을 홈페이지 루트에 풀고:',
    'manual.origin': '3. Origin 등록',
    'manual.originDesc': '프로젝트 URL의 Origin은 자동 등록됩니다. www/스테이징 도메인은 콘솔에서 추가하세요.',
    'manual.troubleshoot': '4. 문제 해결',
    'manual.ts403': '위젯을 붙인 도메인이 Origin 화이트리스트에 없음',
    'manual.ts429': '플랜 호출 한도 초과',
    'manual.tsCsp': '고객 사이트 CSP에 SaaS 호스트를 script-src에 추가',
  },
  en: {
    // 공통 / 레이아웃
    'common.logout': 'Log out',
    // 랜딩/인증
    'index.tagline': 'Enter your URL and an AI assistant widget is generated automatically.',
    'index.cta': 'Get started free',
    'login.title': 'Log in',
    'login.email': 'Email',
    'login.password': 'Password',
    'login.submit': 'Log in',
    'login.signupLink': 'Sign up',
    'login.failed': 'Login failed',
    'signup.title': 'Sign Up',
    'signup.name': 'Name',
    'signup.pwPlaceholder': 'Password (8+ characters)',
    'signup.submit': 'Sign up',
    'signup.failed': 'Sign up failed',
    'preview.liveTag': 'Widget live preview',
    // 대시보드
    'dash.title': 'My Projects',
    'dash.adminProjects': 'Manage Projects',
    'dash.errorReports': 'Error Reports',
    'dash.newProject': 'New Project',
    'dash.myAccount': 'My Account',
    'dash.changePw': 'Change Password',
    'dash.planNote': '📌 You can create up to 5 projects.',
    'dash.pw.current': 'Current password',
    'dash.pw.new': 'New password',
    'dash.pw.newPlaceholder': '8+ characters',
    'dash.pw.confirm': 'Confirm new password',
    'dash.pw.confirmPlaceholder': 'Re-enter new password',
    'dash.pw.mismatch': 'New passwords do not match.',
    'dash.pw.tooShort': 'New password must be at least 8 characters.',
    'dash.pw.changed': 'Password changed successfully.',
    'dash.pw.failed': 'Failed to change password.',
    'dash.pw.changing': 'Changing...',
    'dash.pw.nameLabel': 'Name',
    'dash.empty': 'No projects yet.',
    // Profile (/profile, /admin/profile)
    'prof.title': 'My Profile',
    'prof.adminTitle': 'Admin Profile',
    'prof.section.account': 'Account',
    'prof.section.contact': 'Contact',
    'prof.section.billing': 'Billing',
    'prof.section.support': 'Support Phone (site-wide)',
    'prof.email': 'ID (email)',
    'prof.emailNote': 'Your ID (email) cannot be changed.',
    'prof.name': 'Name',
    'prof.role': 'Role',
    'prof.plan': 'Plan',
    'prof.phone1': 'Primary phone',
    'prof.phone2': 'Secondary phone (optional)',
    'prof.phoneHint': 'Used in error notices and support inquiries.',
    'prof.billing.company': 'Company',
    'prof.billing.contact': 'Billing contact',
    'prof.billing.email': 'Billing email',
    'prof.billing.address': 'Billing address',
    'prof.billing.note': 'Billing notes',
    'prof.billing.amount': 'Monthly price',
    'prof.billing.default': 'Default price: {price} {currency} / month',
    'prof.billing.enterprise': 'Enterprise pricing is applied.',
    'prof.billing.enterpriseNote': 'Enterprise pricing is configured by the administrator.',
    'prof.billing.gateway': 'Payment method',
    'prof.billing.gatewayPrep': 'PayPal / Stripe integration coming soon. Do not enter card details yet.',
    'prof.supportPhone': 'Support phone',
    'prof.supportPhoneNote': 'Shown in widget error notices. (default: {default})',
    'prof.save': 'Save',
    'prof.saving': 'Saving...',
    'prof.saved': 'Profile saved.',
    'prof.loadFailed': 'Failed to load profile.',
    'prof.backToDash': '← Dashboard',
    'prof.backToAdmin': '← Admin',
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
    'proj.edit.failMsg': 'Regenerate, or contact us at {phone}.',
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
    // Admin pages (/admin/projects, /admin/chat-errors)
    'admin.projects.title': 'Manage Projects',
    'admin.projects.adminProfile': 'Admin Profile',
    'admin.projects.refresh': 'Refresh',
    'admin.projects.selectAccount': 'Select Account',
    'admin.projects.selectPlaceholder': 'Select an account',
    'admin.projects.admin': '(Admin)',
    'admin.projects.phone1': 'Phone 1',
    'admin.projects.phone2': 'Phone 2',
    'admin.projects.monthlyPrice': 'Monthly price (empty or 0 = default)',
    'admin.projects.pricePlaceholder': '0 = default price',
    'admin.projects.priceHint': 'Default price: {price} / month — enter 1+ for enterprise pricing, or leave empty / 0 for the default price.',
    'admin.projects.save': 'Save',
    'admin.projects.saving': 'Saving...',
    'admin.projects.saved': 'Saved',
    'admin.projects.saveFailed': 'Failed to save.',
    'admin.projects.noPhone': 'No phone',
    'admin.projects.enterprise': 'Enterprise',
    'admin.projects.default': 'Default',
    'admin.projects.projectsCount': '{n} projects for the selected account',
    'admin.projects.searchPlaceholder': 'Search name / URL',
    'admin.projects.noProjects': 'No projects for this account.',
    'admin.projects.stopped': 'Disabled',
    'admin.projects.regenerate': 'Regenerate Q&A',
    'admin.projects.regenerating': 'Regenerating...',
    'admin.projects.disable': 'Disable',
    'admin.projects.enable': 'Enable',
    'admin.projects.processing': 'Processing...',
    'admin.projects.llmSettings': 'LLM Settings',
    'admin.projects.delete': 'Delete',
    'admin.projects.llmLoading': 'Loading LLM settings...',
    'admin.projects.llmNote': 'Leave empty to use global (.env) values. (OpenRouter is managed via .env only)',
    'admin.projects.geminiKey': 'Gemini API Key',
    'admin.projects.geminiModel': 'Gemini model',
    'admin.projects.geminiTest': 'Test Gemini key then apply',
    'admin.projects.testing': 'Testing...',
    'admin.projects.testApply': 'Test & Apply',
    'admin.projects.resetGlobal': 'Reset to global values',
    'admin.projects.regenerateConfirm': "Regenerate Q&A for project '{name}'?",
    'admin.projects.regenerateDone': "Q&A regenerated for '{name}' ({n} items)",
    'admin.projects.regenerateFailed': 'Failed to regenerate.',
    'admin.projects.toggleConfirm': "{action} project '{name}'?",
    'admin.projects.toggleDone': "'{name}' {action} completed",
    'admin.projects.toggleFailed': 'Failed to change status.',
    'admin.projects.deleteConfirm': "Delete project '{name}'?\nDeleted projects cannot be recovered.",
    'admin.projects.deleteDone': "'{name}' deleted",
    'admin.projects.deleteFailed': 'Failed to delete.',
    'admin.projects.llmResetConfirm': "Reset LLM settings for '{name}' to global (.env) values?",
    'admin.projects.llmResetDone': "LLM settings for '{name}' reset to global defaults.",
    'admin.projects.llmLoadFailed': 'Failed to load LLM settings.',
    'admin.projects.llmResetFailed': 'Failed to reset LLM settings.',
    'admin.projects.llmTestOk': 'Connected ({model}) — response: {reply} (applied)',
    'admin.projects.llmTestFailed': 'Test failed.',
    'admin.projects.supportTitle': 'Customer Center Q&A ({n})',
    'admin.projects.supportNote': 'Answer questions posted by this account\'s users.',
    'admin.projects.supportEmpty': 'No Q&A yet.',
    'admin.projects.answerPlaceholder': 'Enter an answer',
    'admin.projects.answerSubmit': 'Post answer',
    'admin.projects.answerEdit': 'Edit answer',
    'admin.projects.answerSubmitting': 'Posting...',
    'admin.projects.answerRequired': 'Please enter an answer.',
    'admin.projects.answerDone': 'Answer posted.',
    'admin.projects.answerFailed': 'Failed to post answer.',
    'admin.projects.answered': 'Answered',
    'admin.projects.pending': 'Pending',
    'admin.projects.answerHint': 'Answer',
    'admin.projects.selectHint': 'Select an account to see the projects created by that account.',
    // Admin — chat error reports
    'admin.errors.title': 'Chat Error Reports',
    'admin.errors.all': 'All',
    'admin.errors.new': 'New',
    'admin.errors.read': 'Read',
    'admin.errors.resolved': 'Resolved',
    'admin.errors.empty': 'No error reports.',
    'admin.errors.project': 'Project',
    'admin.errors.question': 'Question',
    'admin.errors.detail': 'Error detail',
    // 적용 매뉴얼 (/manual)
    'manual.title': 'Integration Manual',
    'manual.recommended': '1. Recommended installation (one line on hosting)',
    'manual.bundle': '2. Self-hosted bundle',
    'manual.bundleDesc': 'Unzip bundle.zip into your website root:',
    'manual.origin': '3. Register Origin',
    'manual.originDesc': 'The Origin of your project URL is registered automatically. Add www/staging domains in the console.',
    'manual.troubleshoot': '4. Troubleshooting',
    'manual.ts403': 'The domain hosting the widget is not in the Origin allowlist',
    'manual.ts429': 'Plan call limit exceeded',
    'manual.tsCsp': 'Add the SaaS host to script-src in your site CSP',
  },
}

// ── 전역 공유 상태 ──────────────────────────────────────────
export function useSilo(): SiloState {
  // useState: SSR/클라이언트 간 공유 + 앱 인스턴스 싱글턴
  // 우선순위: 1) 컨테이너 env(NUXT_PUBLIC_SILO_LANG) — SSR 100% 확정
  //          2) 백엔드 /api/silo-info/ 동적 조회 (폴백)
  const lang = useState<SiloLang>('silo-lang', () => {
    const envLang = (useRuntimeConfig().public as any)?.siloLang
    return (envLang === 'en' || envLang === 'ko') ? envLang : 'ko'
  })
  const ready = useState<boolean>('silo-ready', () => false)
  // 사이트 대표 연락처 — 오류 안내 문구(proj.edit.failMsg 등)에서 {phone} 치환용
  const supportPhone = useState<string>('silo-support-phone', () => '')

  const load = async () => {
    // env로 이미 확정된 경우(운영 도커) API 호출 불필요
    const envLang = (useRuntimeConfig().public as any)?.siloLang
    if (envLang === 'en' || envLang === 'ko') {
      if (ready.value) return
      lang.value = envLang as SiloLang
      ready.value = true
      return
    }
    if (ready.value) return
    try {
      const config = useRuntimeConfig()
      const res: any = await $fetch('/api/silo-info/', { baseURL: config.public.apiBase, credentials: 'include' })
      if (res?.lang && ['ko', 'en'].includes(res.lang)) lang.value = res.lang
    } catch {
      // 실패 시 기본값(ko) 유지
    }
    // 대표 연락처는 인증 여부와 무관하게 노출되어야 하므로 별도 실험
    try {
      const config = useRuntimeConfig()
      const res2: any = await $fetch('/api/site-info/', { baseURL: config.public.apiBase, credentials: 'include' })
      if (res2?.supportPhone) supportPhone.value = res2.supportPhone
    } catch {
      // 실패 시 빈 값 유지 → t()에서 기본 번호 사용
    }
    ready.value = true
  }

  const t = (key: string, params?: Record<string, string | number>): string => {
    const table = MESSAGES[lang.value] || MESSAGES.ko
    let out = table[key] || MESSAGES.ko[key] || key
    // {phone} 플레이스홀더 — supportPhone 조회 전이면 백엔드 기본값 사용
    const merged = { ...params }
    if ('phone' in merged) {
      merged.phone = supportPhone.value || String(merged.phone)
    } else if (out.includes('{phone}')) {
      merged.phone = supportPhone.value || '02-888-9999'
    }
    if (Object.keys(merged).length) {
      for (const [k, v] of Object.entries(merged)) {
        out = out.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      }
    }
    return out
  }

  // ── 로케일 헬퍼 ──────────────────────────────────────────
  // 날짜/숫자 포맷을 사일로 언어에 맞춘다. (en 사일로에서 ko-KR 로케일이
  // 그대로 쓰이던 문제 대응)
  const locale = computed(() => (lang.value === 'en' ? 'en-US' : 'ko-KR'))

  /** 사일로 로케일로 날짜·시간을 포맷한다. */
  const formatDate = (
    value: string | number | Date | null | undefined,
    options: Intl.DateTimeFormatOptions = { hour12: false },
  ): string => {
    if (value === null || value === undefined || value === '') return ''
    const d = value instanceof Date ? value : new Date(value)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleString(locale.value, options)
  }

  return { lang, ready, supportPhone, t, load, locale, formatDate }
}