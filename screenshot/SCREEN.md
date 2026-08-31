# 기능 테스트 스크린샷 (2026-08-31)

ko/en 두 언어 사일로에서 **개인 사용자(`tensun@naver.com`)** 와 **관리자(`admin@local`)** 로
주요 기능을 실제로 실행하며 캡처한 화면 모음이다. 각 사일로는 완전히 격리된 브라우저
세션(ko: 8080, en: 8081)으로 테스트했다.

- **ko 사일로**: http://127.0.0.1:8080 (Docker `webmcp-ko-*` 스택)
- **en 사일로**: http://127.0.0.1:8081 (Docker `webmcp-en-*` 스택)
- 테스트 계정: 개인 `tensun@naver.com` / 10dlfdud, 관리자 `admin@local` / test1234

---

## 1. 공통 — 로그인 화면

### `ko-login.png` — 한국어 로그인
![ko-login](ko-login.png)

**한국어 로그인 화면.** 이메일·비밀번호 입력과 "회원가입" 링크. CSRF 쿠키 기반 세션 로그인 (SECURE_COOKIES 스위치로 http 환경에서도 쿠키 저장).

### `en-login.png` — 영어 로그인 화면
![en-login](en-login.png)

**영어 로그인 화면.** "Log in" / "Sign up" — 같은 코드베이스지만 `NUXT_PUBLIC_SILO_LANG=en` 주입으로 랜딩·인증 UI 전체가 영어로 렌더링된다.

> 같은 URL 경로(`/login`)이며 UI 문구가 사일로 언어를 따르는 것 = useSilo(또는 SSR env) 기반 i18n의 기본 동작 확인.

## 2. 개인 사용자 (tensun@naver.com) — ko 사일로

### `ko-user-01-dashboard.png` — 내 프로젝트 (대시보드)
![ko-user-01-dashboard](ko-user-01-dashboard.png)

- 로그인 직후 랜딩 화면. 헤더에 `+ 새 프로젝트`와 우상단 계정 메뉴(👤 tensun@naver.com ▾).
- 소유 프로젝트 3개가 카드 목록으로 표시: **에이아키**, **럽디**, **생생병원** — 각 카드에 사이트 URL과 진행 상태(`완료 100%`), `수정`/`삭제` 버튼.
- 상단 안내 문구 `📌 내 프로젝트는 최대 5개까지 생성할 수 있습니다.` = free 플랜 한도(5개) 노출.

### `ko-user-02-project-detail.png` — 프로젝트 상세 (생생병원)
![ko-user-02-project-detail](ko-user-02-project-detail.png)

파이프라인 완료 후 사용자가 보는 핵심 화면. 화면 순서대로:
1. **헤더**: 프로젝트명·상태 배지(`완료 100%`), `재생성`·`수정`·`삭제` 액션.
2. **수집된 소스 정보 (10)**: 크롤러가 수집한 실제 URL 10건 목록(제목+원문 링크). 목록을 클릭하면 선택 소스로 Q&A 재생성이 possible.
3. **미리보기 링크** (`👁 미리보기`) — 동일 오리진 iframe으로 실제 위젯을 띄운다.
4. **빠른메뉴 — 자동화된 질문 및 답변**: 도메인 카탈로그(병원 유형) 기반 5개 메뉴(병원정보/의료진/치료방법/연락처/**AI비서란?**)가 각각 접힌 `<details>`로 표시. `AI비서란?`은 필수 메뉴로 **편집 불가** 고정 답변.
5. **✏️ 빠른메뉴 질문 편집**: 질문을 **1회만** 수정할 수 있는 잠금 정책 UI.
6. **고객센터 Q&A**: 사용자가 질문을 등록 → 관리자 답변 확인 (2000자 제한 카운터).
7. **읽어볼 내용**: 이용약관 / AI 이용고지 / 개인정보처리방침 / 프로그램 사용동의 아코디언 — 한국어 정식 문서.

### `ko-user-03-preview-widget.png` — 위젯 미리보기 (런처 닫힘)
![ko-user-03-preview-widget](ko-user-03-preview-widget.png)
- Django `/preview/3/`가 iframe으로 서빙하는 데모 페이지. `미리보기` 배지와 안내 문구(우하단 💬 버튼)가 한국어.
- 모바일 대응: `viewport-fit=cover` + 하단 safe-area 여백 (스마트폰에서 런처가 가려지던 문제 수정 반영).
- 우하단 **AI 런처 버튼**(✦ 스파크 포함)이 정상 표출.

### `ko-user-04-profile.png` — 내 프로필
![ko-user-04-profile](ko-user-04-profile.png)

개인 사용자의 계정·연락처·결제 정보 화면:
- **계정 정보**: 아이디(이메일)는 변경 불가(disabled), 이름 수정 가능. 비밀번호 변경(현재/새/확인 3필드, 미입력 시 버튼 disabled).
- **연락처**: 대표·보조 전화번호 2개 — 오류 안내·고객 문의에 사용.
- **결제 정보**: 월 결제 금액 **50,000원** (ko 사일로 기본가, KRW). `💳 결제 수단: PayPal / Stripe — 연동 준비 중` 안내. 회사명/담당자/이메일/주소/비고 입력란.
- 관리자가 이 계정의 `monthly_price`를 지정하면 이 화면의 표시 금액이 바뀐다(기본가 override).

### `ko-user-05-new-project.png` — 새 프로젝트 1단계
![ko-user-05-new-project](ko-user-05-new-project.png)

- URL 입력 + **업종 카테고리** 5개(🏥 병원 / ⚖️ 법률 / 🎓 교육및상담 / 🏢 일반회사 / 📦 기타) 선택 카드.
- 카테고리 선택 시 **세부 유형** 드롭다운이 해당 언어 사일로의 카탈로그(한국어 27종 중 해당 카테고리)로 채워진다.
- **위젯 테마 선택**: Blue Sky / Red Orange / White Snow / Banana Pink / Black Neon 5종 (CSS 변수 기반 테마).

### `ko-user-06-dashboard-final.png` — 대시보드 (재방문)
![ko-user-06-dashboard-final](ko-user-06-dashboard-final.png)

- 세션 유지 상태에서의 대시보드. 프로젝트 상태가 카드별로 `완료 100%` 표시되는 것을 재확인.

## 3. 관리자 (admin@local) — ko 사일로

### `ko-admin-01-dashboard.png` — 관리자 대시보드
![ko-admin-01-dashboard](ko-admin-01-dashboard.png)
- 개인 사용자와 동일한 레이아웃이지만 **`🛠 프로젝트 관리` / `📮 오류 신고`** 관리자 전용 링크가 추가로 노출.
- admin@local은 소유 프로젝트가 없어 "등록된 프로젝트가 없습니다" 상태 (계정 소유 기준 목록이므로 정상).

### `ko-admin-02-admin-projects.png` — 프로젝트 관리 (진입)
![ko-admin-02-admin-projects](ko-admin-02-admin-projects.png)
- 전체 사용자 프로젝트를 관리하는 화면. 상단 **계정 선택** 드롭다운:
  - `admin@local (관리자) — 50,000원 (기본)`
  - `tensun@naver.com — 50,000원 (기본)`
- 계정별로 **기본 요금(ko 50,000원)** 이 라벨에 바로 표시된다. 계정을 선택해야 해당 계정의 프로젝트 목록이 로드된다.

### `ko-admin-03-billing-panel.png` — 사용자별 결제/연락처 설정 (계정 선택 후)
![ko-admin-03-billing-panel](ko-admin-03-billing-panel.png)

이번 세션의 핵심 기능:
- **tensun@naver.com 선택 시** 즉시 결제 패널이 펼쳐진다.
- 표시 값: **50,000원 (기본)** / 연락처 없음.
- 입력란: `Phone 1` / `Phone 2` (오류 안내 문구용 번호), `Monthly price` 숫자 입력 + **통화 콤보(KRW(원) / USD($))**.
- 안내 문구: 기본가 50,000원/월, **숫자를 1 이상 입력하면 엔터프라이즈 요금**, 빈 값 또는 **0 입력 시 기본 요금으로 복귀** 규칙 설명.
- 하단에 해당 계정의 프로젝트 목록(카테고리·상태 배지) + **Q&A 재생성 / 사용중지 / ⚙ LLM 설정 / 삭제** 액션과 고객센터 Q&A 답변 영역.

### `ko-admin-04-admin-profile.png` — 관리자 프로필
![ko-admin-04-admin-profile](ko-admin-04-admin-profile.png)
- 개인 프로필에 **`문의 연락처 (사이트 대표)`** 섹션이 추가된 형태. 여기서 수정한 대표 번호(`02-888-9999`)는 **위젯 오류 안내 문구**에 실시간 반영된다(SiteSetting → `/api/site-info/` 공개 API → useSilo `{phone}` 플레이스홀더).
- 그 아래 계정 정보/비밀번호/연락처/결제 정보는 개인 프로필과 동일 구성.

### `ko-admin-05-chat-errors.png` — 오류 신고 관리
![ko-admin-05-chat-errors](ko-admin-05-chat-errors.png)
- 위젯 방문자가 `📮 오류 신고하기`로 접수한 ChatErrorReport 목록(상태: 접수/처리 완료 토글).
- 현재 케이스가 없어 빈 상태("신고된 오류가 없습니다").

### `ko-admin-06-django-admin.png` — Django admin
![ko-admin-06-django-admin](ko-admin-06-django-admin.png)
- `/django-admin/` — Django 관리자 화면(인증 및 권한/그룹 등).
- 브라우저 캡처 시점에 `/static/admin/*` 정적 파일이 JSON MIME으로 내려오는 이슈가 관찰됨(스타일 미적용). **콘솔 UI 사용에는 영향 없음** — 필요 시 `collectstatic` 서빙 설정 개선 과제.

## 4. 개인 사용자 (tensun@naver.com) — en 사일로

### `en-user-01-dashboard.png` — My Projects
![en-user-01-dashboard](en-user-01-dashboard.png)
- 제목 **My Projects**, 안내 `📌 You can create up to 5 projects.` — en 사일로 카피가 영어로 표시.
- 소유 프로젝트 5개: **delta dentalins / realtor / autolist / edmunds / stanfordhealthcare**.
- 프로젝트 상태 배지가 한국어가 아닌 **`Completed 100%` / `Failed 10%`** 로 렌더링 — STATUS_LABELS가 useSilo computed로 언어 전환되는 부분 확인.
- edmunds 실패 건에는 안내 문구 `Regenerate, or contact us at 02-888-9999.` — 오류 시 지원 연락처 자동 노출.

### `en-user-02-project-detail.png` — Project Detail (stanfordhealthcare)
![en-user-02-project-detail](en-user-02-project-detail.png)
- ko 화면과 동일 구성이지만 모두 영어: 소스 목록 **Collected sources (10)**, 설치 안내는 **Installation & Usage** 영어 컴포넌트(`InstallGuideEn.vue`), 정적 문서는 **Terms & Policies** 영어 컴포넌트(`TermsEn.vue` — 이용약관/AI Disclosure/Privacy Policy/Program Use Agreement).
- Quick menus: About / Doctors / Treatments / Contact / **About AI Assistant** (필수 메뉴의 영어 라벨).
- 고객센터 Q&A 영어 문구("Ask a question…", 0/2000 카운터).

### `en-user-03-preview-widget.png` — 위젯 미리보기 (런처 닫힘)
![en-user-03-preview-widget](en-user-03-preview-widget.png)
- 배지 **Preview**, 안내 `Check the AI assistant with the 💬 button at the bottom-right.` — `preview_html()`의 en 분기 문구.
- ko와 동일한 데모 레이아웃/런처 위치로 **언어만 다름** → 사일로 격리 + UI 공통 구조 확인.

### `en-user-04-profile.png` — My Profile
![en-user-04-profile](en-user-04-profile.png)
- **월 결제 금액 $49** (en 사일로 기본가, USD). ko(50,000원)와 같은 화면이 `DEFAULT_MONTHLY_PRICE={'ko':('KRW',50000),'en':('USD',49)}`로 갈라짐.
- 라벨 전체 영어: ID (email) / Name / Change Password / Primary phone / Billing 등 — useSilo prof.* 키 적용.
- 통화 표기도 `$49` 로케일 연동(이번 커밋의 `fmtPrice` 로케일 분기 결과).

### `en-user-05-new-project.png` — New Project
![en-user-05-new-project](en-user-05-new-project.png)
- Industry Category 5개(**Healthcare / Legal / Education & Counseling / Company / Others**) + Widget Theme 5종 — 카탈로그 27종이 영어로 노출되는 것의 진입점.
- 업종별 세부 유형은 Company 선택 시 15개(Chemical, Biotech, Healthcare, Pharma, Electronics, Logistics, Research, Investment, Consulting, Knowledge, Tech, Sales, Construction, Retail, Company) 영어 라벨.

### `en-user-06-widget-open.png` — 위젯 열림 (영어 UI)
![en-user-06-widget-open](en-user-06-widget-open.png)
- 미리보기에서 AI 런처 클릭 → 패널 오픈.
- 헤더 제목 **stanfordhealthcare AI Assistant** (config.title en 분기), 상태 배지 **✅ Connected**, Quick menu pills(About/Doctors/Treatments/Contact/About AI Assistant), 입력 placeholder **Type a message...**, 런처 라벨 **Voice input**, `⚙️ How it works` — 전부 위젯 I18N 사전(32키)에서 가져온 영어.
- 시간 표시 `09:48 AM` — 위젯 시계도 사일로 로케일(`en-US`) 적용.

### `en-user-07-widget-answer.png` — 위젯 실시간 대화 (영어 답변)
![en-user-07-widget-answer](en-user-07-widget-answer.png)
- 입력창에 "What treatments does Stanford Healthcare offer?" 직접 전송 → LLM 응답 수신.
- 답변이 **영어 마크다운**(bold 섹션 + 불릿)으로 생성되고 **실제 사이트 정보만 인용**: Emergency Department 911 / Express Care / Primary Care / Specialized Treatments, 예약 방법(MyHealth Portal 링크, **650-498-3333**, **GuestServices@stanfordhealthcare.org**).
- = en 사일로 system_prompt + 프록시(`/api/chat/`) + 서버 부착 지식 요약 파이프라인이 end-to-end 동작.

## 5. 관리자 (admin@local) — en 사일로

### `en-admin-01-dashboard.png` — Admin Dashboard
![en-admin-01-dashboard](en-admin-01-dashboard.png)
- **🛠 Manage Projects / 📮 Error Reports** 링크, 본인 프로젝트 1개(Stanford Healthcare, Completed 100%) — 개인 대시보드와 동일 구성에 관리 링크만 추가된 모습.

### `en-admin-02-admin-projects.png` — Manage Projects (진입)
![en-admin-02-admin-projects](en-admin-02-admin-projects.png)
- 계정 선택 드롭다운이 영어로 표시: `admin@local (Admin) — $49 (Default)` / `tensun@naver.com — $49 (Default)`.
- 안내 문구 `Select an account to see the projects created by that account.` — admin.projects.* 키 적용.

### `en-admin-03-billing-panel.png` — 결제/연락처 설정 (en)
![en-admin-03-billing-panel](en-admin-03-billing-panel.png)
- tensun@naver.com 선택 → 결제 패널 영어 버전:
  - **$49 (Default)**, Phone 1/Phone 2, Monthly price 입력 + 통화 콤보(**KRW(원) / USD($)** — 옵션 라벨은 통용 목적으로 한글 유지).
  - 설명 문구 `Default price: $49 / month — enter 1+ for enterprise pricing, or leave empty / 0 for the default price.` — 0 입력 시 기본 복귀 규칙까지 영어로 안내.
- 하단 프로젝트 목록 5건(Delta Dentalins=**Dental**/Completed, realtor=**Real Estate**, autolist=**Retail**, edmunds=Retail/**Failed**, stanfordhealthcare=**Hospital**) — 이번 카탈로그 대칭화(27종)로 en에 추가된 도메인 배지가 그대로 보임.
- **Customer Center Q&A (0)** — 관리자가 답변 등록하는 영역도 영어화.

### `en-admin-04-admin-profile.png` — Admin Profile
![en-admin-04-admin-profile](en-admin-04-admin-profile.png)
- 문의 연락처 섹션(**Support contact**) + 개인 계정/비밀번호/연락처/Billing 편집 — ko 관리자 프로필과 1:1 대응의 영어판.

### `en-admin-05-chat-errors.png` — Error Reports
![en-admin-05-chat-errors](en-admin-05-chat-errors.png)
- 오류 신고 관리 화면 — 빈 상태 문구 영어(`admin.errors.empty` = "No error reports."). 프로젝트/질문/상세 컬럼 라벨 포함.

### `en-admin-06-manual.png` — Integration Manual (`/manual`)
![en-admin-06-manual](en-admin-06-manual.png)
- **영어 전용 매뉴얼 페이지**. 1) Recommended installation(한 줄 스크립트) 2) Self-hosted bundle(bundle.zip 구성 코드) 3) Register Origin 4) Troubleshooting(403/429/CSP 해설).
- 이전에는 한글 고정이던 `/manual`이 useSilo `manual.*` 10키로 사일로 언어를 따르게 된 직접적인 결과(=이번 i18n 개선의 대표 사례).

---

## 테스트에서 확인된 핵심 동작 요약

1. **언어 격리 완성** — 같은 코드베이스를 2개 컨테이너로 띄우고 `WEBMCP_LANG`/`NUXT_PUBLIC_SILO_LANG`만 달리 했을 때, 로그인→대시보드→프로젝트→위젯→프로필→관리 전 구간 UI가 완전히 해당 언어로 동작한다.
2. **요금 체계 사일로 분리** — ko 50,000원/KRW vs en $49/USD, 관리자가 특정 계정의 금액(엔터프라이즈)을 지정하면 개인 프로필에도 그 값이 반영된다.
3. **en 위젯 LLM 응답 품질** — 실제 크롤링 지식 기반의 영어 마크다운 답변 + 실제 연락처/링크 인용(지어내기 금지 프롬프트 정상 동작).
4. **역할 분리** — 사용자는 자기 프로젝트/프로필만, 관리자는 전체 사용자의 결제·연락처·프로젝트·Q&A·오류 신고를 관리.
5. **모바일 대응** — 미리보기 페이지 safe-area/하단 여백이 적용되어 런처가 콘텐츠와 겹치지 않는다.

## 관측된 사소한 이슈 (기능 영향 없음)

- `ko-admin-06-django-admin.png`: Django admin 정적 파일(`static/admin/*`)이 `application/json` MIME으로 응답되어 스타일이 깨져 보임 — 향후 nginx/collectstatic 서빙 점검 과제.
- 세션 CSRF 만료 후 재로그인이 한 번 실패했다가 성공(정상 동작 — 페이지 새로고침으로 CSRF 쿠키 재발급).