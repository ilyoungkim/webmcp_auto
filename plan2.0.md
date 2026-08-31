# WebMCP Auto 2.0 — 하네스 엔진 기반 완전 자동화 HTML Injection Plan

> **비전 3대 원칙**
> ① **Zero-Mapping** — 개발자가 querySelector·XPath를 수동 작성하지 않는다. 하네스가 DOM Hash를 감지하고 AI가 실시간으로 셀렉터를 재발견·주입한다.
> ② **Hybrid Optimization** — 최초 1회 방문 시 기기 사양이 좋으면 **로컬 sLLM(WebGPU)**, 낮으면 **클라우드 API**가 자동 분담한다. 2회차부터 IndexedDB 캐시 조회로 **AI 호출 0회 · 주입 0ms**.
> ③ **1-Line Install** — 고객 사이트 공통 `<header>`에 `<script>` 1줄만 삽입하면 사이트 전체가 AI 에이전트 대응으로 전환된다.
>
> **하네스(Harness) 엔진**이 페이지 초기 분석 → AI 호출 판단 → 스키마 합성 → DOM 주입 → 실행 검증까지 자율 수행하며,
> 초소형 LLM(sLLM 0.5B~3B)의 장점(온디바이스·무료·프라이버시·오프라인)을 극대화한다.

---

## 0. 1.x → 2.0 차이 한눈에 보기

| 구분 | 1.x (현재 운영: 136 서버/Docker 사일로) | 2.0 (본 플랜) |
|------|--------------------------------------|---------------|
| 핵심 산출물 | 콘솔(Nuxt·Django)에서 크롤→Q&A→위젯 생성 후 **bundle.zip 배포** | 고객 사이트에 **script 1줄** 삽입 → 하네스가 자동 변환 |
| 셀렉터 매핑 | 고객 사이트별 수동 크롤·Q&A 생성 (개발자 개입) | **Zero-Mapping** — AI 실시간 셀렉터 재발견 |
| AI 호출 | 서버(OpenRouter `openai/gpt-oss-120b`) 실시간 | **로컬 sLLM ↔ 클라우드 자동 라우팅** + 캐시 히트 시 0회 |
| 2회차 이후 | 매번 서버 LLM 호출 | **IndexedDB 캐시 → 0ms 즉시 주입, AI 호출 0회** |
| 대상 화면 | 위젯 채팅(빠른메뉴 Q&A) | **모든 폼·예약·장바구니·문진표** (Tool 노출) |
| 레거시 대응 | 대상 아님 | SPA(React/Vue)·PHP/JSP 레거시·쇼핑몰(카페24/고도몰/메이크샵) 전부 |
| 브라우저 | 그대로 | **PC·스마트폰·태블릿 전체 + WebGPU 미지원 폴백 체인** |
| 유지보수 | 프로젝트별 재생성/재빌드 | **Zero** — UI 개편 시 DOM Hash 변화 감지 → AI 재설계 |

---

## 1. 목표 (Goals)

### 1.1 정량 목표 (KPI)

| # | 목표 | 수치 | 측정 방법 |
|---|------|------|----------|
| G1 | 설치 공수 | 사이트당 **script 1줄**(약 60자) | 하네스 부트 로그 |
| G2 | 셀렉터 수동 작업 | **0줄** (Zero-Mapping) | 설정 파일에 작성된 셀렉터 수 = 0 |
| G3 | 2회차 방문 주입 시간 | **0ms** (AI 호출 0회, 캐시 히트) | Performance API + 하네스 텔레메트리 |
| G4 | 최초 분석 시간 | 로컬 ≤ **2초** / 클라우드 ≤ **4초** | 풋프린트 해시 생성→주입 완료 |
| G5 | 폼 자동입력 성공률 | **99%** (Human-in-the-Loop 제외) | Tool execute 결과 수집 |
| G6 | 프레임워크 호환 | React·Vue·jQuery·Vanilla **합성 이벤트 통과율 100%** | MutationObserver 검증 픽스처 |
| G7 | 기기 커버리지 | **전 기기 = 하네스 4모드 동작 + 로컬 sLLM은 §4.3 스펙 이상** | §4 매트릭스 |
| G8 | 월간 운영비 | 캐시 히트율 ≥ 90% 시 클라우드 AI 비용 **1.x 대비 1/10 이하** | usage 집계 |

### 1.2 비목표 (Non-Goals)

- 고객 서버 소스(HTML/PHP/JSP/백엔드) 수정 — 하지 않는다. 외부 JS 주입만으로 완결.
- CAPTCHA·본인인증(PASS/KCP) 해킹적 우회 — Human-in-the-Loop 또는 Agent 전용 창구(`/ai`) 토큰 인증으로 설계적으로 해소.
- 콘솔 SaaS(1.x)의 퇴역 — 2.0은 1.x와 **공존·통합**한다(§2 F10: 하네스 스튜디오).

---

## 2. 기능 정의 (Feature Definition)

### F1. 1-Line Installer
- 고객 공통 템플릿(`header.php`/`layout.html`/`app.vue` 등)에 1줄 삽입:
  ```html
  <script src="https://cdn.webmcp.auto/harness/v2/webmcp-harness.js" data-site="SITE_KEY" defer></script>
  ```
- `data-site` 키만으로 테넌트 식별 → 콘솔에서 발급. CSP 대응 nonce/SRI 옵션 제공.
- 첫 로드 후 하네스는 비동기 idle(priority: idle)로 가동하여 **메인 스레드 블로킹 0** 보장.

### F2. 하네스 엔진 (핵심) — 5단계 파이프라인

```
[0] BOOT   script 1줄 로드 → WebGPU/기기 등급 감지 → 테넌트 키 검증
[1] SCAN   DOM 풋프린트 스캔 (form/input/select/textarea/button/[role=form])
[2] CACHE  페이지 구조 Hash → IndexedDB 조회 (히트 → 3단계로 즉시 스킵, 0ms)
[3] ROUTE  Engine Router: 복잡도 + 기기 등급 → 로컬 sLLM / 클라우드 API 결정
[4] FILL   스키마 합성 → DOM 속성(tool-*) 주입 + navigator.modelContext.registerTool()
[5] GUARD  실행 후 검증(셀렉터 유효성) → 실패 시 1회 재합성 → 이후 클라우드 폴백
```

각 단계는 모듈 분리되어 **독립 교체 가능** — 이것이 "하네스의 유연성"의 정체(§6.1).

### F3. Zero-Mapping (셀렉터 자동 재발견)
- 페이지 구조 요약 HTML(clean footprint, ≤3,000자)에서 **AI가 toolName/description/submitSelector/fields JSON을 생성** (Structured Outputs 강제).
- UI 개편으로 ID/Class가 바뀌어도 DOM Hash가 변하기 때문에 하네스가 **변화를 감지 → 자동 재합성**.
- 개발자가 `webmcp-config.js`에 셀렉터를 쓰는 1.x 방식(수동 JSON)을 **완전 제거**. 오히려 수동 config는 신뢰도 1.0의 "힌트(hint)"로만 선택 입력 가능.

### F4. Hybrid AI Router (로컬 sLLM ↔ 클라우드)
| 조건 | 라우팅 | 엔진 |
|------|--------|------|
| WebGPU 지원 + memory≥8(grade A) + 복잡도 낮음(footprint < 2KB) + 모델 캐시 존재 | 🟢 **로컬** | WebLLM (기본 Qwen2.5-1.5B-Instruct — grade A PC는 SmolLM3-3B, 모바일은 0.5B) |
| Chrome 150+ 내장 AI(window.ai.languageModel) 감지 | 🟢 **로컬(보조)** | Chrome Built-in Gemini Nano (Chromium 전용 — WebLLM 단독 경로의 가속 보조일 뿐) |
| WebLLM 설치 가능 기기에서 복잡도 높음 / 로컬 추론·검증 실패 | 🔵 **클라우드** | OpenRouter `openai/gpt-oss-120b` Structured Outputs (1회 재시도) |
| **WebLLM 설치 불가 기기**(스펙 미달) | ⚪ **보수 모드** | 정적 발견 규칙 — 클라우드 미제공 |
| 오프라인 / 클라우드 장애 | ⚪ **보수 모드** | 정적 발견 규칙(label/aria/name 추론, 필드 description = 원본 label) |

- 로컬/클라우드 결과는 **동일 스키마 규격**(§3.5)이므로 라우팅은 투명하며, 선택 사유를 텔레메트리로 기록.

### F5. 캐시 레이어 (IndexedDB 0ms)
하네스는 브라우저 로컬 DB(IndexedDB)를 **3가지 목적**으로 활용한다.

#### ① WebMCP 스키마 캐시 (기존)
- 키: `pageHash = sha1(host + path + 정규화된 폼 HTML)`, 값: `{schema, createdAt, engine, hitCount}`.
- TTL 정책: 기본 30일 / `hitCount` 높은 인기 스키마 90일 / 셀렉터 검증 실패 시 즉시 폐기.
- 클라우드 스키마는 **서버 측 스키마 공유 캐시**(PostgreSQL 18, 테넌트별 캐시 테이블)에도 적재 → 다른 방문자·다른 기기도 캐시 히트 가능("기기 캐시 + 클러스터 캐시" 2단).

#### ② Q&A 캐시 (질문-답변 로컬 저장)
- 키: `qna:{siteKey}:{questionHash}`, 값: `{question, answer, confidence, createdAt}`.
- **목적**: 1.x 위젯 채팅의 Q&A 유사도 매칭 결과를 로컬에 저장하여, 동일 질문 재발생 시 **서버 호출 없이 즉시 응답**.
- TTL: 7일 / confidence < 0.6 또는 사용자 "오류 신고" 시 즉시 폐기.
- 서버 측 Q&A 업데이트 시 `Cache-Control: no-cache` 헤더 또는 버전 태그로 무효화.

#### ③ WebMCP 원시 데이터 저장 (AI 합성 입력 소재)
- 키: `raw:{pageHash}`, 값: `{cleanFootprint, domSnapshot, extractedFields, scannedAt}`.
- **목적**: DOM 풋프린트·폼 구조 스냅샷·추출된 필드 목록 등 **AI 스키마 합성의 입력 소재를 영속 저장**하여, 오프라인/Context Lost 시에도 재합성 없이 복구하고, 디버깅·텔레메트리·스키마 검수(Harness Studio)에 활용.
- TTL: 90일 / UI 개편 감지(DOM Hash 불일치) 시 자동 갱신.

#### 공통
- 모델 가중치는 WebLLM 내부 Cache API로 브라우저 저장 → 2회차부터 네트워크 다운로드 없이 1~2초 내 엔진 워밍.
- 모든 로컬 DB 데이터는 **테넌트 키(siteKey)로 네임스페이스 분리** → 멀티테넌트 환경에서 데이터 혼재 방지.

### F6. SPA 대응 (MutationObserver + Router 감지)
- `MutationObserver`(childList, subtree) + **디바운스 300ms** — React/Vue 무더기 렌더링에도 스캔 1회로 수렴.
- `history.pushState/replaceState` 모듈 패칭 + `popstate` 리스너로 **React Router/Vue Router/Nuxt 이동 감지**.
- 처리 완료 노드는 `WeakSet` 추적 → 중복 등록 방지 + GC 친화(메모리 누수 0).

### F7. Human-in-the-Loop (캡차/본인인증)
- 스키마 필드에 `requiresHumanInput: true`(캡차), `requiresHumanAuth: true + authTriggerSelector`(PASS 인증 버튼) 선언 가능.
- Tool execute가 일반 필드까지 자동 주입 후 `status: "NEEDS_HUMAN_INPUT"`과 함께 **포커스 이동 + 안내 반환** → 제어권 사용자 전환.
- 위젯 채팅과 연동 시: 사용자가 채팅으로 보안문자를 말해주면 하네스가 이어서 제출하는 **바통 터치** 모드.

### F8. Agent-First 전용 창구 (`/ai`) — 옵션 모듈
- 캡차·주소팝업·본인인증이 구조적으로 불가피한 서비스(병원 예약, 내차팔기 견적)용 **경량 전용 페이지** 생성기.
- `<form tool-name="..." tool-description="...">` + `hidden agent_auth_token`(고정값)만 담은 KB 단위 HTML — 콘솔 1클릭 생성, 하네스와 상호 보완.
- User-Agent 감지 리다이렉트: `WebMCP-Agent|ChatGPT|Claude|Gemini` → `/ai` 하위 대응 페이지 (nginx 규칙 동봉).

### F9. 보안 레이어 (§7 상세)
- Edge(Cloudflare WAF·Rate Limit) → Gateway(HMAC 서명·Nonce) → API(Strict Regex·Sanitization) → Business(알림톡 2차 승인) 4단 구조를 1.x 위젯 프록시에 이식·확장.

### F10. Admin Dashboard (서버측 · 관리자 전용)

서버(Nuxt + Django)에서 동작하는 **관리자 전용 통합 운영 콘솔**. 하네스 엔진 제어, 비즈니스 운영, 시스템 관리를 담당한다. 일반 사용자는 접근 불가(RBAC).

#### A. 엔진 제어 (Engine Control)
| 기능 | 설명 |
|------|------|
| **WebLLM ↔ OpenRouter 스위치** | 서버 측 WebLLM이 OpenRouter(oss-120b)를 호출하는 것을 **enable/disable 토글**. disable 시 로컬 추론만 허용(오프라인 모드), enable 시 클라우드 폴백 활성화. 테넌트별·전역 설정 가능 |
| **모델 선택·버전 관리** | 기본 모델(Qwen2.5-1.5B-Instruct)·모바일(0.5B)·고사양(SmolLM3-3B) 변경, MLC 빌드 버전 업로드·롤백 |
| **구조화 출력 엔진 설정** | XGrammar on/off, temperature·max_tokens 조정, JSON Schema 템플릿 편집 |
| **캐시 정책 관리** | 스키마/Q&A/원시 데이터 TTL 일괄 조정, 강제 무효화(flush), 클러스터 캐시 동기화 트리거 |
| **`/ai` 전용 창구 빌더** | Agent-First 페이지 1클릭 생성·편집·삭제, UA 리다이렉트 규칙 관리 |

#### B. 사용자·접속 관리 (User & Access)
| 기능 | 설명 |
|------|------|
| **사용자 CRUD** | 생성·수정·삭제·비활성화, 역할(admin/operator/viewer) 부여, 비밀번호 초기화 |
| **테넌트(siteKey) 관리** | 발급·삭제·일시중지, 도메인 화이트리스트(Origin), 플랜 할당 |
| **접속 현황 대시보드** | 실시간 활성 세션, DAU/WAU/MAU, 기기/브라우저/grade 분포, 지역별 접속 맵 |
| **인증·보안** | 로그인 이력·실패 로그, IP 화이트리스트, 2FA 설정, 세션 만료 정책, API 키 발급·폐기 |
| **감사 로그(Audit Log)** | 관리자 작업 전 기록(who/when/what), 스키마 승인·모델 변경·설정 수정 추적 |

#### C. 콘텐츠·Q&A 분석 (Content & Q&A Analytics)
| 기능 | 설명 |
|------|------|
| **주요 질문·답변 랭킹** | 인기 질문 Top-N, 저신뢰도 답변 목록, 사용자 오류 신고 큐 |
| **Q&A 품질 모니터링** | confidence 분포, 로컬 캐시 히트 vs 서버 호출 비율, 응답 시간 P50/P95 |
| **스키마 검수** | AI 생성 스키마를 인간이 승인/수정(선택) → 클러스터 캐시에 즉시 반영, 거절 사유 기록 |
| **원시 데이터 브라우저** | 저장된 DOM 풋프린트·폼 스냅샷 조회, 디버깅용 재생성 테스트 |
| **콘텐츠 내보내기** | Q&A·스키마 CSV/JSON 일괄 다운로드, 백업 |

#### D. 성능·sLLM 사용량 (Performance & sLLM Usage)
| 기능 | 설명 |
|------|------|
| **캐시율 대시보드** | 스키마/Q&A/원시 데이터 각각의 히트율, TTL 만료율, 플러시 빈도 |
| **sLLM 사용 통계** | 로컬 추론 횟수·토큰 소비·평균 지연시간, 모델별 분담 비율, grade별 성공률 |
| **클라우드 API 사용량** | oss-120b 호출 횟수·토큰·비용 추정, Rate Limit 도달 빈도 |
| **WebMCP Tool 메트릭** | Tool 등록 수·실행 성공률·평균 주입 시간, Human-in-the-Loop 전환율 |
| **엔진 분담 차트** | 로컬/클라우드/정적 모드 시계열 그래프, 이상 징후 알림 |

#### E. 결제·빌링 (Billing & Payment)
| 기능 | 설명 |
|------|------|
| **플랜 관리** | Free/Pro/Enterprise 플랜 정의, 기능 제한(최대 사이트 수·Q&A 쿼터·모델 선택) |
| **결제 처리** | PayPal/Stripe 연동, 구독 갱신·취소·환불, 인보이스 발행 |
| **사용량 기반 과금** | sLLM 토큰·클라우드 API 호출·저장 용량 초과분 자동 청구 |
| **결제 이력·영수증** | 거래 내역 조회, 세금 계산서, 결제 수단 관리 |
| **엔터프라이즈 계약** | 개별 요금 설정, SLA 약관, 전용 지원 채널 연결 |

#### F. 시스템·일반 Admin (System & General)
| 기능 | 설명 |
|------|------|
| **시스템 헬스** | 백엔드/워커/DB/CDN 상태 모니터, 장애 알림(Slack/Email/Webhook) |
| **설정 관리** | 전역 환경변수, Rate Limit 임계값, HMAC 키 로테이션, CSP/SRI 정책 |
| **로그 뷰어** | Django RequestLog·하네스 텔레메트리 통합 검색, 필터·내보내기 |
| **백업·복원** | DB·캐시·스키마 정기 백업 스케줄, 원클릭 복원 |
| **공지·안내** | 관리자 공지 게시, 유지보수 안내 배너, 버전 업데이트 노트 |
| **권한·RBAC** | 역할 기반 접근 제어, 메뉴/기능 단위 권한, IP 제한 |
| **다국어(i18n)** | Admin UI ko/en 전환, 사일로별 기본 언어 설정 |

---

### F11. User Harness Dashboard (로컬 · 일반 사용자용)

하네스 스크립트가 삽입된 고객 사이트에서 **일반 사용자가 로컬 하네스 상태와 데이터를 확인하는 브라우저 내 대시보드**. 서버가 아닌 **브라우저 로컬에서만 동작**하며, IndexedDB에 저장된 개인 데이터를 열람·관리한다.

#### ⚠️ HTTPS 제약 및 해결 방안

로컬 하네스 대시보드는 브라우저 보안 제약으로 인해 **HTTPS 컨텍스트가 필수**이다.

| 제약 | 원인 | 영향 |
|------|------|------|
| `navigator.modelContext` | WebMCP API가 Secure Context 필수 | HTTP에서는 Tool 등록 불가 |
| IndexedDB | 일부 브라우저가 비보안 컨텍스트에서 제한 | 캐시/원시 데이터 접근 불가 |
| WebGPU/WebLLM | GPU API가 Secure Context 필수 | 로컬 추론 불가 |
| Service Worker | HTTPS 또는 localhost만 허용 | 워커 격리 불가 |

**해결 방안 (3단계 폴백)**:

| 단계 | 방식 | 대상 |
|------|------|------|
| **① 기본** | 고객 사이트가 이미 HTTPS → 하네스 대시보드가 동일 오리진에서 자동 동작 | 대부분의 현대 웹사이트 |
| **② 개발/테스트** | `localhost` / `127.0.0.1` → 브라우저 예외로 Secure Context 인정 | 로컬 개발 환경 |
| **③ HTTP 사이트** | 하네스가 CDN(`https://cdn.webmcp.auto`)에서 서빙되는 **iframe 샌드박스** 내부에서 대시보드 렌더링 → postMessage로 호스트 페이지와 통신 | 레거시 HTTP 사이트 |

> 💡 **핵심**: 하네스 스크립트 자체가 HTTPS CDN에서 로드되므로, 호스트 페이지가 HTTP여도 **하네스 대시보드는 iframe 내에서 Secure Context를 확보**할 수 있다. 단, iframe 간 통신은 `postMessage` + Origin 검증으로 보호한다.

#### A. 사용자 정보 (User Profile)
| 기능 | 설명 |
|------|------|
| **프로필 표시** | 현재 siteKey, 접속 중인 도메인, 브라우저/기기 등급, WebGPU 지원 여부 |
| **세션 상태** | 하네스 부트 시각, 현재 활성 Tool 수, 마지막 스키마 주입 시각 |
| **테넌트 정보** | 소속 사이트명, 플랜(Free/Pro/Enterprise), 남은 쿼터 |

#### B. LLM 설정 (Local LLM Config)
| 기능 | 설명 |
|------|------|
| **현재 모델 표시** | 로드된 모델명(Qwen2.5-1.5B 등), 양자화 수준(q4f16), 가중치 크기 |
| **엔진 상태** | WebLLM 워커 활성 여부, VRAM 사용량, 추론 평균 지연시간 |
| **모델 전환(제한)** | 관리자가 허용한 범위 내에서 로컬 모델 선택 변경 (기본/경량/고품질 프리셋) |
| **오프라인 모드 토글** | 클라우드 호출 차단/허용 (개인 프라이버시 선호 시 로컬 전용) |

#### C. 사용 통계 (Usage Statistics)
| 기능 | 설명 |
|------|------|
| **로컬 추론 통계** | 금일/주간/월간 추론 횟수, 토큰 소비, 평균 응답 시간 |
| **캐시 히트율** | 스키마/Q&A/원시 데이터 각각의 로컬 캐시 히트율 (%) |
| **Tool 실행 이력** | 최근 실행된 Tool 목록, 성공/실패 건수, Human-in-the-Loop 전환 횟수 |
| **엔진 분담** | 로컬/클라우드/정적 모드 비율 파이 차트 |

#### D. 로컬 DB 캐시·색인 (Local Cache & Index Browser)
| 기능 | 설명 |
|------|------|
| **스키마 캐시 목록** | 저장된 pageHash 목록, 각 스키마의 hitCount/TTL/생성 시각, 상세 JSON 보기 |
| **Q&A 캐시 목록** | 저장된 질문-답변 쌍, confidence, 만료 예정일, 삭제(개별/일괄) |
| **원시 데이터 목록** | 저장된 DOM 풋프린트·폼 스냅샷, scannedAt, 재생성 테스트 버튼 |
| **캐시 관리** | 전체 flush, TTL 만료 항목 일괄 삭제, 용량 사용 현황(MB) |
| **데이터 내보내기** | 캐시 데이터 JSON 다운로드 (개인 백업·디버깅용) |
| **검색·필터** | pageHash/question/toolName 기준 검색, 날짜/엔진 타입 필터 |

#### E. 진단·디버그 (Diagnostics)
| 기능 | 설명 |
|------|------|
| **하네스 헬스 체크** | WebGPU/WebLLM/IndexedDB/modelContext 각 컴포넌트 정상 여부 ✅/❌ |
| **텔레메트리 미리보기** | 다음 sendBeacon 전송 예정 데이터 확인 (PII 미포함 검증) |
| **오류 로그** | 최근 하네스 내부 오류 목록, 스택 트레이스, 재시도 횟수 |
| **콘솔 링크** | Chrome DevTools WebMCP Inspector로의 직접 이동 가이드 |

---

## 3. 아키텍처 (Architecture)

### 3.1 전체 시스템 구조도

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [사용자 기기] PC · 스마트폰 · 태블릿 (Chrome/Edge/Safari/Firefox)              │
│  고객 사이트 (레거시 PHP/JSP · React/Vue SPA · 쇼핑몰 솔루션)                 │
│   └─ <script src="…/webmcp-harness.js" data-site="KEY" defer>  ← 1줄 설치   │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ ① 페이지 스캔 → 풋프린트 Hash
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    🧠 WebMCP HARNESS ENGINE (브라우저 상주)                 │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐  ┌────────────┐  ┌─────────┐ │
│  │ Scanner │→ │ CacheEng │→ │ EngineRouter│→ │ SchemaGen  │→ │ Injector│ │
│  │ (DOM)   │  │ (IDB)    │  │ (A/B/C/D)   │  │(local/cloud)│ │ (inject)│ │
│  └─────────┘  └──────────┘  └──────┬──────┘  └─────┬──────┘  └────┬────┘ │
│        ▲                           │ miss          │              │      │
│        │        SPA 감지(MutationObserver/History) │              │      │
│        └───────────────────────────┘               │              │      │
▼ 히트 시 즉시                                       │ miss         │      │
 [IndexedDB 0ms 주입]                ┌───────────────┘              │      │
                                    │ 🟢 로컬 sLLM (WebLLM·WASM 주력 / Chrome Nano 보조)│
                                    │ 🔵 ────────────────────────────▶─── ┘
                                    │      ② HTML 풋프린트     ③ JSON Schema
└───────────────────────────────────┼──────────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ [Edge] Cloudflare WAF · Rate Limit(5r/m·IP) · Bot 차단                    │
│ [Gateway] Nginx — HMAC 서명 검증(X-Agent-Signature/Timestamp/Nonce)         │
│ [Backend] Django 5.2 + DRF — POST /api/webmcp/analyze-dom                 │
│    ├─ Structured Outputs 강제 → 규격 JSON만 반환                            │
│    ├─ 스키마 검증·Sanitization → 클러스터 캐시 저장                           │
│    └─ LLM: OpenRouter openai/gpt-oss-120b (Structured Outputs, WebLLM 기기 한정)    │
│ [DB] PostgreSQL 18 (스키마 캐시 · 텔레메트리 · 테넌트)                       │
│ [Business] 카카오 알림톡 2차 승인 (Pending → CONFIRMED)                     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 하네스 엔진 핵심 역할 — 자원 격리 기반 런타임 수명주기 오케스트레이터

하네스는 단순한 "스키마 생성기"가 아니라, **자원 격리 기반의 런타임 수명주기 오케스트레이터**로 정의한다.
모바일 브라우저는 메모리가 극도로 제한적이고 하드웨어 자원 경쟁이 치열하며, 신뢰할 수 없는 동적 코드 실행(Injection)을 보안상 엄격히 차단하기 때문이다.
이를 위해 하네스가 수행하는 **4대 핵심 역할**은 다음과 같다.

#### ① WebWorker 기반 자원 분할 · 쓰레드 오케스트레이션 (Resource Orchestration)
- **문제**: 메인 쓰레드(UI)에서 WebLLM 모델을 로드하거나 WebMCP 코드를 생성하면 화면이 즉시 프리즈(Freeze)된다.
- **역할**: `ServiceWorkerMLCEngine`/`WebWorkerMLCEngine` 인터페이스를 제어해 **추론 쓰레드(WebLLM Worker)와 UI 런타임을 물리적으로 분리**한다.
- **작동**: 무거운 WebGPU 연산과 온디바이스 모델 가중치(Llama/Gemma 등) 캐싱은 백그라운드 워커에 격리하고, 메인 쓰레드는 사용자 UI/렌더링에만 집중하도록 자원 흐름을 중재한다. 부트 스크립트는 `requestIdleCallback` 기반 지연 가동으로 초기 페이로드를 최소화한다.

#### ② 엄격한 Sandboxing 기반 동적 코드 주입 안전망 (Secure Injection Safeguard)
- **문제**: WebLLM이 생성한 WebMCP 코드를 활성 페이지에 실시간 주입하는 것은 심각한 **XSS 취약점**을 유발할 수 있다.
- **역할**: 생성된 명령형(Imperative) API 코드가 메인 DOM이나 민감 세션(쿠키·토큰)을 오염시키지 않도록 **실행 환경 가드레일**을 제공한다.
- **작동**: `Origin-Agent-Cluster` 등 오리진 격리 요구를 준수하며, 생성 코드를 **하네스 내부 가상 샌드박스에서 1차 컴파일·검증**한 뒤, 안전성이 확인된 **도구(Tools) 프로토콜 데이터만** 브라우저 WebMCP 레지스트리에 등록(`allow="tools"`)한다. 스키마 실존 검증(§6.4) 통과 시에만 주입한다.

#### ③ 구조화 출력 보장 · WebMCP JSON 스키마 변환 (Structured Schema Mapping)
- **문제**: 온디바이스 sLLM은 서버급 대비 추론 능력이 낮아 **환각(규칙 밖 코드 생성) 확률**이 높고, WebMCP는 표준 HTML/JS 구조를 명확한 JSON Schema로 요구한다.
- **역할**: WebLLM 출력을 **XGrammar 등 구조화 출력(Structured Output) 엔진**과 결합해, 반드시 WebMCP 규격에 맞는 JS/HTML 속성 구조만 나오도록 제한한다.
- **작동**: 모델의 자유 텍스트 출력을 차단하고, **현재 페이지 UI 상태(DOM 컴포넌트 정보)를 컨텍스트로 주입**하여 해당 페이지에 정확히 호환되는 `tool-name`/`tool-description` 속성 코드를 실시간 빌드한다. `temperature 0.1` + "JSON만 출력, 마크다운/사족 금지" 지시문으로 결정론적 출력을 유도한다.

#### ④ 모바일 환경 최적화 상태 관리 · 폴백 제어 (Mobile Context & Lifecycle Management)
- **문제**: 모바일 브라우저는 탭 전환·백그라운드 이동 시 메모리 확보를 위해 **GPU 컨텍스트를 강제 해제(Context Lost)** 해버린다.
- **역할**: WebLLM의 VRAM 상태와 주입된 실시간 도구의 라이프사이클을 **영속적으로 감시·관리**한다.
- **작동**: GPU 메모리 해제·네트워크 단절(오프라인)에도 **IndexedDB(기기 캐시)에 스키마·Q&A·원시 데이터(풋프린트/DOM 스냅샷)를 동기화**하여 상태를 보존하고, WebLLM 추론 지연·실패 시 **저장된 원시 데이터로 재합성 시도 → 실패 시 하드코딩된 기본 WebMCP 폼 요소(선언적 API)로 즉시 복구**하는 2단계 폴백 메커니즘을 가동한다.

#### 지원 기능 (상기 4대 역할을 뒷받침하는 하네스 기본 기능)

| 기능 | 내용 |
|------|------|
| **페이지 초기 분석** (Scanner) | 대화형 요소 전수 수집 → clean footprint(≤3,000자) → `pageHash = sha1(host+path+정규화 폼 HTML)` — UI 개편 감지(Zero-Mapping) 기준값 |
| **하네스 실행** (Engine Router) | 기기 등급(A/B/C/D) + 복잡도 산정 → 캐시→로컬→클라우드(oss-120b)→정적 폴백 사다리(§6.4) |
| **DOM 주입** (Injector) | `tool-*` 속성 기록(선언형) + `registerTool()` 호출(명령형) — 선언·명령 양면 지원 |
| **실행 검증** (Executor + Guard) | Native Value Setter + `input/change/blur` 합성 이벤트, `radio/checkbox/select/hidden(fixed)` 분기, submit 트리거 |
| **캐시** (CacheEngine) | 기기(IndexedDB) → 클러스터(PostgreSQL) 2단, 2회차 0ms·AI 0회(§2 F5) |
| **SPA·Human 감지** (spa-watcher/hithl) | MutationObserver+300ms 디바운스·History 패칭·WeakSet 중복 방지, 캡차 바통터치(§2 F6·F7) |

> 🎯 **요약**: 모바일 웹 환경의 WebLLM + WebMCP 구조에서 하네스는 **"GPU 자원을 쥐어짜 오동작 없는 WebMCP 코드를 뽑아내고, 이를 브라우저 보안 필터를 통과시켜 안전하게 페이지에 주입하는 오케스트레이터이자 가드레일"**이다.

#### 성능 타협 포인트 (구글 WebMCP 제약 수용)

구글은 WebMCP를 **실험 단계(Chrome 150+ "WebMCP for testing" 플래그)**로 제한하며, 브라우저 보안상 동적 코드 실행·오리진 격리·메인 쓰레드 연산을 엄격히 차단한다. 이 제약을 수용하는 대신, 하네스는 아래 지점에서 **정확도·속도 일부를 양보**하고 **가용성·안전성을 우선**한다.

| 구글 제약 | 하네스 타협 | 양보하는 것 | 확보하는 것 |
|-----------|-------------|-------------|-------------|
| 동적 `eval`/임의 코드 실행 차단 | **구조화 출력(JSON 모드) 강제** — 자유 텍스트 생성 포기, XGrammar로 스키마만 허용 | 토큰 +20~30%, 추론 +0.3~0.5s(1.5B 기준) | 환각 코드 0, XSS 원천 차단 |
| 메인 쓰레드 연산 제한(UI 프리즈) | **WebWorker 격리 필수** — 구조적 클론(메시지 직렬화) 오버헤드 수용 | 모델 로딩·통신 지연(초기 1~2s) | UI 프리즈 없음, 백그라운드 추론 |
| `Origin-Agent-Cluster` / `allow="tools"` | **선언형 HTML 속성 주입 위주** + 검증 통과 도구만 등록 | 임의 명령형 코드 실행 포기 | 오리진 격리·도구 등록 안전성 |
| 모바일 GPU Context Lost(강제 해제) | **선언형/정적 폴백 우선** — 0.5B 실패 시 정적 규칙으로 다운그레이드 | 로컬 정확도 일부 하락 | 탭 전환·백그라운드·오프라인에도 비손상 |
| WebMCP 실험 플래그(Chromium 한정) | **WebLLM 주력(크로스브라우징)** — 명령형 API는 Chromium 한정으로 수용 | Chromium 외 브라우저는 명령형 API 미지원 | Edge/Safari/Firefox 공통 온디바이스 |

- **원칙**: "성능보다 가용성·안전성 우선" — 구글 제약이 걸린 지점에서는 **동작 보장(정적/선언형 폴백)** 을 최우선하고, 성능(속도·정확도)은 그다음 우선순위로 배치한다.

### 3.3 하네스 엔진 내부 모듈 (ES Module 단일 번들, 지연 로드)

| 모듈 | 책임 | 크기 목표 |
|------|------|----------|
| `scanner` | 대화형 요소 수집, 풋프린트 정제(script/style/svg/img/iframe 제거), Hash 생성 | ≤ 3KB gzip |
| `cache` | IndexedDB 래퍼(기기 캐시) + 클러스터 캐시 API 클라이언트 | ≤ 2KB |
| `router` | WebGPU 지원·VRAM 힌트·복잡도·배터리(옵션) 기반 라우팅 결정 | ≤ 2KB |
| `local-engine` | **WebLLM 로더(WebGPU+WASM — Edge·Safari·Firefox 크로스브라우징 주력)** · Chrome window.ai 어댑터(Chromium 보조) | 동적(모델 제외) |
| `cloud-engine` | Structured Outputs 요청·재시도·폴백 체인 | ≤ 2KB |
| `schema` | LLM 출력 JSON 검증(AJV 대경량 자체 검증기), required/type 정규화 | ≤ 2KB |
| `injector` | tool-* 속성 주입 + `navigator.modelContext / document.modelContext` registerTool + execute 런타임 | ≤ 6KB |
| `executor` | 합성 이벤트 주입(Native Setter·input/change/blur dispatch), radio/checkbox/select 처리, submit 트리거 | ≤ 4KB |
| `spa-watcher` | MutationObserver·History 패칭·WeakSet 추적 | ≤ 2KB |
| `telemetry` | 성능·성공률 배치 전송(sendBeacon), PII 미수집 | ≤ 2KB |
| `hithl` | 캡차·본인인증 제어권 전환, 채팅 바통 터치 | ≤ 2KB |

- 부트 스크립트(`harness.js`)는 scanner/cache/router/injector만 즉시 로드(≈15KB gzip), 나머지는 필요 시 동적 import → **최초 페이로드 최소화**. 전체 번들 합계 ≤30KB gzip(모델 가중치 제외).

### 3.4 데이터 흐름: 1회 방문 vs 2회 방문

```
[1회 방문] SCAN(50ms) → CACHE MISS → ROUTE → ENGINE(로컬 ≤2s·기본 1.5B 기준 / 클라우드 ≤4s)
        → INJECT → GUARD 검증 → 캐시 저장(기기+클러스터) → 텔레메트리

[2회 방문] SCAN(50ms) → CACHE HIT → INJECT(**0ms**) → 완료  (AI 호출 0회)
   └ UI 개편 감지: DOM Hash 불일치 → 자동으로 1회 방문 경로 재실행(Zero-Mapping)
```

### 3.5 WebMCP Tool 스키마 규격 (하네스 공통 계약)

```json
{
  "toolName": "submit_yonza_counsel_diagnosis",
  "description": "담당 상담사(448) 진단 문진표를 작성하고 상담을 신청합니다.",
  "submitSelector": "#diagForm button[type=submit]",
  "formSelector": "#diagForm",
  "fields": [
    { "name": "introcounselor", "selector": "input[name=introcounselor]",
      "type": "fixed", "description": "담당 상담사 고유 코드 (448 고정값, 변경 금지)" },
    { "name": "q1_status", "selector": "input[name=q1_status]",
      "type": "radio", "valueMap": { "1": "여드름/트러블", "2": "색소/기미", "3": "탄력/주름" },
      "description": "주요 고민 증상 선택", "required": true },
    { "name": "privacy_agree", "selector": "input[name=privacy_agree]",
      "type": "checkbox", "onValue": "Y", "required": true,
      "description": "개인정보 수집 동의 (필수 'Y')" },
    { "name": "captcha_code", "selector": "#captchaCode", "type": "text",
      "requiresHumanInput": true, "description": "화면의 보안문자 4~6자리 (사용자 직접 입력)" }
  ],
  "meta": { "engine": "local|cloud|static",
            "pageHash": "…", "schemaVersion": "2.0", "confidence": 0.94 }
}
```

- 1.x 위젯의 `tool-*` 선언 속성 표준과 상호 호환: 주입 시 DOM에 `tool-name/tool-description/tool-param-description`을 역시 기록 → 선언적·명령형 API **양면 지원**.
- `valueMap`은 radio/선택값 매핑(1.x 문진표 규칙), `type: fixed`는 hidden 고정값 보호(1.x `isFixed` 계승).

---

## 4. 디바이스/브라우저 지원 매트릭스

### 4.1 대상 환경 (2026 최신)

| 디바이스 | 브라우저 | 최소 버전 | WebGPU | 동작 모드 |
|----------|----------|----------|--------|----------|
| PC (Windows/macOS) | Chrome / Edge | 150+ | ✅ | **A: 로컬 sLLM 우선** |
| PC | Safari | 18+ (Sonoma 14+) | ✅ | A (Safari GPU 제한 시 B로 자동 전환) |
| PC | Firefox | 141+ | ✅(desktop) | A/B |
| 스마트폰/태블릿 (Android) | Chrome | 150+ | ✅(일부) | A/B (RAM < 6GB → B/C 강등) |
| 스마트폰/태블릿 (iPhone/iPad) | Safari | iOS 17+ | 부분 | **B: WebLLM(0.5B WASM) 시도 → 클라우드/C 폴백** |
| 구형 기기/브라우저 (WebLLM 미설치) | 전체 | — | ❌ | **C: 정적/보수 모드 Only** (클라우드 미제공) |
| 오프라인/네트워크 차단 | 전체 | — | — | **D: 보수 모드(정적 규칙)** |

### 4.2 기기 등급 산정 (Engine Router 입력)

```
grade A → WebGL/WebGPU 어댑터 info(devicePCIeArchitecture 등) + navigator.deviceMemory ≥ 8 → 로컬 우선 (기본 Qwen2.5-1.5B-Instruct, 고사양 PC는 SmolLM3-3B 선택)
grade B → WebGPU ✅, deviceMemory 4~7, 모바일 → 로컬(0.5B) 시도 후 실패 시 클라우드(oss-120b)
grade C → WebLLM 설치 불가(WebGPU ❌ 또는 RAM < 4, 스펙 미달) → 클라우드 미제공, 정적/보수 모드
grade D → fetch 실패/오프라인 → 정적 발견 규칙(aria-label·label·placeholder·name 추론)
```

- 스마트폰은 iOS/Android 모두 **하네스 자체는 100% 동작**(모든 모드에서 Tool 등록·주입은 가능) — 등급은 "AI 엔진 선택"에만 영향.

### 4.3 최소 하드웨어 스펙 (로컬 sLLM 구동 기준)

| 디바이스 | 최소 하드웨어 | 비고 |
|----------|--------------|------|
| 스마트폰 (Android) | **Galaxy S24 (Exynos 2400) 이상** | WebGPU 가속 + 8GB RAM 이상 |
| 스마트폰 (iPhone) | **iPhone 15 Pro (A17 Pro) 이상** | iOS 17+ WebGPU 부분 지원 |
| 태블릿 (Android) | **Snapdragon 8 Gen 3 이상** | 8GB RAM 이상 권장 |
| 태블릿 (iPad) | **Apple M1 이상** (iPad Pro M1 / iPad Air M1) | WebGPU 데스크톱급 가속, 8GB RAM 이상 |
| PC | WebGPU 지원 + 8GB RAM 이상 | GPU/드라이버 최신 |

- 위 스펙 미달 기기는 **grade C** 로 강등되어 로컬 sLLM과 **클라우드(oss-120b) 모두 미제공** — 정적/보수 모드로만 동작한다 (하네스 자체 주입은 여전히 100% 동작). 클라우드 폴백은 **WebLLM 설치 가능 기기**(상기 스펙 이상)에 한해 제공한다.

---

## 5. SW 스택 (최신 버전 구성)

| 레이어 | 기술 | 버전 (2026 최신) | 비고 |
|--------|------|-----------------|------|
| 하네스 코어 | TypeScript(ES2023)+Vanilla, Vite 빌드 | Vite 7 / TS 5.x | 프레임워크 미종속(vanilla 강점 유지) |
| 로컬 sLLM | WebLLM (@mlc-ai/web-llm) | 최신 | **기본 Qwen2.5-1.5B-Instruct** (데스크톱) · 모바일 Qwen2.5-0.5B · 고사양 PC 한정 SmolLM3-3B(선택) — 전부 q4f16 양자화 |
| 내장 AI (보조) | Chrome Built-in AI (window.ai.languageModel) | Chrome 150+ | Chromium 전용 **보조 가속**(주력 아님) — 미감지 시 WebLLM 단독 경로 |
| 모델 검증 | 자체 경량 검증기 | — | Structured Output 수신 즉시 검증 |
| 클라우드 LLM | OpenRouter `openai/gpt-oss-120b` | — | Structured Outputs/JSON 모드 — **WebLLM 설치 가능 기기 한정** 폴백 (전 기기 제공 아님) |
| 백엔드 | Django + DRF | Django 5.2 LTS | 1.x 코드베이스 확장(신규 앱 `apps/harness`) |
| DB | PostgreSQL | 18 | 스키마 캐시·텔레메트리(1.x silo PG18 동일) |
| 캐시 | IndexedDB / PostgreSQL / (선택) Redis 8 | 최신 | 2단 캐시(기기+클러스터) |
| CDN | Cloudflare (WAF·Bot Management·Rate Limit) | — | Edge 보안 1단 |
| Gateway | Nginx | stable 1.28+ | HMAC 검증, UA 리다이렉트 |
| 위젯/웹MCP | navigator.modelContext (명령형) + tool-* (선언형) | Chrome 150+ | 1.x `webmcp.js v2.1` 계승 |
| 쇼핑몰 어댑터 | 카페24/고도몰/메이크샵 셀렉터 프리셋 사전 | 상시 갱신 | 자동감지(detector) + 폴백 셀렉터 |
| 관측성 | 하네스 텔레메트리(sendBeacon) + Django RequestLog 확장 | — | 엔진 분담·성공률 KPI |

---

## 6. 하네스 엔진 상세 설계

### 6.1 "강력한 유연성"의 4가지 설계 원리

1. **모듈 분리·교체 가능** — 각 단계(scanner/cache/router/generator/injector/executor)는 독립 모듈. 로컬 엔진을 새 sLLM으로 갈아끼우거나 클라우드 프로바이더를 교체해도 다른 모듈 무수정.
2. **2중 규격(선언형+명령형) 동시 지원** — AI가 만든 스키마는 (a) DOM에 `tool-*` 속성으로 주입되고 (b) `registerTool`로 등록됨. Chrome WebMCP Inspector(문서.modelContext)로도 검증 가능.
3. **레벨별 확장 포인트** — 페이지 주입 시 `siteKey`별 힌트(수동 config·쇼핑몰 프리셋·valueMap)를 "우선 참고" 계층으로 얹음: `수동 config → 솔루션 프리셋 → AI 합성 → 보수 모드` 순 폴백 사다리.
4. **계약 불변(Contract Stability)** — 스키마 규격(§3.5)은 `schemaVersion` 관리. UI가 바뀌어도 계약은 유지 → 고객 측 변경 0.

### 6.2 Engine Router 의사결정 로직

```text
if (cacheHit)                          → 주입 후 종료 (0ms)
else if (WebLLM 설치 가능 && memory>=8 && complexity<2KB && modelCached) → LOCAL(WebLLM·WASM)
else if (window.ai?.languageModel && complexity<2KB)                   → LOCAL(Chrome AI — Chromium 보조)
else if (WebLLM 설치 가능)             → LOCAL(WebLLM·WASM) 시도 → 실패/검증실패 → CLOUD(oss-120b) (1회)
else                                   → STATIC(정적 규칙) — WebLLM 미설치 기기는 클라우드 미제공
on offline / CLOUD 실패                → STATIC(정적 규칙, confidence 낮음 표기)
```

- **LOCAL 주력 엔진은 WebLLM(WebGPU+WASM) 단일 경로** — `window.ai`(Chrome 내장)는 Chromium 한정 실험 API이므로 "존재하면 보조 가속"일 뿐, 기본 로컬 경로는 WebLLM 하나로 통일한다. 이로써 Chrome·Edge·Safari·Firefox가 **동일한 온디바이스 처리 경로**를 갖는다(크로스브라우징 주력 = window.ai 비의존).
- **클라우드(oss-120b)는 WebLLM 설치 가능 기기 한정 폴백** — WebLLM 미설치 기기(스펙 미달)는 클라우드를 제공하지 않고 정적/보수 모드로만 동작한다.
- 모든 결정은 `meta.engine`으로 스키마에 기록되어 텔레메트리에서 **분담 비율**이 집계됨 (G8/KPI).

### 6.3 sLLM 장점 극대화 전략

| 전략 | 내용 | 효과 |
|------|------|------|
| **크로스브라우징 주력(WebLLM)** | `window.ai` **미의존** — WebLLM(WebGPU+WebAssembly) 단일 경로로 Edge/Safari/Firefox 공통 온디바이스 구동 | Chrome 의존 배제, 전 현대 브라우저 동일 처리 |
| **기본 모델(데스크톱)** | **Qwen2.5-1.5B-Instruct** q4f16 — 다국어(한국어 포함)·정확도·속도 균형 | PC/태블릿 데스크톱 기본 경로 |
| **초지극량화 모델(모바일)** | Qwen2.5-0.5B q4f16 — 모바일 WebGPU에서 크래시 없이 구동 | 스마트폰 로컬 처리 가능 |
| **고사양 전용(선택)** | grade A(PC·deviceMemory ≥ 8) 한정 **SmolLM3-3B** — 3B SoTA·도구호출(xml_tools/python_tools) 우수 | 고성능 PC 스키마 품질 향상 |
| **DOM 풋프린트 축소** | script/style/svg/img 제거 + 공백 정규화 + 3,000자 캡핑 | 프롬프트 토큰 -90%, 추론 속도 ↑ |
| **온도 최소화** | temperature 0.1 + 지시문 "JSON만 출력, 마크다운/사족 금지" | 결정론적 스키마, 파싱 실패율 최소 |
| **Few-shot 1회 포함** | 모델 카드 캐시 시 시스템 프롬프트에 예시 1개 첨부(선택) | 0.5B 출력 정확도 보정 |
| **캐시 2단** | 기기(IndexedDB) → 클러스터(서버) 순 조회 | 재방문·타기기 모두 **AI 호출 0회** |
| **프라이버시** | 로컬 추론 시 폼 데이터가 기기를 떠나지 않음 | 의료·법률 등 민감 도메인 우위 |
| **오프라인/저비용** | 클라우드 키 없이도 D 모드 동작 | 소형 고객 온보딩 장벽 제거 |

> ⚠️ **SmolLM3-3B 언어 한계**: 6개 유럽어(영·프·스·독·이·포)만 지원하고 **한국어는 미지원** → 한국어 `description` 생성은 Qwen2.5 계열 또는 클라우드가 담당한다. SmolLM3는 구조/셀렉터 파싱 보조 또는 영어(en) 사일로 한정으로만 사용한다.

### 6.4 신뢰성 체인 (폴백 사다리)

```text
수동 config(선택) → 쇼핑몰 프리셋 → 로컬 sLLM → 클라우드(oss-120b, WebLLM 기기 한정) → 정적 규칙 → Tool 등록 스킵(조용히 종료)
```

- 각 단계 결과는 **셀렉터 실존 검증**(document.querySelector로 fields/submitSelector 존재 확인) 통과 시에만 채택.
- 검증 실패 시 다음 단계로 폴백하고, 최종 실패해도 페이지 동작에 영향 0(비침입 원칙).

---

## 7. 보안 설계

### 7.1 4단 보안 구조 (Agent 전용 창구 및 API 공통)

```
[1 Edge]     Cloudflare WAF — DDoS·Bot 차단, Rate Limit(IP당 5r/m, burst 2)
[2 Gateway]  Nginx — HMAC 서명(X-Agent-Timestamp·X-Agent-Signature·Nonce, 5분 유효, Replay 차단)
             UA 감지 리다이렉트(WebMCP-Agent|ChatGPT|Claude|Gemini → /ai)
[3 API]      Strict Validation — phone: ^01[016789]\d{7,8}$, Prepared Statement, XSS Sanitizer
             CORS/Origin 화이트리스트 (1.x TenantOrigin 계약 재사용)
[4 Business] Pending 저장 → 카카오 알림톡/SMS 확인 링크 2차 승인 → CONFIRMED
             (가짜 번호·매크로 스팸·타인 명의 도용 근본 차단)
```

### 7.2 하네스 스크립트 자체 보안
- SRI 해시 + 서브리소스 무결성, `data-site` 키 도메인 결합(타 도메인 탈취 사용 방지).
- 텔레메트리는 PII 미수집(페이지 경로 해시만), CSP 친화(채용 시 nonce 주입 가이드 제공).
- 고정 토큰(`agent_auth_token`)은 클라이언트 노출이 전제된 **1차 검증**이며 실제 승인은 4단 알림톡 확정으로 대체 — 1.x의 보안 교훈(브루트포스·IP화이트리스트)과 일관.

---

## 8. 성능 목표 (버짓)

| 항목 | 로컬(A) | 클라우드(C) | 캐시 히트 |
|------|---------|-------------|----------|
| 최초 스크립트 페이로드 | ≤15KB gzip | 동일 | 동일 |
| 스키마 합성 지연 | ≤2.0s(기본 1.5B 기준) | ≤4.0s | **0ms** |
| AI 토큰 소비(폼 1회) | 0 (기기) | 입력 ≤2K/출력 ≤800 tokens | 0 |
| 재방문 모델 로드 | 1~2s(가중치 캐시) | 0 | 0 |
| 실행 후 성공률 | 99% | 99% | 99% |

- 클라우드(C) 열은 oss-120b 기반이며 **WebLLM 설치 가능 기기에 한해** 적용된다 (스펙 미달 기기는 정적/보수 모드).

---

## 9. 마일스톤 (6주 로드맵)

| 주차 | 범위 | 산출물 |
|------|------|--------|
| W1 | PoC 코어 — scanner+cache+injector+executor, 정적 규칙 모드 | 단일 폼(문진표) 0ms 주입 데모 |
| W2 | 로컬 엔진 — **WebLLM(WebGPU+WASM) 주력** + Chrome window.ai 보조 통합, Engine Router v1, **Qwen2.5-1.5B/0.5B MLC 빌드 검증** | grade A/B 기기 로컬 합성 성공 |
| W3 | 클라우드 엔진 — `/api/webmcp/analyze-dom` Structured Outputs, 클러스터 캐시 | 로컬↔클라우드 폴백 E2E |
| W4 | SPA·쇼핑몰 — MutationObserver/History 패칭, 카페24·고도몰·메이크샵 프리셋 | React/Vue 데모 + 쇼핑몰 데모 통과 |
| W5 | 보안·Agent 창구 — HMAC·Rate Limit·알림톡 2차, `/ai` 빌더 | 4단 보안 E2E, UA 리다이렉트 |
| W6 | Harness Studio — 콘솔 통합(키 발급·텔레메트리·스키마 검수), 문서 | **v2.0 GA** (136/Render 배포 준비) |

- 1.x 인프라(136 서버, docker-compose.silo, Django/Nuxt, PG18, Gemini 키)를 **그대로 확장** 사용 — 인프라 중복 투자 없음.

---

## 10. 리스크 및 대응

| # | 리스크 | 영향 | 대응 |
|---|--------|------|------|
| R1 | 모바일 iOS WebGPU 미지원/메모리 제한 | 로컬 불가 | 등급 C 강등 → 정적/보수 모드(클라우드 미제공), WebLLM 설치 가능 시 0.5B 이하 모델만 |
| R2 | **모바일 0.5B 모델**의 셀렉터 오류 | 잘못된 값 주입 | 셀렉터 실존 검증 + 클라우드 재합성 1회 + confidence 임계 |
| R3 | 대형 WAF 사이트(CAPTCHA) | 자동화 차단 | Human-in-the-Loop + `/ai` 토큰 창구(설계적 해소) |
| R4 | SPA 극한 최적화(가상화 리스트) | 스캔 누락 | 디바운스+WeakSet+라우트별 재스캔, 실패 시 보수 모드 |
| R5 | 캐시 스키마 부패(UI 개편) | 실패율 ↑ | Hash 재계산 자동 감지 → 재합성, 클러스터 캐시 즉시 갱신 |
| R6 | 하네스 남용(스팸 접수) | 운영 피해 | 4단 보안 + 테넌트별 Rate Limit + 알림톡 확정 플로우 |
| R7 | Chrome window.ai 명세 변동 | 로컬 계획 차질 | WebLLM 독립 채널 유지(로컬 엔진 이원화) |
| R8 | CDN 장애 | 하네스 로드 실패 | 셀프호스팅 번들(bundle.zip) 병행 배포 옵션 |

---

## 11. 1.x 자산 재사용 맵

| 1.x 자산 | 2.0 활용 |
|----------|----------|
| `saas/widget-dist/webmcp.js v2.1` (registerTool, 불가 브라우저 폴링) | 하네스 `injector`의 Tool 등록 코어 계승 |
| `tool-name/tool-description/tool-param-description` 변환 규칙(radio valueMap·hidden 고정값·동의 체크) | `schema` 규격의 필드 타입/매핑 표준으로 그대로 채택 |
| `apps/proxy` Origin 화이트리스트·쿼터·RequestLog | 하네스 API 게이트 보안/계측으로 확장 |
| 쇼핑몰 셀렉터 매핑 연구(카페24/고도몰/메이크샵) | 프리셋 사전(detector + fallback selector) 신설 |
| CAPTCHA 병원 예약 바통 터치·`/ai` Agent 창구 RFC | F7·F8 그대로 구현 |
| SPA 하네스 스니펫(MutationObserver·History 패칭·WeakSet·디바운스) | `spa-watcher` 모듈로 승격 |
| IndexedDB 캐시·WebLLM 로더·window.ai 어댑터 프로토타입 | `cache`·`local-engine` 모듈의 프로덕션화 |
| OpenRouter `openai/gpt-oss-120b` (1.x Q&A 배치 엔진) | 클라우드 엔진(WebLLM 기기 한정 폴백)으로 재사용 |