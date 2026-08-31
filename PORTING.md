# PORTING.md — 다른 서버로 포팅하기 (136 배포판 기준)

> WebMCP Auto 사일로(ko/en)를 **새로운 Linux 서버에 Docker로 이식**하는 절차.
> 원본 검증环境: `192.168.31.136` (Fedora 39, Docker 27.3.1, Compose v2.21) —
> 이 문서의 명령은 해당 서버에서 실측·동작 확인을 마친 내용이다.

---

## 0. 사전 요건

| 요건 | 확인 방법 | 비고 |
|---|---|---|
| Docker 24+ / Compose v2 | `docker --version && docker compose version` | rootless 또는 docker 그룹 권한 필요 |
| 빌드 가능한 여유 공간 | 최소 5GB (이미지 2종 + postgres 데이터) | 136 검증: 805G 여유 |
| 인터넷 아웃바운드(443) | `curl -sI https://openrouter.ai/api/v1/models` | LLM API + npm(base image) |
| 외부 접속용 포트 2개 | 아래 구성 예: 8443/8444 (1024 초과면 sudo 불필요) | 80/443은 sudo 필요 |
| (SSL용) 도메인 또는 사설 DNS | DuckDNS 권장 — 무료, DNS-01 지원 | 공인 CA 인증서 또는 mkcert |

## 1. 소스 확보

### 방법 A — GitHub에서 클론 (권장)
```bash
git clone https://github.com/ilyoungkim/webmcp_auto.git
cd webmcp_auto
```

### 방법 B — 개발 mac에서 rsync (내부망, 최신 작업본 이동)
```bash
cat > /tmp/rsync-excludes.txt <<'EOF'
.git/
node_modules/
.venv/
__pycache__/
.output/
.nuxt/
crawled/
db.sqlite3
backups/
logs/
screenshot/
*.pyc
.DS_Store
EOF
rsync -az --exclude-from=/tmp/rsync-excludes.txt \
  saas/ docker/ <user>@<server>:~/webmcp_auto/
```

> **주의 — rsync 후 필수 확인**: compose의 `env_file: [../saas/backend/.env]`는
> **compose 파일 위치 기준 상대경로**다. 최종 구조는 반드시
> `~/webmcp_auto/saas/backend/.env` 가 되어야 한다.
> (136 실측: 루트에 풀린 `backend/`를 `saas/backend`으로 이동해야 했음)

### 필수 파일 체크리스트 (누락 시 빌드 실패)
```
saas/backend/            (requirements.txt, manage.py, apps/, config/, core/)
saas/widget-dist/        ★ saas/ 바로 아래 — Dockerfile COPY 경로 (frontend/public 아님)
saas/frontend/           (package.json, nuxt.config.ts, pages/, composables/ ...)
docker/docker-compose.silo.yml
docker/Dockerfile.backend / Dockerfile.frontend   ← compose build에 필수
docker/nginx-ko.conf, docker/nginx-en.conf, docker/docker-entrypoint.sh
```

## 2. 환경설정

### 2.1 `.env` (필수)
```bash
cp saas/backend/.env.example saas/backend/.env   # 또는 기존 개발 .env를 복사
```
필수 키: `GEMINI_API_KEY`(실시간 채팅), `OPENROUTER_API_KEY`(배치 Q&A), `ADMIN_SEED_PASSWORD`
- 언어별 분리(선택): `GEMINI_API_KEY_EN`, `OPENROUTER_MODEL_EN` — 없으면 전역 키 폴백

### 2.2 포트 계획 — **8080은 흔히 점유되어 있다**
136 실측: `8080`은 이미 wiki-engine이 사용 중 → **18080/18081로 변경**.
```yaml
# docker-compose.silo.yml의 nginx-ko / nginx-en services:
ports: ["18080:80"]   # ko
ports: ["18081:80"]   # en
```
> 사전 확인: `ss -tlnp | grep -E ':(8080|8081|18080|18081)'`

### 2.2.1 `SAAS_PUBLIC_URL` / `ALLOWED_HOSTS` / CSRF — 서버 주소로 치환
이 값들은 **위젯 assetBase/proxyEndpoint에 빌드 시점에 박제**된다. 서버 접속 주소로 통일할 것:
```bash
cd docker
sed -i 's|192.168.0.5:8443|webmcp.duckdns.org:8443|g; s|192.168.0.5:8444|webmcp.duckdns.org:8444|g; s|192.168.0.5:8080|webmcp.duckdns.org:8443|g; s|192.168.0.5:8081|webmcp.duckdns.org:8444|g' docker-compose.silo.yml
sed -i 's|^  ALLOWED_HOSTS:.*|  ALLOWED_HOSTS: "127.0.0.1,localhost,backend,webmcp.duckdns.org"|' docker-compose.silo.yml
# 검증
docker compose -f docker-compose.silo.yml config --quiet && echo OK
```
> ⚠️ 기존 프로젝트가 이미 있다면 assetBase에 구 주소가 박제되어 있다 → DB REPLACE 또는 위젯 재생성 필요(세션 로그 참고).

## 3. 최초 기동

```bash
cd docker
DOCKER_HOST=unix:///var/run/docker.sock docker compose -f docker-compose.silo.yml up -d --build
```
- 빌드: backend(python3.13 + node/terser), frontend(node/nuxt) — 수 분 소요
- `docker-entrypoint.sh`가 자동 실행: `migrate` → `seed_catalogs` → `seed_admin` → `collectstatic` → gunicorn
- **worker는 migrate 전에 뜨면 실패 합니다**: 로그 확인 후 `docker compose -f docker-compose.silo.yml restart worker-ko worker-en`

```bash
# 헬스체크
curl -s http://127.0.0.1:18080/health/     # {"status":"ok"}
curl -s http://127.0.0.1:18081/health/
docker ps --format '{{.Names}} {{.Status}}' | grep webmcp   # 10개 전부 Up 확인
```
- 로그인: `admin@local` / `.env`의 `ADMIN_SEED_PASSWORD` (must_change_password=True)

## 4. HTTPS (필수 — 음성입력 등 보안콘텍스트 기능 때문)

Web Speech API(위젯 음성입력)는 **HTTPS 또는 localhost에서만 동작**한다. LAN http로는 마이크가 차단되므로 TLS 필수.

### 4a. Let's Encrypt 공인 인증서 (권장 — 접속 기기에서 경고 없음)
DuckDNS는 DNS-01 challenge를 지원하므로 **공인 IP 없이도 발급 가능**:
```bash
brew install acme.sh        # 또는 curl https://get.acme.sh | sh
export DuckDNS_Token='<duckdns 토큰>'    # 정확한 변수명 — DUCKDNS_TOKEN 아님
acme.sh --issue --dns dns_duckdns -d webmcp.duckdns.org --server letsencrypt
acme.sh --install-cert -d webmcp.duckdns.org --ecc \
  --fullchain-file ~/webmcp_auto/ssl/fullchain.cer \
  --key-file      ~/webmcp_auto/ssl/webmcp.duckdns.org.key \
  --reloadcmd 'nginx -s reload -c ~/webmcp_auto/webmcp_silo_https.conf'
```
- DNS A 레코드를 **사설 IP(예: 192.168.31.136)로** 갱신하면 LAN 전용 접속이 되어 인터넷 노출이 없다:
  `https://www.duckdns.org/update?domains=webmcp&token=...&ip=192.168.31.136`
  ⚠️ `ip` 파라미터를 빼먹으면 **호출한 기기의 공인 IP로 덮어써진다** (실제 사고 사례 — 반드시 명시).

### 4b. 호스트 nginx 리버스 프록시 (TLS 종료 → Docker 사일로)
`~/webmcp_auto/webmcp_silo_https.conf` — 독립 nginx 인스턴스(pid/tmp/logs를 홈에 두면 **sudo 불필요**):
```nginx
server {
    listen 8443 ssl;  http2 on;
    server_name webmcp.duckdns.org;
    ssl_certificate     /home/<user>/webmcp_auto/ssl/fullchain.cer;
    ssl_certificate_key /home/<user>/webmcp_auto/ssl/webmcp.duckdns.org.key;
    location / {
        proxy_pass http://127.0.0.1:18080;
        proxy_set_header Host $host:8443;
        proxy_set_header X-Forwarded-Proto https;      # 필수
        proxy_set_header Origin https://$host:8443;    # CSRF/Origin 정합
        proxy_read_timeout 180s;                       # LLM 지연 대비
    }
}
# (en은 :8444 → 18081로 동일 구성)
```
```bash
nginx -c ~/webmcp_auto/webmcp_silo_https.conf   # 시작 (sudo 불필요)
nginx -s reload -c ~/webmcp_auto/webmcp_silo_https.conf
```
> 참고: homebrew nginx는 기본 설정에 `listen 8080`이 있어 Docker와 충돌할 수 있다 → `nginx.conf`의 기본 server 블록 주석 처리.

## 5. 검증 체크리스트

```bash
# 1) 컨테이너 10개 전부 Up (2 healthy)
docker ps | grep webmcp
# 2) 사일로별 헬스
curl -s http://127.0.0.1:18080/health/ && curl -s http://127.0.0.1:18081/health/
# 3) HTTPS 인증서 체인
echo | openssl s_client -connect 127.0.0.1:8443 -servername webmcp.duckdns.org 2>/dev/null | grep 'Verify return code'
#    → Verify return code: 0 (ok)
# 4) 언어 격리 — 랜딩 문구로 확인
#   ko: "무료로 시작" / en: "Get started free"
# 5) 채팅 E2E: 미리보기 → 퀵메뉴 즉답(캐시) + 자유 질문(LLM) 응답 확인
```

## 6. 자주 발생하는 이슈 (FAQ)

| 증상 | 원인 | 해결 |
|---|---|---|
| `bind() to 0.0.0.0:8080 failed: Address already in use` | 호스트 nginx 기본 설정 또 다른 서비스 | nginx.conf 기본 서버 블록 주석 / 포트 변경 |
| `failed to read dockerfile` | Dockerfile이 compose `context`에 없음 | compose와 같은 상대경로 위치에 Dockerfile 배치 |
| `"/saas/widget-dist": not found` | `saas/widget-dist/`미존재(frontend/public 만 있음) | `saas/widget-dist/`로 복사 — Dockerfile COPY 경로 |
| 컨테이너 재시작 후 nginx 502 (`Host is unreachable`) | 정적 upstream의 시작 시 1회 resolve | resolver 기반 proxy_pass(적용됨) 또는 nginx restart |
| 데이터 일부만 복원됨, 이후 PK 충돌 | 시퀀스 뒤처짐 | `setval(pg_get_serial_sequence(테이블,'id'), MAX(id))` — 테이블마다 |
| 위젯 채팅 504 | Gemini 실시간 호출 지연 | 호스트 nginx `proxy_read_timeout 180s` 상향, 필요 시 백엔드 타임아웃 정책 조정 |

## 7. 새 언어 사일로 추가

`docker/HOWTO.md` §4.0 절차에 따른다 — 요약:
1. `core/langsilo.py`의 `SUPPORTED_LANGS`에 코드 추가
2. `seed_catalogs.py`에 `SEED_XX` 시드 작성 (ko/en과 1:1 대응 권장 — 현재 27종×4메뉴 대칭)
3. `docker-compose.silo.yml`에 서비스 5개 추가 (postgres-XX, backend-XX, worker-XX, frontend-XX, nginx-XX)
4. `.env`에 `GEMINI_API_KEY_XX` 설정(선택)
5. `up -d --build` → `migrate` → 시드 → nginx 설정 추가
## 8. Render Blueprint (클라우드 원클릭 포팅)

> Linux 서버 대신 **Render**에 올린다면 repo 루트의 **`render.yaml`** (Blueprint)으로
> 웹 2 + 워커 2 + DB 2를 한 번에 프로비저닝할 수 있다.

```bash
# 구성 요약 (render.yaml)
#   databases: webmcp-postgres-ko / webmcp-postgres-en  (Managed PG, plan basic-256mb)
#   services:
#     webmcp-web-ko    (web,    Dockerfile.backend, healthCheck /api/health/)
#     webmcp-worker-ko (worker, dockerCommand: run_pipeline_worker --interval 2.0)
#     webmcp-web-en    / webmcp-worker-en (동일 구성의 en 사일로)
```

**배포 절차**
1. Render Dashboard → `New → Blueprint` → 이 저장소 선택 (render.yaml 자동 인식)
2. `sync: false` 항목 입력 (GEMINI_API_KEY, OPENROUTER_API_KEY, SAAS_PUBLIC_URL, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS)
3. 첫 배포 완료 후 헬스체크 `https://webmcp-ko.onrender.com/api/health/` 확인

**필수 코드 조정 (1줄)** — entrypoint가 0.0.0.0:8000 고정이므로 Render 포트와 맞추려면:
```dockerfile
# docker/Dockerfile.backend 의 CMD → 환경변수 PORT 지원
# docker-entrypoint.sh 의 gunicorn bind 를 다음으로 교체 권장:
#   --bind "0.0.0.0:${PORT:-8000}"
```

**요금 개요**
| 서비스 | 플랜 | 월 |
|---|---|---|
| Web ×2 (starter) | 512MB | $7 × 2 |
| Worker ×2 (starter) | — | $7 × 2 |
| PostgreSQL ×2 (basic-256mb) | | $6.90 × 2 |
| **합계** | | **약 $28/mo** |

- 개발 검증은 ko 1개(web+worker+db ≈ $14/mo)로 먼저 시작하는 것을 권장.
- 프론트(Nuxt)를 Cloudflare Pages로 분리하면 비용·성능 모두 개선 가능.
