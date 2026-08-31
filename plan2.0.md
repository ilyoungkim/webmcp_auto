# WebMCP Auto 2.0 — 하네스 엔진 기반 완전 자동화 HTML Injection Plan

> **비전 3대 원칙**
> ① **Zero-Mapping** — 개발자가 querySelector·XPath를 수동 작성하지 않는다. 하네스가 DOM Hash를 감지하고 AI가 실시간으로 셀렉터를 재발견·주입한다.
> ② **Hybrid Optimization** — 최초 1회 방문 시 기기 사양이 좋으면 **로컬 sLLM(WebGPU)**, 낮으면 **클라우드 API**가 자동 분담한다. 2회차부터 IndexedDB 캐시 조회로 **AI 호출 0회 · 주입 0ms**.
> ③ **1-Line Install** — 고객 사이트 공통 `<header>`에 `<script>` 1줄만 삽입하면 사이트 전체가 AI 에이전트 대응으로 전환된다.
>
> **하네스(Harness) 엔진**이 페이지 초기 분석 → AI 호출 판단 → 스키마 합성 → DOM 주입 → 실행 검증까지 자율 수행하며,
> 초소형 LLM(sLLM 0.5B~1B)의 장점(온디바이스·무료·프라이버시·오프라인)을 극대화한다.

---

## 0. 1.x → 2.0 차이 한눈에 보기

| 구분 | 1.x (현재 운영: 136 서버/Docker 사일로) | 2.0 (본 플랜) |
|------|--------------------------------------|---------------|
| 핵심 산출물 | 콘솔(Nuxt·Django)에서 크롤→Q&A→위젯 생성 후 **bundle.zip 배포** | 고객 사이트에 **script 1줄** 삽입 → 하네스가 자동 변환 |
| 셀렉터 매핑 | 고객 사이트별 수동 크롤·Q&A 생성 (개발자 개입) | **Zero-Mapping** — AI 실시간 셀렉터 재발견 |
| AI 호출 | 서버(Gemini 3.5 Flash Lite / OpenRouter) 실시간 | **로컬 sLLM ↔ 클라우드 자동 라우팅** + 캐시 히트 시 0회 |
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
| G7 | 기기 커버리지 | WebGPU 등급 A/B/C/D **전 기기 4모드 동작** | §4 매트릭스 |
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
| WebGPU 지원 + 복잡도 낮음(footprint < 2KB) + 모델 캐시 존재 | 🟢 **로컬** | WebLLM (Qwen 0.6B q4f16 등) |
| Chrome 150+ 내장 AI(window.ai.languageModel) 감지 | 🟢 **로컬** | Chrome Built-in Gemini Nano |
| WebGPU 미지원 / 복잡도 높음 / 로컬 추론 실패 | 🔵 **클라우드** | 하네스 백엔드 Structured Outputs API |
| 로컬 성공이나 셀렉터 검증 실패 | 🔵 **클라우드 폴백** | 동일 API (1회 재시도) |
| 오프라인/클라우드 장애 | ⚪ **보수 모드** | 정적 발견 규칙(label/aria/name 추론, 폼은 Tool로 등록하되 필드 description = 원본 label) |

- 로컬/클라우드 결과는 **동일 스키마 규격**(§3.4)이므로 라우팅은 투명하며, 선택 사유를 텔레메트리로 기록.

### F5. 캐시 레이어 (IndexedDB 0ms)
- 키: `pageHash = sha1(host + path + 정규화된 폼 HTML)`, 값: `{schema, createdAt, engine, hitCount}`.
- TTL 정책: 기본 30일 / `hitCount` 높은 인기 스키마 90일 / 셀렉터 검증 실패 시 즉시 폐기.
- 클라우드 스키마는 **서버 측 스키마 공유 캐시**(PostgreSQL 18, 테넌트별 캐시 테이블)에도 적재 → 다른 방문자·다른 기기도 캐시 히트 가능("기기 캐시 + 클러스터 캐시" 2단).
- 모델 가중치는 WebLLM 내부 Cache API로 브라우저 저장 → 2회차부터 네트워크 다운로드 없이 1~2초 내 엔진 워밍.

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

### F10. 하네스 스튜디오 (1.x 콘솔 통합)
- 기존 Nuxt 콘솔에 "**Harness Studio**" 신설:
  - 사이트 키 발급/삭제, 도메인 화이트리스트(Origin 1.x 계약 재사용)
  - 실시간 텔레메트리 대시보드: 페이지당 캐시 히트율·엔진 분담(로컬/클라우드)·Tool 실행 성공률·폴백 사유
  - 스키마 검수 화면: AI 생성 스키마를 인간이 승인/수정(선택) → 클러스터 캐시에 즉시 반영
  - `/ai` 전용 창구 빌더, 보안 규칙(Rate Limit·알림톡 확정 플로우) 설정

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
                                    │ 🟢 로컬 sLLM (WebLLM/Gemini Nano)   │
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
│    └─ LLM: Gemini 3.5 Flash Lite(1차) / OpenRouter 폴백 (1.x 엔진 재사용)    │
│ [DB] PostgreSQL 18 (스키마 캐시 · 텔레메트리 · 테넌트)                       │
│ [Business] 카카오 알림톡 2차 승인 (Pending → CONFIRMED)                     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 하네스 엔진 내부 모듈 (ES Module 단일 번들, 지연 로드)

| 모듈 | 책임 | 크기 목표 |
|------|------|----------|
| `scanner` | 대화형 요소 수집, 풋프린트 정제(script/style/svg/img/iframe 제거), Hash 생성 | ≤ 3KB gzip |
| `cache` | IndexedDB 래퍼(기기 캐시) + 클러스터 캐시 API 클라이언트 | ≤ 2KB |
| `router` | WebGPU 지원·VRAM 힌트·복잡도·배터리(옵션) 기반 라우팅 결정 | ≤ 2KB |
| `local-engine` | WebLLM 로더(동적 import)·Chrome window.ai 어댑터 | 동적(모델 제외) |
| `cloud-engine` | Structured Outputs 요청·재시도·폴백 체인 | ≤ 2KB |
| `schema` | LLM 출력 JSON 검증(AJV 대경량 자체 검증기), required/type 정규화 | ≤ 2KB |
| `injector` | tool-* 속성 주입 + `navigator.modelContext / document.modelContext` registerTool + execute 런타임 | ≤ 6KB |
| `executor` | 합성 이벤트 주입(Native Setter·input/change/blur dispatch), radio/checkbox/select 처리, submit 트리거 | ≤ 4KB |
| `spa-watcher` | MutationObserver·History 패칭·WeakSet 추적 | ≤ 2KB |
| `telemetry` | 성능·성공률 배치 전송(sendBeacon), PII 미수집 | ≤ 2KB |
| `hithl` | 캡차·본인인증 제어권 전환, 채팅 바통 터치 | ≤ 2KB |

- 부트 스크립트(`harness.js`)는 scanner/cache/router/injector만 즉시 로드(≈15KB gzip), 나머지는 필요 시 동적 import → **최초 페이로드 최소화**.

### 3.3 데이터 흐름: 1회 방문 vs 2회 방문

```
[1회 방문] SCAN(50ms) → CACHE MISS → ROUTE → ENGINE(로컬 2s / 클라우드 4s)
        → INJECT → GUARD 검증 → 캐시 저장(기기+클러스터) → 텔레메트리

[2회 방문] SCAN(50ms) → CACHE HIT → INJECT(**0ms**) → 완료  (AI 호출 0회)
   └ UI 개편 감지: DOM Hash 불일치 → 자동으로 1회 방문 경로 재실행(Zero-Mapping)
```

### 3.4 WebMCP Tool 스키마 규격 (하네스 공통 계약)

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
| 스마트폰/태블릿 (iPhone/iPad) | Safari | iOS 17+ | 부분 | **B: Chrome AI + 캐시 / 폴백** |
| 구형 기기/브라우저 | 전체 | — | ❌ | **C: 클라우드 Only** |
| 오프라인/네트워크 차단 | 전체 | — | — | **D: 보수 모드(정적 규칙)** |

### 4.2 기기 등급 산정 (Engine Router 입력)

```
grade A → WebGL/WebGPU 어댑터 info(devicePCIeArchitecture 등) + navigator.deviceMemory ≥ 8 → 로컬 우선
grade B → WebGPU ✅, deviceMemory 4~7, 모바일 → 로컬(0.5B) 시도 후 실패 시 클라우드
grade C → WebGPU ❌ 또는 RAM < 4 → 클라우드 즉시
grade D → fetch 실패/오프라인 → 정적 발견 규칙(aria-label·label·placeholder·name 추론)
```

- 스마트폰은 iOS/Android 모두 **하네스 자체는 100% 동작**(모든 모드에서 Tool 등록·주입은 가능) — 등급은 "AI 엔진 선택"에만 영향.

---

## 5. SW 스택 (최신 버전 구성)

| 레이어 | 기술 | 버전 (2026 최신) | 비고 |
|--------|------|-----------------|------|
| 하네스 코어 | TypeScript(ES2023)+Vanilla, Vite 빌드 | Vite 7 / TS 5.x | 프레임워크 미종속(vanilla 강점 유지) |
| 로컬 sLLM | WebLLM (@mlc-ai/web-llm) | 최신 | **Qwen3-0.6B / Qwen2.5-0.5B / Llama-3.2-1B q4f16**, 모바일은 0.5B 이하 강제 |
| 내장 AI | Chrome Built-in AI (window.ai.languageModel) | Chrome 150+ | 감지되면 최우선 로컬 엔진 |
| 모델 검증 | 자체 경량 검증기 | — | Structured Output 수신 즉시 검증 |
| 클라우드 LLM | Gemini 3.5 Flash Lite (1.x 재사용) + OpenRouter 폴백 | — | Structured Outputs/JSON 모드 |
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
4. **계약 불변(Contract Stability)** — 스키마 규격(§3.4)은 `schemaVersion` 관리. UI가 바뀌어도 계약은 유지 → 고객 측 변경 0.

### 6.2 Engine Router 의사결정 로직

```text
if (cacheHit)                → 주입 후 종료 (0ms)
else if (navigator.gpu && memory>=8  && complexity<2KB && modelCached) → LOCAL
else if (window.ai?.languageModel && complexity<2KB)                    → LOCAL(Chrome AI)
else if (navigator.gpu && !mobile)  → LOCAL 시도 → 실패/검증실패 → CLOUD (1회)
else                        → CLOUD
on offline / CLOUD 실패      → STATIC(정적 규칙, confidence 낮음 표기)
```

- 모든 결정은 `meta.engine`으로 스키마에 기록되어 텔레메트리에서 **분담 비율**이 집계됨 (G8/KPI).

### 6.3 sLLM 장점 극대화 전략

| 전략 | 내용 | 효과 |
|------|------|------|
| **초지극량화 모델** | 0.5B q4f16 — 모바일 WebGPU에서 크래시 없이 구동 | 스마트폰 로컬 처리 가능 |
| **DOM 풋프린트 축소** | script/style/svg/img 제거 + 공백 정규화 + 3,000자 캡핑 | 프롬프트 토큰 -90%, 추론 속도 ↑ |
| **온도 최소화** | temperature 0.1 + 지시문 "JSON만 출력, 마크다운/사족 금지" | 결정론적 스키마, 파싱 실패율 최소 |
| **Few-shot 1회 포함** | 모델 카드 캐시 시 시스템 프롬프트에 예시 1개 첨부(선택) | 0.5B 출력 정확도 보정 |
| **캐시 2단** | 기기(IndexedDB) → 클러스터(서버) 순 조회 | 재방문·타기기 모두 **AI 호출 0회** |
| **프라이버시** | 로컬 추론 시 폼 데이터가 기기를 떠나지 않음 | 의료·법률 등 민감 도메인 우위 |
| **오프라인/저비용** | 클라우드 키 없이도 D 모드 동작 | 소형 고객 온보딩 장벽 제거 |

### 6.4 신뢰성 체인 (폴백 사다리)

```text
수동 config(선택) → 쇼핑몰 프리셋 → 로컬 sLLM → 클라우드 sLLM(Structured) → 정적 규칙 → Tool 등록 스킵(조용히 종료)
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
| 스키마 합성 지연 | ≤2.0s | ≤4.0s | **0ms** |
| AI 토큰 소비(폼 1회) | 0 (기기) | 입력 ≤2K/출력 ≤800 tokens | 0 |
| 재방문 모델 로드 | 1~2s(가중치 캐시) | 0 | 0 |
| 실행 후 성공률 | 99% | 99% | 99% |

---

## 9. 마일스톤 (6주 로드맵)

| 주차 | 범위 | 산출물 |
|------|------|--------|
| W1 | PoC 코어 — scanner+cache+injector+executor, 정적 규칙 모드 | 단일 폼(문진표) 0ms 주입 데모 |
| W2 | 로컬 엔진 — WebLLM/Chrome AI 통합, Engine Router v1 | grade A/B 기기 로컬 합성 성공 |
| W3 | 클라우드 엔진 — `/api/webmcp/analyze-dom` Structured Outputs, 클러스터 캐시 | 로컬↔클라우드 폴백 E2E |
| W4 | SPA·쇼핑몰 — MutationObserver/History 패칭, 카페24·고도몰·메이크샵 프리셋 | React/Vue 데모 + 쇼핑몰 데모 통과 |
| W5 | 보안·Agent 창구 — HMAC·Rate Limit·알림톡 2차, `/ai` 빌더 | 4단 보안 E2E, UA 리다이렉트 |
| W6 | Harness Studio — 콘솔 통합(키 발급·텔레메트리·스키마 검수), 문서 | **v2.0 GA** (136/Render 배포 준비) |

- 1.x 인프라(136 서버, docker-compose.silo, Django/Nuxt, PG18, Gemini 키)를 **그대로 확장** 사용 — 인프라 중복 투자 없음.

---

## 10. 리스크 및 대응

| # | 리스크 | 영향 | 대응 |
|---|--------|------|------|
| R1 | 모바일 iOS WebGPU 미지원/메모리 제한 | 로컬 불가 | 등급 B/C 강등 → 클라우드 폴백, 0.5B 이하 모델만 |
| R2 | 0.5B 모델의 셀렉터 오류 | 잘못된 값 주입 | 셀렉터 실존 검증 + 클라우드 재합성 1회 + confidence 임계 |
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
| Gemini 3.5 Flash Lite + OpenRouter 폴백 파이프라인 | 클라우드 엔진 1차/폴백 그대로 |