# webmcp/front/ — 공용 프론트엔드 (웹 위젯 + 프록시 연동)

여러 도메인(yonza.co.kr, saengsaenghospital.com 등)이 공용으로 사용하는 위젯과,
Gemini 키를 직접 들고 있지 않고 백엔드 프록시를 호출하는 `webmcp.js`를 포함합니다.

```
webmcp/front/
├── webmcp.js           # 공용 라이브러리 — 프록시 /api/chat 호출 (키 미보관)
├── widget.js           # AI 비서 위젯 로더 — webmcp-widget.js 동적 로드 (캐시 방지 ?v=)
├── webmcp-widget.js    # 공용 위젯 로직 (마크다운, 퀵질문, 상태배지, 아코디언, 🧠 대화 기억)
├── widget.css          # 위젯 스타일 (#webmcp-widget 스코프 → 페이지 충돌 방지)
├── yonja-config.js     # yonja.html 기준 WebMCPConfig + 시스템 프롬프트
├── hospital-config.js  # hospital.html 기준 WebMCPConfig + 시스템 프롬프트
├── index.html          # yonja 데모 페이지
├── hospital.html       # 생생병원 데모 페이지
├── genisev.html        # 제니스코리아 데모 페이지
├── memory-test.html    # 🧠 대화 기억(Memory) 기능 로컬 테스트 페이지
└── HISTORY.md          # 버전별 변경 이력
```

## 파일 역할

| 파일 | 역할 |
|------|------|
| `webmcp.js` | `window.WebMCP.callGeminiViaProxy(prompt)` — 프록시로 Gemini 호출. 키 미보관 |
| `widget.js` | 공통 라이브러리 로더. `webmcp-widget.js`를 동적으로 로드 (캐시 방지 `?v=1`) |
| `webmcp-widget.js` | 위젯 DOM 자동 마운트. 마크다운 렌더링, 퀵 질문 pill, 연결 상태 배지, 동작 방식 아코디언, 🧠 대화 기억(Memory) |
| `widget.css` | 위젯 스타일. 모든 선택자가 `#webmcp-widget`으로 스코프 |
| `yonja-config.js` | `window.WebMCPConfig`(service/consultant/diagnosis 툴) + `window.YONJA_SYSTEM_PROMPT` |
| `hospital-config.js` | `window.WebMCPConfig`(health/doctor/appointment 툴) + `window.HOSPITAL_SYSTEM_PROMPT` |
| `index.html` | yonja 데모. WebMCP 정보/클라이언트·서버/WebMCP.config에/DB 스키마/사용법 아코디언 |
| `hospital.html` | 생생병원 데모. 동일한 아코디언 구조 |
| `genisev.html` | 제니스코리아 데모. WebMCP 툴 데모 |
| `memory-test.html` | 🧠 메모리(대화 기억) 기능 로컬 테스트 페이지 |
| `HISTORY.md` | 버전별 변경 이력 (마지막 버전 상단) |

## 위젯 동작 원리

```
사용자 위젯 ──POST /api/chat──▶ nginx(8081) ──▶ FastAPI(8001) ──▶ Gemini
                              (Origin 헤더로 도메인 판별, DB에서 키 조회)
```

- `widget.js`는 `window.YONJA_SYSTEM_PROMPT || window.HOSPITAL_SYSTEM_PROMPT`를
  자동 선택해 프록시 요청에 포함합니다.
- `webmcp.js`는 `window.WebMCPConfig.proxyEndpoint`(기본 `/api/chat`)로 호출합니다.

## 🧠 대화 기억(Memory) 기능

`webmcp-widget.js`(v1.1.0)에 **백엔드 API 없이 로컬스토리지만 사용**하는 대화 기억 기능이 포함됩니다.

| 기능 | 동작 |
|------|------|
| 대화 저장 | 질문-답변 쌍을 `localStorage`(`wmcpMemory`)에 저장 (최대 50개) |
| 유사 질문 유추 | 질문을 단어로 쪼개 이전 질문과 겹치는 비율 계산 (임계값 0.35) |
| 기억 컨텍스트 | 유사 질문이 있으면 `[이전 대화 기억]` 컨텍스트를 프롬프트에 포함해 일관되게 답변 |
| 영속성 | 새로고침/재접속 후에도 브라우저에 저장되어 유지 |

- **동작 순서**: 사용자 질문 → 유사 이전 대화 검색 → 있으면 `[이전 대화 기억]` 컨텍스트 포함 → 프록시로 전송 → 답변을 메모리에 저장.
- **서버 저장 없음**: 별도 백엔드 설정 불필요. 기기(브라우저)별 로컬 저장만 합니다.
- **테스트**: `memory-test.html`에서 기능 검증 가능 (전체 PASS 확인됨).

> 💡 로컬스토리지 기반이므로 브라우저/기기를 바꾸면 대화 기억은 공유되지 않습니다. 서버 저장이 필요하면 백엔드 API를 추가해야 합니다.

## 페이지에 붙이는 방법

```html
<!-- ① 사이트별 config (webmcp.js 보다 먼저) -->
<script src="yonja-config.js"></script>   <!-- 또는 hospital-config.js / genisev-config.js -->
<!-- ② 공용 라이브러리 -->
<script src="webmcp.js"></script>
<!-- ③ 위젯 로더 (webmcp-widget.js 는 widget.js가 자동 로드) -->
<link rel="stylesheet" href="widget.css" />
<script src="widget.js"></script>
```

> 💡 **캐시 방지**: `widget.js`는 내부에서 `webmcp-widget.js?v=1`로 로드합니다.
> `webmcp-widget.js`를 수정·배포했는데 새 기능이 안 보이면 `widget.js`의 `?v=` 값을 올리면 됩니다.
> (브라우저가 구버전을 캐시하는 문제를 방지)

---

## 외부 사이트 배포 시 주의사항 ⚠️

외부 고객사 사이트(별도 서버/도메인)에 붙일 때 아래를 반드시 준수하세요.

### 1. HTTPS 사이트에서는 HTTP 백엔드 호출 불가 (Mixed Content)

브라우저는 HTTPS 페이지에서 `http://...` 리소스를 차단합니다.

| 페이지 프로토콜 | 백엔드 호출 주소 |
|-----------------|------------------|
| `http://` (내부 데모) | `http://114.205.189.190:8081` |
| `https://` (실서비스) | `https://webmcp.duckdns.org` |

### 2. 두 가지 연동 방식

**방식 A — 상대경로 + 사이트 서버 리버스 프록시 (권장)**
`proxyEndpoint`를 기본 `/api/chat`으로 두고, 고객사 서버가 `/api/`를 백엔드로 프록시.
프록시 대상은 **HTTPS 주소** 사용.

**방식 B — HTTPS 절대경로 직접 호출**
```js
window.WebMCPConfig = {
  proxyEndpoint: 'https://webmcp.duckdns.org/api/chat',
};
```

### 3. ⚠️ 서버 프록시 시 헤더 전달 필수

백엔드는 `Origin`/`User-Agent` 헤더로 테넌트 판별·비정상 요청 차단을 합니다.
고객사 서버가 프록시할 때 **원본 브라우저 헤더를 그대로 전달**해야 합니다.

| 헤더 | 없으면 | 설명 |
|------|--------|------|
| `Origin` | **403** | DB `tenants`에서 테넌트 판별 |
| `User-Agent` | **401** | `Mozilla/5.0` + 브라우저명 필요 |

> ⚠️ Node.js(Next.js) `fetch` 기본 UA는 브라우저가 아니므로, 서버 프록시 시
> **브라우저 UA를 그대로 넘겨야** 401을 피할 수 있습니다.

자세한 Next.js Route Handler 예시는 상위 [`webmcp/README.md`](../README.md)의
"5. 외부 사이트 배포 시 지켜야 할 사항"을 참고하세요.
