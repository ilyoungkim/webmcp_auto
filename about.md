# AI Assistant WebMCP — Project Story

## Inspiration
Small clinics, counseling centers, and SMBs have websites, but no AI to answer the basic questions visitors ask around the clock — booking, pricing, location. General-purpose chatbots don't know the business's actual information and end up hallucinating. We wanted to give every small business an AI assistant that actually knows *their* site, without requiring any engineering effort from them.

## What it does
WebMCP is a fully automated AI-assistant SaaS. You paste a URL, and it:
1. **Crawls** the site (sitemap-based, multi-page)
2. **Generates industry-specific Q&A** with an LLM
3. **Builds a widget** (5 themes, voice input, quick-menu)
4. **Ships a paste-and-go embed** (`/embed/<id>.js`)

Visitors then chat with an AI that answers from the site's real knowledge — with off-topic screening and hallucination guards built in.

## How we built it
- **Nuxt 3 (SSR) console + Django 5/DRF backend + vanilla JS widget** (single loader embed)
- **Celery-free polling worker** — `select_for_update` + lock-expiry auto-recovery for restart resilience
- **Dual LLM engines** — Gemini 3.5 Flash Lite for real-time chat (low latency + off-topic guard), OpenRouter `gpt-oss-120b` for batch Q&A (~$0.00196/run)
- **Multilingual silos** — ko/en fully separated across DB, containers, prompts, and UI
- **3-stage deployment** — Docker Compose → self-hosted server (nginx + Let's Encrypt) → Render Blueprint (IaC)

## Challenges we ran into
1. **Passive → proactive AI** — the ideal is the widget JS dynamically scanning and injecting into site forms (no owner-side changes), but form structures vary wildly. We deliberately deferred form control and focused on chat automation.
2. **Crawling engine trade-off** — plain HTTP parsers fail on WAF/SPA sites; browser crawlers are too heavy. Solved with a dual engine (httpx + browser-header fallback).
3. **Off-topic questions** — solved with system-prompt bounding + cached Q&A similarity matching (≥0.6), verified stable on Gemini 3.5 Flash Lite.
4. **Multi-tenant security** — Origin allowlist + publicId auth, per-tenant keys, global IP-allowlist switch.
5. **Platform quirks** — Render misread a `dockerCommand` chain as a filename, crashing the worker in a loop.

## Accomplishments that we're proud of
- **End-to-end automation** — URL in, working widget out, validated all the way to the cloud.
- **Cost engineering** — batch Q&A at ~$0.00196/run using OSS models, with similarity caching to cut expensive calls.
- **Structural multilingualism** — language mixing blocked at the architecture level, not via translation keys.
- **45 documented test records** (T-001~T-045) and a troubleshooting FAQ that prevent repeat mistakes.

## What we learned
- **Scope selection is the essence of automation** — one feature done end-to-end beats many half-done features.
- **Combine models by purpose** — cost-effective OSS for batch, low-latency Gemini for real-time.
- **The prompt is a security layer** — off-topic filtering via prompt bounding, at zero extra cost.
- **Security should be a switch, not a default** — environment-adaptable controls are what make them practical.

## What's next for AI assistant WebMCP
- **Proactive form integration** — the widget JS dynamically scanning and injecting into site forms (booking, contact), so the AI can *complete* actions, not just answer.
- **Broader language silos** — Japanese, Chinese, and more, following the existing 4-step extension path.
- **Deeper model routing** — per-tenant model selection and cost controls at scale.

---

# AI 어시스턴트 WebMCP — 프로젝트 스토리

## Inspiration (영감)
소규모 병원·상담센터·중소기업은 웹사이트는 있지만, 방문자가 24시간 궁금해하는 기본 질문(예약, 요금, 위치)에 답해줄 AI가 없습니다. 범용 챗봇은 그 업체의 실제 정보를 몰라 환각을 일으킵니다. 우리는 **엔지니어링 노력 없이도** 모든 소규모 사업체가 자기 사이트를 진짜 아는 AI 비서를 가질 수 있게 하고 싶었습니다.

## What it does (하는 일)
WebMCP는 완전 자동화 AI 비서 SaaS입니다. URL만 붙여넣으면:
1. **크롤링** (sitemap 기반 멀티페이지)
2. **업종별 Q&A 생성** (LLM)
3. **위젯 빌드** (5종 테마, 음성 입력, 빠른메뉴)
4. **붙여넣기 임베드 배포** (`/embed/<id>.js`)

방문자는 사이트의 실제 지식을 바탕으로 답하는 AI와 대화합니다 — 오프토픽 스크리닝과 환각 방지 가드가 내장되어 있습니다.

## How we built it (구축 방법)
- **Nuxt 3(SSR) 콘솔 + Django 5/DRF 백엔드 + vanilla JS 위젯** (단일 로더 임베드)
- **Celery 없는 폴링 워커** — `select_for_update` + 잠금 만료 자동 복구로 재시작 내성 확보
- **LLM 이중 엔진** — 실시간 채팅은 Gemini 3.5 Flash Lite(저지연+오프토픽 가드), 배치 Q&A는 OpenRouter `gpt-oss-120b`(1회 약 $0.00196)
- **다국어 사일로** — ko/en을 DB·컨테이너·프롬프트·UI까지 완전 분리
- **3단계 배포** — Docker Compose → 자체 서버(nginx+Let's Encrypt) → Render Blueprint(IaC)

## Challenges we ran into (직면한 도전)
1. **수동적 → 능동적 AI** — 이상은 위젯 JS가 사이트 폼을 동적으로 스캔·삽입하는 것(소유자 수정 불필요)이지만, 폼 구조가 천차만별이라 의도적으로 폼 제어를 미루고 채팅 자동화에 집중했습니다.
2. **크롤링 엔진 트레이드오프** — 단순 HTTP 파서는 WAF/SPA를 못 읽고, 브라우저 크롤러는 너무 무거움. 이중 엔진(httpx + 브라우저 헤더 폴백)으로 해결.
3. **오프토픽 질문** — 시스템 프롬프트 바운딩 + 저장 Q&A 유사도 매칭(≥0.6)으로 해결, Gemini 3.5 Flash Lite에서 안정 동작 확인.
4. **멀티테넌트 보안** — Origin 화이트리스트 + publicId 인증, 테넌트별 키, 전역 IP 화이트리스트 스위치.
5. **플랫폼 특이점** — Render가 `dockerCommand` 체인을 파일명으로 오판해 워커가 크래시 루프에 빠짐.

## Accomplishments that we're proud of (자랑스러운 성과)
- **엔드투엔드 자동화** — URL 입력 → 동작하는 위젯 출력, 클라우드까지 검증 완료.
- **비용 엔지니어링** — OSS 모델로 배치 Q&A 1회 약 $0.00196, 유사도 캐시로 고비용 호출 절감.
- **구조적 다국어** — 번역 키가 아닌 아키텍처 레벨에서 언어 혼용 차단.
- **45건의 테스트 기록**(T-001~T-045)과 트러블슈팅 FAQ로 재발 방지.

## What we learned (배운 점)
- **자동화의 본질은 범위 선택** — 하나를 끝까지 완성하는 것이 여러 개를 반쯤 하는 것보다 낫습니다.
- **모델은 용도별 조합** — 배치는 가성비 OSS, 실시간은 저지연 Gemini.
- **프롬프트가 보안 계층** — 오프토픽 필터링을 프롬프트 바운딩으로, 추가 비용 없이 해결.
- **보안은 스위치로 설계** — 환경에 맞게 조절 가능해야 실용적입니다.

## What's next for AI assistant WebMCP (다음 단계)
- **능동적 폼 통합** — 위젯 JS가 사이트 폼(예약·문의)을 동적으로 스캔·삽입해, AI가 답변을 넘어 **행동을 완수**하도록.
- **더 넓은 언어 사일로** — 일본어·중국어 등, 기존 4단계 확장 경로를 따라 추가.
- **고도화된 모델 라우팅** — 테넌트별 모델 선택과 대규모 비용 통제.
