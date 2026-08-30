# WebMCP Auto — 테스트 결과 기록 (test-results.md)

> 2026-08-28 ~ 2026-08-30까지 수행된 테스트를 시간 순으로 기록한다.
> 각 항목은 **날짜 / 대상 / 방법 / 결과** 순으로 정리한다.

---

## 2026-08-28 — 초기 구현 E2E 검증 (M0~M6)

### T-001. 파이프라인 E2E (로컬 SQLite)
- **대상**: 프로젝트 생성 → 크롤 → LLM Q&A 생성 → 위젯 빌드 → 미리보기/채팅
- **방법**: `manage.py run_pipeline_worker` 워커 가동 후 실제 사이트 5건 등록
- **결과**: ✅ 5개 프로젝트 전부 `completed` (아인병원, 아인병원척추관절센터, 아인뷰티, 뉴로이어법률서비스, 연애의자격)
  - SiteContent 5건 / Q&A 20건 / PipelineJob 19건 / Widget 40개 버전(버전 관리 동작)
  - 채팅 UsageEvent 141건, RequestLog 147건, 다운로드 2건, 고객센터 티켓 1건

### T-002. Docker 클린 인스톨
- **대상**: docker/ (PostgreSQL 18 전환)
- **방법**: `docker compose down --rmi all -v` 전체 삭제 후 재빌드 → `ADMIN_SEED_PASSWORD=test1234` 시드
- **결과**: ✅ health/login/파이프라인/채팅 전체 동작. `admin@local/test1234` 로그인 성공(`must_change_password=True`)
- **학습**: worker는 backend migrate 이전에 기동하면 테이블 없음 오류 → migrate 후 재시작 필요

### T-003. 백업/복원 스크립트
- **대상**: `docker/backup.sh`, `docker/restore.sh`
- **결과**: ✅ PostgreSQL 운영 DB 전체 덤프(`postgres_dump.sql`) + 설정파일 포함 확인. 프로젝트/Q&A/위젯/사용자 데이터 포함 검증 완료

### T-004. 로그 백업/로테이션
- **대상**: `docker/backup-logs.sh`, LineCountRotatingFileHandler
- **결과**: ✅ 5개 컨테이너 로그 백업 성공, 2000줄 초과 시 일자 넘버링 로테이션, 4주 retention 동작 확인

---

## 2026-08-29 — 다국어 사일로 + 보안 검증

### T-005. ko/en 사일로 격리 (HTTP)
- **대상**: 8080(ko) / 8081(en)
- **결과**: ✅ 두 사일로가 서로 다른 DB·카탈로그를 보는 것 확인. ko 25종(한국어), en 15개(Hospital/About) 카탈로그 격리 완료

### T-006. en 사일로 Q&A 영어 강제
- **대상**: Stanford Healthcare (en 사일로)
- **방법**: Q&A 5개 생성 후 한글 전수 스캔
- **결과**: ✅ question/answer 모두 영어, 한글 검출 False (한글 비율 >5% 재생성 안전장치 동작 확인)

### T-007. 콘솔 SSR 언어 확정
- **대상**: 랜딩/로그인/회원가입/대시보드/미리보기
- **방법**: `NUXT_PUBLIC_SILO_LANG=en` 주입 후 curl로 SSR HTML 확인
- **결과**: ✅ 하이드레이션 전 HTML부터 영어 렌더링. (기존: routeRules 프록시 502로 ko 고정되던 버그 수정 검증)

---

## 2026-08-30 — 크롤러 WAF 대응 (Edmunds 사례)

### T-008. Edmunds 크롤 실패 원인 분석
- **대상**: `https://www.edmunds.com/`
- **방법**: 단계별 헤더 매트릭스 실측 (httpx)
- **결과**:
  | 시도 | 결과 |
  |---|---|
  | sitemap/robots.txt 수집 | ✅ HTTP 200 |
  | 페이지 크롤 | ❌ HTTP 403 (16,126B 차단 페이지) |
  | 커스텀 UA (`WebMCPAutoBot/1.0`) | ❌ 403 |
  | Chrome UA + Accept + Sec-Fetch 전체 헤더 | ❌ 403 |
  | 세션 워밍업(robots.txt로 Akamai 쿠키 `bm_s` 획득) 후 | ❌ 403 |
  | **Googlebot / Bingbot UA** | ❌ **403** ← 결정적 증거 |
- **차단 페이지 본문**: "403 Access Denied … network restrictions or unusual activity. IP Address 114.205.189.190 (KR)"
- **판정**: UA가 아닌 **IP/지역 기반 차단** → 헤더 폴백 불가

### T-009. VPN(해외 IP) 재시험
- **결과**: ❌ 여전히 실패 → **최종 포기** (사용자 결정)
- **대안 확정**: 같은 자동차 카테고리의 **Autolist로 대체** (정상 크롤 확인)
- **robots.txt 확인**: Edmunds는 GPTBot/ClaudeBot/DeepSeekBot 등 AI 크롤러 `Disallow: /` 명시

### T-010. `_crawl_httpx()` WAF 폴백 적용 (수정 발견)
- **원인**: Autotrader 대응에서 만든 `Sec-Fetch 폴백`이 `_crawl_httpx`에만 누락됨
- **수정**: 403/차단 감지 → `_UA_BROWSER` 재시도, JS 리다이렉트 추종에도 폴백 헤더 적용
- **회귀 테스트**:
  | 사이트 | 결과 |
  |---|---|
  | example.com | ❌ 본문 178자 (원래 짧은 사이트, 정상 동작) |
  | python.org | ✅ "Welcome to Python.org" 4,041자 |
  | news.ycombinator.com | ✅ "Hacker News" 6,119자 |
- **추가 실측**: hopkinsmedicine.org가 당일 Cloudflare 403으로 전환 확인(WAF 사이트별 정책 변동 상수 관찰), Autotrader는 200 위장 차단페이지(3,762B) 패턴 유지

---

## 2026-08-30 — 프로필/결제 기능 (로컬 API 테스트 10단계)

### T-011. 마이그레이션 적용
- **대상**: `apps/accounts/migrations/0004_*`, `apps/proxy/migrations/0003_sitesetting`
- **방법**: `manage.py makemigrations accounts proxy` → `migrate` (로컬 SQLite)
- **결과**: ✅ 전항목 신규 필드(billing_*, phone1/2, monthly_price/currency) 생성, SiteSetting 테이블 생성. `manage.py check` 0 issues

### T-012. 프로필/설정 API 테스트 (curl 세션)
- **순서**:
  1. `/api/auth/csrf/` → 쿠키 획득 ✅
  2. `POST /api/auth/login/` (admin@local) → 200 ✅
  3. `GET /api/auth/profile/` → 전체 필드 + `billing.defaultCurrency=KRW, defaultPrice=50000, isEnterprise=false` ✅
  4. `PATCH /api/auth/profile/` → 전화번호 2개 + 결제 정보 5필드 저장 ✅
  5. `GET /api/admin/settings/` → `supportPhone: 02-888-9999` ✅
  6. `PATCH /api/admin/settings/` → `02-1234-5678` 변경 ✅
  7. **공개** `/api/site-info/` → 변경값 즉시 반영 확인 ✅ (인증 없이 접근 OK)
  8. `GET /api/admin/users/` → `phone1/2, monthlyPrice, billingCompany, defaultPrice` 확장 확인 ✅
  9. `PATCH /api/admin/users/4/` → `monthlyPrice=150000 KRW` → 사용자 목록에서 150000.0/KRW 확인 ✅ → `monthlyPrice: null` 로 기본 복귀 ✅
  10. 원상복구 (설정 02-888-9999) ✅
- **보호 동작**: 미인증 `GET /api/auth/profile/` → 403 ✅

---

## 2026-08-30 — Docker 배포 + 브라우저 E2E (프로필)

### T-013. 사일로 이미지 재빌드/기동
- **방법**: `docker/build.sh --run` (ko+en 전체)
- **문제 1**: 구버전 ko 컨테이너(webmcp-nginx)가 8080 점유 → `port already allocated`
- **해결**: `docker compose -f docker-compose.yml down` 후 재기동
- **문제 2**: 컨테이너 첫 기동 시 worker 종료 (`pipeline_pipelinejob does not exist`)
- **해결**: `exec backend-ko python manage.py migrate` 후 worker 재시작 (en 동일)
- **문제 3**: worker 재기동 후 nginx 502 (DNS 캐시)
- **해결**: nginx-en restart
- **최종**: 14개 컨테이너 실행, `/api/health/` → `{"status":"ok"}` (ko/en 모두)

### T-014. 브라우저 E2E — ko 사일로 (8080)
- **/profile**: 로그인(코드로 `requestSubmit` 처리 필요했음) → 모든 섹션 한국어, 요금 박스 **50,000원 (기본)** 표시 ✅
- **/admin/profile**: "문의 연락처(사이트 대표)" 카드에서 **02-777-8888 저장** → 공개 `/api/site-info/` 실시간 반영 확인 ✅ → 원상복구(02-888-9999)
- **브라우저 CSRF 학습**: 백엔드 재시작 직후 403 "자격 인증 데이터가 제공되지 않았습니다" → 페이지 새로고침으로 토큰 재발급 해결

### T-015. 브라우저 E2E — en 사일로 (8081)
- **/profile**: 전 문구 영어(My Profile/Account/Billing…), 요금 박스 **$49 (Default)** — ko와 사일로별 자동 구분 ✅

---

## 2026-08-30 — 결제금액/연락처 설정 UI (계정 선택 연동)

### T-016. ko-nginx 기동 실패 원인 발견/수정
- **증상**: SSR HTML이 구버전(`pay-panel` 없음), `/_nuxt/최신청크` 404, nginx-ko 반복 종료
- **로그 분석**: `host not found in upstream "backend:8000"` — silo 네트워크에 `backend-ko`만 존재
- **수정**: `docker/nginx-ko.conf` 신설(upstream backend-ko/frontend-ko) + compose 볼륨 교체
- **부가 정리**: 구 compose 프로젝트(webmcp-nginx, 8080 점유) stop/rm 후 silo 전체 `down/up` 일괄 재기동 → ko/en 모두 200

### T-017. 계정 선택 → 결제 패널 E2E (ko 8080)
- **방법**: 브라우저에서 계정 선택 → 패널 자동 표시 확인
- **저장 시나리오**:
  1. 전화번호 1/2 + 금액 150000 KRW → ✅ "저장 완료", 배지 **150,000원 (엔터프라이즈)** 즉시 반영
  2. 금액 비우기 + 연락처 비우고 저장 → ✅ **50,000원 (기본)** 복귀, "연락처 없음"
- **버그 발견/수정**: 초기 테스트에서 클릭 시 요청 자체가 미전송 → `useApi` PATCH에 **Content-Type 헤더 미명시**가 원임 → `headers: {'Content-Type': 'application/json'}` 명시로 해결 (요청 스니핑으로 원인 분석)

### T-018. en 사일로 동일 시나리오 (8081)
- `99 USD` 저장 → **$99 (엔터프라이즈)** ✅ → 지우고 저장 → **$49 (기본)** 복귀 ✅
- 드롭다운 라벨(`admin@local (Admin) — $99 (엔터프라이즈)`)도 실시간 갱신 확인

### T-019. 0=기본요금 규칙 (커밋 605a733)
- **규칙 변경**: 빈 값 또는 **0** → 기본 요금, 1 이상 → 엔터프라이즈
- **UI 문구 통일**: 라벨 "월 결제 금액 (비우면 또는 0이면 기본 요금)", placeholder "0 = 기본 요금", 힌트 문구 갱신
- **E2E**:
  - ko: 150,000원(엔터프라이즈) → `0` 저장 → ✅ 50,000원 (기본)
  - en: $99(엔터프라이즈) → `0` 저장 → ✅ $49 (기본)

---

## 2026-08-30 — tensun 계정 로그인 불가 복구

### T-020. 증상 및 원인 파악
- **증상**: 8080에서 `tensun@naver.com` 로그인 실패
- **원인**: ko 사일로 DB(`webmcp_ko`)에 **계정이 1개(admin@local)만 존재** — 초기 도커 재배포 시 구 볼륨(`docker_postgres_data`의 `webmcp` DB) 데이터가 새 사일로 DB로 이전되지 않음

### T-021. 데이터 복구 (pg_dump/psql)
- **절차**:
  1. `docker run --rm -d --name pg-old -v docker_postgres_data:/var/lib/postgresql -p 55432:5432 postgres:18-alpine` — 임시 컨테이너로 구 클러스터 기동
  2. `pg_dump -U webmcp -d webmcp --data-only --no-owner --no-privileges` → 구 데이터 추출
  3. 현재 `webmcp_ko`에 복원
- **장애 및 해결**:
  | 문제 | 해결 |
  |---|---|
  | `backslash commands are restricted` — psql 18이 pg_dump 18.6의 `\restrict/\unrestrict` 지시어 거부 | **sed로 5행/865행 2줄만 정확 제거** (`grep -v ^\restrict`는 데이터 행 손상 위험) |
  | `syntax error at or near "1"` | 위 restrict 지시어 제거로 해소 |
  | `duplicate key (accounts_user_pkey, catalogs_*)` | 이미 복원된 행과 중복 — 무해(무시) |
  | `relation already exists` (schema 포함 덤프로 실수) | `--data-only` 재덤프로 해결 |
  | 시퀀스 후행 정렬 필요 | `setval(pg_get_serial_sequence(...))` 전 테이블 동기화 |
- **복원 결과 검증**:
  - users 2 (admin@local + **tensun@naver.com**)
  - projects 1 (부천 연세본사랑병원, completed, tensun 소유)
  - Q&A 5 / SiteContent 1 / Widgets 6
  - 카탈로그 26/130 (시드 유지)

### T-022. 로그인 API 실측 (복구 확인)
- `POST /api/auth/login/` → **HTTP 200**, `{"email":"tensun@naver.com","name":"김일영","role":"user","plan":"free","mustChangePassword":false}` ✅
- 사후 처리: backend-ko/worker-ko restart + nginx-ko restart + 시퀀스 setval

---

## 2026-08-30 — 전체 기능 검토 (사일로 정합성, 수정 전 조사)

### T-023. 사일로 언어 분기 전수 검토
- **방법**: 백엔드 `lang == 'en'` 분기 45곳 / 프론트 `useSilo`·`siloLang` 22곳 그리프 + 코드 리뷰
- **발견 (수정 전)**:
  - 🔴 `/admin/projects`, `/admin/chat-errors` — `useSilo` 미적용(하드코딩 한국어) → en 사일로에서 한국어 노출
  - 🟡 `_required_menu_answer()`("AI비서란?") — en 분기 없음(한국어 고정)
  - 🟡 ko/en 프롬프트 상세도 비대칭(ko가 한국 특화 연락수단 상세, en은 일반) — 의도된 로컬라이제이션
  - ✅ langsilo.py 중앙화, compose 대칭, useSilo 키 대칭, preview/lang 상속 정상
- (이후 T-024에서 2건 수정 확정 — 아래)

---

## 2026-08-30 — 관리자 페이지 사일로 다국어 수정 + 검증

### T-024. 수정 구현 및 배포
- `/admin/projects`, `/admin/chat-errors`에 `useSilo()` 도입
- `useSilo.ts`에 `admin.*` 키 60여개 추가(ko/en 대칭)
- `STATUS_LABELS`를 `computed`로 전환(프로젝트 상태도 언어별)
- `runner.py `_required_menu_answer` en 분기 추가
- **부수 버그 수정**: `prof.backToDash` 키가 이미 `←`를 포함 → 템플릿 `&larr;` 중복으로 "← ← Dashboard" 뜨던 것 제거

### T-025. 배포 후 브라우저 검증
- **en 8081 `/admin/projects`**:
  - 텍스트: "Manage Projects / Select Account / Admin Profile / Refresh / No phone / Phone 1/2 / Monthly price (empty or 0 = default) / Save"
  - 프로젝트 상태: **"Completed"** (computed 라벨 적용 확인)
  - 한글 잔존 스캔: `["원"]` 1개 — 통화 선택 옵션 `KRW(원)` 라벨만(의도 유지)
- **en 8081 `/admin/chat-errors`**: "Chat Error Reports / All / New / Read / Resolved / No error reports." — 한글 잔존 0
- **ko 8080 `/admin/projects`**: 한국어 정상 유지 ("프로젝트 관리 / 계정 선택 / 관리자 프로필 …")

### 최종 도커 상태 검증
- 14개 컨테이너 전부 Up, `/api/health/` 200(ko/en), `/api/silo-info/` `{"lang":"ko"}`/`{"lang":"en"}` 정상

---

## 2026-08-30 — LAN(192.168.x.x) 원격 접속 허용

### T-026. LAN 접속 설정 및 실측 (커밋 597b095)
- **요구**: 사무실 내 다른 PC에서 `http://<Mac IP>:8080/8081` 접속, DB는 로컬 전용 유지
- **설정 변경** (`docker-compose.silo.yml`):
  - `ALLOWED_HOSTS` += `192.168.31.248, 192.168.64.1` (실제 LAN + 가상 인터페이스)
  - `SAAS_PUBLIC_URL`: `http://192.168.31.248:8080/8081` (위젯 assetBase/proxyEndpoint 박제 주소 — LAN 사용자 브라우저가 이 주소로 위젯 JS 로드)
  - `CSRF_TRUSTED_ORIGINS`: LAN URL 2개 추가
- **검증**:
  | 항목 | 결과 |
  |---|---|
  | `http://192.168.31.248:8080/api/health/` | ✅ 200 |
  | `http://192.168.31.248:8081/api/health/` | ✅ 200 |
  | `localhost:8080` 기존 접속 | ✅ 200 유지 |
  | LAN 오리진 로그인(CSRF 라운드트립) | ✅ 200 |
  | **DB 포트매핑** (`docker port` postgres-ko/en) | ✅ **매핑 없음** — 5432는 `expose` 전용이라 호스트/LAN에서 접속 불가 |
  | 호스트 리슨 상태 | `*.8080`, `*.8081` LISTEN (tcp46) |
- **주의사항 기록**:
  - Mac의 DHCP IP가 바뀌면(공유기 재부팅 등) 위 3곳의 IP를 갱신해야 함 — `/sbin/ifconfig | grep "inet 192.168"`로 확인
  - macOS 방화벽이 켜져 있으면 8080/8081 수신 허용 필요
  - `expose`(내부) vs `ports`(호스트 바인딩) 구분 확인 — DB는 후자가 아님

---

### T-027. 스마트폰 LAN 로그인 실패 원인 분석/수정 (커밋 07e19df)
- **증상**: 같은 Wi-Fi의 스마트폰에서 `http://192.168.31.248:8080/login` 화면은 뜨지만 로그인이 안 됨
- **진단 과정**:
  1. LAN 경유 `/api/health/` 200, `/login` 페이지 200 — nginx/라우팅 정상
  2. curl로 스마트폰 동일 조건(Origin/Referer = LAN URL) 로그인 POST → **200** (API 자체는 정상)
  3. **Set-Cookie 응답 분석 → 원인 확정**: `csrftoken`/`sessionid` 모두 **`Secure` 속성이 붙어 있었음**
- **근본 원인**: `settings.py`의 `if not DEBUG: SESSION/CSRF_COOKIE_SECURE = True` — compose가 `DJANGO_DEBUG=false`이므로 **http 접속에서 브라우저가 Secure 쿠키를 폐기** → 로그인 API는 성공해도 브라우저가 세션 쿠키를 저장하지 못함 (curl -c는 Secure 쿠키도 저장해 헤더 재현 시 성공처럼 보이는 함정)
- **수정**:
  - `settings.py`: `SECURE_COOKIES` env 스위치 신설(기본 `true` — https 배포 안전 유지)
  - `docker-compose.silo.yml`: LAN 배포용으로 `SECURE_COOKIES: "false"` 주입 (인터넷 공개 시 true로 되돌릴 것을 주석 명시)
- **검증**:
  | 항목 | 결과 |
  |---|---|
  | Set-Cookie에 Secure 속성 | ✅ 제거 확인 (`SameSite=Lax`만) |
  | LAN 로그인(tensun) | ✅ 200 |
  | LAN 로그인 후 `/api/auth/me/` 세션 유지 | ✅ 200 |
  | localhost 접속 | ✅ 200 유지 |
- **운영 주의**: 인터넷 공개(https) 시 compose에서 `SECURE_COOKIES: "true"`로 되돌려야 쿠키 보안 유지

---

## 부록 A. 커밋 이력 (시간 순)

| 커밋 | 내용 |
|---|---|
| `e6692b1`/`83ca7ed` | 크롤러 WAF 대응(감지+Sec-Fetch 폴백+세션 워밍업) — 이전 세션 |
| `4e8e319` | `_crawl_httpx`에 WAF 폴백 UA 적용(403/차단 시 브라우저 헤더 재시도) |
| `903cdf3` | 프로필 페이지(일반/관리자), 사이트 연락처 관리, 엔터프라이즈 결제금액 기능 |
| `caf04fc` | 계정 선택 시 결제 패널 즉시 표시 + Content-Type PATCH 수정 + `nginx-ko.conf` 신설 |
| `605a733` | 결제금액 0 입력 시 기본 요금 복귀 |
| `ea0abb7` | 관리자 페이지 사일로 다국어 + "AI비서란?" en 분기 |
| `179dd07` | plan.md §0.10 최신 현황 추가 |
| `4536bb2` | test-results.md 최초 생성 (T-001~T-025) |
| `597b095` | LAN(192.168.x.x) 원격 접속 허용 — 8080/8081, DB 로컬 전용 유지 |
| `0eccdd0` | test-results.md T-026 LAN 접속 테스트 추가 |
| `2eb18e9` | DEPLOY_PORUDCTION.md §5.1 LAN 접속 절차 문서화 |
| `07e19df` | SECURE_COOKIES 스위치 — LAN http 로그인 쿠키 폐기 문제 수정 |
| `ce780c2` | test-results.md 커밋 이력 갱신 |

## 부록 B. 배포·운영 체크리스트 (테스트 중 도출)

1. 새 언어 사일로 첫 기동: `up -d` → `exec backend-<lang> migrate` → worker 재시작
2. worker/backend 재시작 후 nginx-<lang>도 restart(DNS 캐시 502 방지)
3. 백엔드 재시작 후 브라우저 CSRF 무효 403 → 페이지 새로고침
4. DB 복원(pg_dump 18.6 → psql): `\restrict` 2줄 제거 + `--data-only` + `--no-owner` + setval
5. 구 docker-compose.yml(구 프로젝트)과 silo compose 동시 기동 금지(8080 충돌)
6. Nuxt는 반드시 이미지 빌드 배포(cp는 SSR청크와 불일치 유발), 필요 시 `build frontend-<lang>`