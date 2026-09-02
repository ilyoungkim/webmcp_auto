# FAQ — WebMCP 자주 발생하는 문제 해결 모음

> 프로젝트 운영 중 반복적으로 나타난 문제들을 원인/진단/해결 구조로 정리한 문서.
> 상세 이력은 `/memories/repo/webmcp-project.md` 참고.

---

## 1. 외부(LTE) 접속 문제

### Q. LTE에서 `webmcp.duckdns.org` 접속이 안 돼요 (`ERR_CONNECTION_TIMED_OUT` / `ERR_ABORTED`)

### 원인
DuckDNS의 A 레코드가 **사설 IP(192.168.31.136)** 로 박혀 있으면, 외부 네트워크(LTE)에서는 해당 IP에 도달할 수 없어 접속이 타임아웃됩니다.

### 진단
```bash
# 1. DuckDNS가 가리키는 IP 확인
dig +short webmcp.duckdns.org
# → 192.168.31.136 (사설 IP면 문제)

# 2. 실제 공인 IP 확인
curl -s --max-time 8 https://api.ipify.org
# → 203.25.124.132 (공인 IP)
```

두 값이 다르면(사설 vs 공인) DuckDNS 갱신이 필요합니다.

### 해결
DuckDNS A 레코드를 공인 IP로 갱신:

```
https://www.duckdns.org/update?domains=webmcp&token=<토큰>&ip=<공인IP>
```

- 토큰: `69b002c5-00d0-459b-b649-d96b98b462b1`
- 공인 IP: `203.25.124.132`

---

## Q. `webmcp.duckdns.org`(80)은 되는데 `:8443`, `:8444`는 `ERR_CONNECTION_REFUSED` 가 나와요

### 원인
공유기(라우터) 포트포워딩에 **80번만** 설정되어 있고, 8443/8444는 포워딩이 누락된 상태입니다. 서버 자체는 정상 리슨 중이지만, 공유기가 외부 트래픽을 내부 서버로 전달하지 못해 `connection refused`가 발생합니다.

### 진단
서버(136)에서 포트 리슨 상태 확인:
```bash
ssh tensun@192.168.31.136 "ss -tlnp | grep -E ':(80|8443|8444)\b'"
```
세 포트 모두 `0.0.0.0`으로 리슨 중이면 서버는 정상 → 공유기 포트포워딩 문제.

### 해결
공유기 관리자 페이지(`http://192.168.31.1`)에서 포트포워딩 규칙 추가:

| 외부 포트 | 내부 IP | 내부 포트 | 프로토콜 |
|-----------|---------|-----------|----------|
| 80 | 192.168.31.136 | 80 | TCP |
| 8443 | 192.168.31.136 | 8443 | TCP |
| 8444 | 192.168.31.136 | 8444 | TCP |

- 메뉴명: "포트포워딩" / "NAT" / "가상서버" / "Port Forwarding" 중 하나
- 80번은 이미 열려 있으므로 **8443, 8444 두 개만 추가**하면 됩니다.

---

## 2. nginx 502 Bad Gateway

### Q. 페이지가 502가 나와요 (`Host is unreachable`)

**원인**: Docker nginx의 정적 `upstream` 블록은 **시작 시 1회만 DNS resolve** → 프론트/백엔드 컨테이너 재시작으로 IP가 바뀌면 구 IP로 접속해 502 발생.

**진단**:
```bash
docker logs nginx-ko   # "113 Host is unreachable" 확인
docker inspect <컨테이너> --format '{{.NetworkSettings.IPAddress}}'
```

**해결**: nginx conf에 `resolver 127.0.0.11 valid=10s ipv6=off;` + 변수 기반 `proxy_pass` 사용 (요청마다 resolve). 이미 적용됨(커밋 9052d17). **단, 최초 1회는 nginx 재시작 필요** — 이후엔 자동 갱신.

### Q. 백엔드 재시작 후 nginx-en이 502

**원인**: nginx가 구 IP 캐시를 들고 있음.

**해결**: `docker restart nginx-en` (resolver 넣어도 최초 1회는 재시작 필요).

---

## 3. worker 기동 실패

### Q. worker가 `pipeline_pipelinejob does not exist` 로 죽어요

**원인**: 신규 컨테이너 첫 기동 시 DB 마이그레이션이 안 된 상태에서 worker가 테이블에 접근.

**해결**:
```bash
docker compose -f docker-compose.silo.yml exec backend-ko python manage.py migrate
docker start webmcp-ko-worker
# en도 동일: backend-en migrate + worker-en restart
```

---

## 4. CSRF 403 에러

### Q. 백엔드 재시작 후 "자격 인증 데이터가 제공되지 않았습니다" (403)

**원인**: 백엔드 재시작으로 브라우저의 CSRF 토큰이 무효화됨.

**해결**: 브라우저 **새로고침** 한 번으로 해결.

---

## 5. 위젯이 안 보임 / 404

### Q. 모바일에서 위젯 런처가 안 떠요 (JS/CSS 404)

**원인**: 위젯 config_json의 `assetBase`/`proxyEndpoint`가 **빌드 시점 `SAAS_PUBLIC_URL`로 고정 박제**됨. 공개 주소가 바뀌면 기존 위젯은 구 주소(예: `localhost`)를 계속 가리켜 404.

**해결**:
1. DB REPLACE로 기존 config.json 주소 치환
2. `widget_asset()`에 `Cache-Control: no-cache, must-revalidate` 추가(모바일 캐시 방지)

**교훈**: `SAAS_PUBLIC_URL`을 바꾸면 기존 프로젝트 전부 재생성 또는 config_json 치환 필요.

### Q. 위젯 수정했는데 고객 임베드에 반영이 안 돼요

**원인**: 위젯 소스가 두 곳에 존재 — `saas/widget-dist/`(원본)와 `saas/frontend/public/widget-dist/`(Nuxt 서빙 복사본). 한쪽만 수정하면 미리보기(원본)는 되는데 실제 임베드는 반영 안 됨.

**해결**: 수정 시 **양쪽 모두 cp 동기화** 필수.

---

## 6. LAN/외부 접속 보안 문제

### Q. 스마트폰에서 로그인이 안 돼요 (http LAN 환경)

**원인**: `DJANGO_DEBUG=false`면 settings가 `SESSION/CSRF_COOKIE_SECURE=True` 강제 → http 접속 시 브라우저가 Secure 쿠키를 폐기 → 로그인 API 200인데 세션 저장 불가.

**해결**: `SECURE_COOKIES=false` env 주입 (compose에 설정). **인터넷 공개(https) 시 반드시 true로 되돌릴 것.**

### Q. 스마트폰에서 음성 입력이 안 돼요

**원인**: Web Speech API(SpeechRecognition)는 마이크 권한이 **보안 콘텍스트(HTTPS 또는 localhost) 필수**. http://192.168.x.x 접속 시 브라우저가 권한 요청 자체를 차단.

**해결**: HTTPS 배포 필수. http 환경에서는 브라우저 규격상 불가.

### Q. 외부 컴퓨터에서 "연결이 비공개로 설정되어 있지 않습니다"

**원인/해결** (2단계):
1. **mac 방화벽이 nginx 차단** → `socketfilterfw --listapps`에서 Block 확인 → `--unblockapp <nginx바이너리>`로 허용. 자기 LAN IP curl 시 TLS 핸드셰이크 전 `SSL_ERROR_SYSCALL`이면 방화벽 의심.
2. **`NET::ERR_CERT_AUTHORITY_INVALID`** → 외부 컴퓨터에 mkcert 루트 CA 미설치. CA 파일을 nginx에서 서빙(`location = /ca.pem`)해 다운로드 → OS 신뢰 저장소 설치. **mkcert 로컬 신뢰는 그 Mac에만 유효.**

---

## 7. Docker 배포 문제

### Q. `port already allocated` 에러

**원인**: 구버전 컨테이너(예: webmcp-nginx, 8080 점유)가 정리 안 됨.

**해결**: `docker compose -f docker-compose.yml down` 으로 구버전 정리 후 재기동.

### Q. PostgreSQL 18 마운트 경로

**주의**: postgres 18+는 마운트 경로가 `/var/lib/postgresql` (data 하위 아님). 16→18 업그레이드는 pg_dump 백업 → 새 볼륨 → 복원 방식.

---

## 8. 프론트엔드(Nuxt) 문제

### Q. PATCH 요청이 무응답 + 저장 실패

**원인**: `useApi`($fetch 래퍼)에서 PATCH 시 `Content-Type` 헤더 미명시.

**해결**: `headers: {'Content-Type': 'application/json'}` 명시.

### Q. en 사일로인데 한국어가 섞여 나와요

**원인**: `useSilo`를 일반 `ref`로 쓰면 컴포넌트마다 새 인스턴스 → 페이지마다 ko fallback.

**해결**: `useSilo`는 반드시 `useState` 싱글턴 사용. SSR 로드는 `await useAsyncData` 필요.

### Q. CSS가 다른 페이지로 누수돼요

**원인**: login/signup/index.vue의 비스코프 `<style>` 전역 스타일이 모든 페이지로 누수.

**해결**: `<style scoped>`로 변경 + 필요한 페이지에 명시적 color 지정. 새 페이지 작성 시 비스코프 스타일 주의.

---

## 9. 크롤러 WAF 차단

### Q. 특정 사이트 크롤이 안 돼요 (차단 페이지 반환)

**원인**: Akamai 등 WAF가 HTTP 200 + 위장 차단페이지(짧은 본문) 반환.

**해결**:
1. `_looks_blocked`(짧은 본문 + 차단 키워드) 감지
2. **결정적 헤더**: `Sec-Fetch-Dest/Mode/Site` + `Upgrade-Insecure-Requests` (Chrome UA만으론 차단)
3. **세션 워밍업**: 홈 먼저 방문 → `_abck` 쿠키 획득 → robots/sitemap 진행

**미해결**: Docker 컨테이너는 Akamai TLS/IP 평판 차단으로 여전히 제한 → crawl4ai(브라우저) 활성화 또는 크롤 프록시 필요. 대형 상업 사이트는 대체 소스 사용이 실용적.

---

## 10. Render 클라우드 배포 문제

### Q. Render 워커가 `not found`로 무한 크래시 루프에 빠져요 — 프로젝트가 Queued 0%에서 멈춰요

**원인**: `dockerCommand: sh -c "a && b"` 형태의 체인 커맨드를 Render가 **전체 문자열을 하나의 실행 파일명으로 오판**. 워커가 시작 즉시 죽고 재시작을 반복해 job을 집어갈 프로세스가 없음.

**진단**: Render 대시보드 → 워커 → Logs에서 아래 패턴 확인
```
sh: 1: python manage.py migrate && python manage.py run_pipeline_worker --interval 2.0: not found
==> Instance restarted   ← 반복
```

**해결**: 체인 커맨드는 `docker/docker-worker-entrypoint.sh`처럼 스크립트 파일로 분리하고 `dockerCommand: ./docker-worker-entrypoint.sh` 한 줄로 실행.

---

### Q. Blueprint에서 Postgres 연결이 안 돼요

**원인**: `fromService: type: postgres`라는 타입은 존재하지 않음. Postgres는 `databases:`에 정의하고 서비스에서 `fromDatabase: connectionString`으로 참조해야 함.

---

### Q. `sync: false`로 넣은 API 키가 배포 후 비어 있어요

**원인**: **envVarGroups 안에서는 `sync: false`가 무시됨** (Render 공식 동작). 생성 프롬프트에도 안 뜨고 값 없이 배포됨.

**해결**: API 키 등 시크릿은 각 서비스의 `envVars`에 `sync: false`로 직접 정의. `generateValue`와 `sync: false` 동시 지정도 불가.

---

### Q. 고객 사이트에 설치한 위젯 채팅이 403 (Forbidden) 이 나와요

**원인**: 콘솔에서 다운로드한 위젯을 **프로젝트 URL과 다른 도메인**에 설치하면 Origin 화이트리스트에 없어 익명 방문자가 전부 403. (RequestLog reason=`origin_not_allowed`)

**진단**:
```bash
curl -X POST https://<front>/api/chat/ -H "Origin: https://고객도메인" \
  -H "Content-Type: application/json" -d '{"publicId":"<id>","question":"hi"}'
# → {"error": "Domain not allowed"} 403 이면 오리진 미등록
```

**해결**:
1. 자동: 소유자/관리자 세션으로 그 사이트에서 채팅 1회 → **오리진 자동 학습 등록** (커밋 faec401)
2. 수동: 콘솔 프로젝트 상세에서 오리진 추가, 또는 `POST /api/projects/<id>/origins/` {"origin":"https://..."}
- 프로젝트 생성 시 www/비www 양쪽은 자동 등록됨

---

### Q. admin/projects에서 특정 계정 선택 시 화면이 통째로 공백이에요

**원인**: 고객센터 Q&A 목록의 `v-for="t in supportItems"` 변수 `t`가 **useSilo 번역 함수 `t()`를 가리는 충돌** → `TypeError: t is not a function` → 컴포넌트 크래시. **고객센터 질문이 있는 계정**에서만 발생.

**해결**: v-for 변수를 `s`로 변경 (커밋 d4fc8e1). **교훈: useSilo의 t를 쓰는 템플릿에서 v-for 변수명으로 t 금지.**

**진단**: 브라우저 콘솔에서 `t is not a function` 확인 + 계정 선택(selectOption) 재현.

---

### Q. Render에서 관리자 계정(admin@local)으로 로그인이 안 돼요 (401)

**핵심 구분**: `403 ipNotAllowed` = IP 차단 / `401 invalidCredentials` = **계정 없음 또는 비번 오류**. 401이면 IP 제약이 아님.

**원인**: Blueprint에 `ADMIN_SEED_PASSWORD` 미설정 시 entrypoint의 seed_admin이 생략됨.

**해결**: Render 웹 서비스 → Shell 탭에서:
```bash
ADMIN_SEED_PASSWORD='<비번>' python manage.py seed_admin
```
강제변경 해제까지: `python manage.py reset_password admin@local '<pw>' --no-force-change`
(참고: `/api/auth/password/` API는 500이 날 수 있어 커맨드가 안전)

IP 화이트리스트는 전역 스위치(관리자 프로필)로 OFF 가능 — Render 등 프록시 뒤 환경에서는 OFF 권장.

---

### Q. Render에서 모바일 위젯 동작 문제 (음성입력 테두리 잔존 / 인사말 가림)

- **음성입력 해제 시 테두리 잔존**: `setMicState`가 `classList.remove→add` 방식으로 확실히 토글하도록 수정 (커밋 4360e6d)
- **모바일 채팅 패널 열면 인사말이 키보드에 가려짐**: 패널 열림 시 자동 `focus()`가 소프트 키보드를 띄워 100dvh 패널을 밀어냄 → **터치 디바이스에서는 자동 포커스 생략** (사용자가 탭할 때만 키보드)
- **"Queued 0% / 30% 멈춤"처럼 보임**: 크롤 ~1분, **Q&A 배치(OpenRouter) 3~5분은 정상 소요** — 워커 로그에 크래시 없으면 대기. 처리 중 스피너가 배지에 표시됨

---

## 접속 주소 정리

| 주소 | 포트 | 용도 |
|------|------|------|
| `http://webmcp.duckdns.org` | 80 | HTTP |
| `https://webmcp.duckdns.org:8443` | 8443 | 한국어 사일로 (ko) |
| `https://webmcp.duckdns.org:8444` | 8444 | 영어 사일로 (en) |
| `https://webmcp-front-en.onrender.com` | 443 | **Render 클라우드** 영어 사일로 (en) — Blueprint IaC |

---

## 인프라 요약

- **공유기(게이트웨이)**: `192.168.31.1`
- **서버(136)**: `192.168.31.136` (tensun@, Fedora 39, Docker)
- **공인 IP**: `203.25.124.132`
- **DuckDNS 도메인**: `webmcp.duckdns.org`
- **DuckDNS 토큰**: `69b002c5-00d0-459b-b649-d96b98b462b1`

## 주의사항

- **공인 IP가 바뀌면** (공유기 재부팅, ISP IP 변경 등) DuckDNS 갱신 URL을 다시 호출해야 합니다.
- 갱신 URL: `https://www.duckdns.org/update?domains=webmcp&token=<토큰>&ip=<공인IP>`
