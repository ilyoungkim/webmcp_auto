# WebMCP Auto — 완전 자동화 AI 비서 SaaS

> **URL만 입력하면** 크롤 → LLM Q&A → 위젯 생성 → 미리보기 → 설치까지 자동화하는
> 멀티테넌트 AI 비서 위젯 SaaS.

- **콘솔 프론트**: Nuxt.js 3 (`saas/frontend`)
- **백엔드**: Python Django 5 + DRF (`saas/backend`)
- **DB**: SQLite(로컬 검증) / PostgreSQL(Docker 운영)
- **배포**: Docker Compose (`docker/`)

---

## 주요 기능

| 영역 | 기능 |
|------|------|
| 계정 | 가입·로그인·비밀번호 변경(강제변경 포함), 플랜(free/pro/admin), **로그아웃 시 세션 확실 삭제** |
| 프로젝트 | URL 입력 → 크롤 → LLM Q&A → 위젯 생성 자동화, **최대 5개** 생성(대시보드 안내) |
| 프로젝트 수정 | **이름/URL 변경 금지**, 도메인 유형·위젯 테마만 변경 가능 |
| 빠른메뉴 | 질문 편집 **1회 제한**, 저장된 소스로 답변 재생성, **"AI비서란?" 필수 메뉴(편집 불가)** |
| 위젯 | 5종 테마, 미리보기, `bundle.zip` 설치 번들(난독화), **AI 로고 아이콘**, **음성 입력(두 줄 버튼)**, **답변 생성 중 입력 잠금** |
| 데이터 플레인 | `/embed/<publicId>.js` 로더, `/api/chat/` 실시간 채팅, Origin 화이트리스트, 쿼터 |
| 관리자 | 사용자·프로젝트·고객센터 관리, **테넌트별 Gemini 설정(테스트 후 적용)** |
| 고객센터 | Q&A 게시판(질문 2000자, 10개/페이지) |
| 이용약관 | 프로젝트 페이지 하단 "읽어볼 내용" 아코디언(이용약관/AI 이용고지/개인정보처리방침/프로그램 사용동의) |
| SEO | **전 페이지 noindex·nofollow**, `robots.txt` 전체 접근 금지, `llms.txt` 제공 |
| 다국어 사일로 | **ko/en 완전 분리** — 언어별 DB·컨테이너·LLM 엔진·카탈로그·위젯UI·콘솔UI 독립 실행 |

## LLM 구성

| 용도 | 공급자 | 모델 | 설정 위치 |
|------|--------|------|-----------|
| 실시간 채팅·사이트 요약 | Google Gemini | `gemini-3.5-flash-lite` | 전역 `.env` 또는 **테넌트별 지정** |
| Q&A 배치 생성 | OpenRouter | `openai/gpt-oss-120b` | 전역 `.env` 전용 |
| 폴백 모델 | OpenRouter | `deepseek/deepseek-v4-flash-latest` | 전역 `.env` 전용 |

> **테넌트(프로젝트)별 Gemini 설정**: 관리자가 `/admin/projects` → "⚙ LLM 설정"에서
> 프로젝트 단위로 Gemini API 키/모델을 지정할 수 있습니다. **테스트 후 적용** 방식으로
> 실제 호출 검증에 성공한 키만 저장되며, 비워두면 전역 `.env` 값을 사용합니다.
> OpenRouter는 전역 `.env`로만 관리됩니다.

## 빠른 시작 (Docker) — build.sh

`docker/build.sh` 가 이미지 컴파일(빌드) + 기동 + health 체크를 한 번에 처리합니다.
**기본값은 ko + en 모두 빌드**이며, `--ko`/`--en` 으로 특정 언어만 지정할 수 있습니다.

```bash
cd docker
# saas/backend/.env 에 GEMINI_API_KEY, OPENROUTER_API_KEY 채우기

./build.sh                  # ko(8080) + en(8081) 사일로 모두 빌드
./build.sh --ko             # ko 사일로만 빌드
./build.sh --en             # en 사일로만 빌드
./build.sh --no-cache       # 캐시 무시 완전 재빌드

./build.sh --run            # 빌드 후 ko + en 모두 기동 + health 체크
./build.sh --run ko         # 빌드 후 ko(8080)만 기동
./build.sh --run en         # 빌드 후 en(8081)만 기동

./build.sh --dry-run        # 실행할 명령만 출력 (빌드 테스트, 실제 빌드 안 함)
./build.sh --list           # 등록된 언어 사일로 목록
./build.sh --help           # 전체 사용법
```

### 접속 주소

| 사일로 | 주소 | 언어 |
|--------|------|------|
| ko | http://localhost:8080 | 한국어 콘솔·위젯 (도메인 26종) |
| en | http://localhost:8081 | English console·widget (도메인 16개) |
| ko (LAN) | http://192.168.31.248:8080 | 사내망 기기에서 접속 (같은 192.168 네트워크) |
| en (LAN) | http://192.168.31.248:8081 | 사내망 기기에서 접속 |

- en 사일로는 별도 DB(`webmcp_en`)·컨테이너로 완전 분리되어 있습니다.
- **LAN 접속**: `192.168.x.x` 대역에서 8080/8081 접속 허용 (DB 5432는 로컬 전용 — 포트매핑 없음)
- **새 언어 추가** (일본어·중국어·프랑스어·스페인어·포르투갈어 등)는
  [`docker/HOWTO.md`](docker/HOWTO.md) §4.0의 4단계 절차를 따릅니다.

수동 실행(스크립트 없이):

```bash
cd docker
docker compose -f docker-compose.silo.yml up -d --build    # ko + en 사일로 모두
docker compose -f docker-compose.silo.yml build postgres-ko backend-ko worker-ko frontend-ko nginx-ko   # ko만
docker compose -f docker-compose.silo.yml build postgres-en backend-en worker-en frontend-en nginx-en   # en만
docker compose -f docker-compose.silo.yml exec backend-ko python manage.py migrate      # 마이그레이션
```

#### Compose 파일 안내 (1개 사용)

- **`docker-compose.silo.yml` — 현재 사용하는 유일한 배포 파일** (단일 진실 공급원).
  ko + en 사일로 전부 이 파일에 정의되어 있고, `build.sh --ko/--en`은 내부에서
  `*-ko`/`*-en` 서비스만 필터링해 실행한다.
- `docker-compose.yml` — **퇴역(legacy)**. 다국어 사일로 이전의 단일 한국어 배포용으로
  참고용만 남겨둠. **실행에 사용하지 말 것** (혼용 시 8080 포트 충돌·구 DB(`webmcp`) 분기 위험).
  문서 보존이 필요 없다면 삭제해도 안전합니다.
- **`ALLOWED_HOSTS` 참고**: `settings.py`의 자기 IP 자동 탐지(`ALLOW_SELF_IP`, 기본 `true`)가
  서버가 가진 모든 IP를 자동 허용하므로, compose의 ALLOWED_HOSTS는 보조 수단이며
  이관 시 `SAAS_PUBLIC_URL`/`CSRF_TRUSTED_ORIGINS`(위젯 박제용)만 수동 갱신하면 된다.

> 관리자 계정: `admin@local` / `.env`의 `ADMIN_SEED_PASSWORD`

---

## Docker Compose 설정 백업 (복구용 레퍼런스)

> 아래는 **현재 사용 중인 `docker/docker-compose.silo.yml` 전문 백업** (2026-08-30 기준, 커밋 `5a29848`).
> 파일이 손상되었거나 특정 시점으로 되돌려야 할 때 이 내용을 그대로 복사해 복원할 수 있습니다.
>
> **복구 방법**: 아래 내용을 `docker/docker-compose.silo.yml`로 저장한 뒤,
> `192.168.31.248`(LAN IP)을 서버의 현재 IP로 바꾸고
> `cd docker && docker compose -f docker-compose.silo.yml up -d` 를 실행한다.
> (또는 `./build.sh --run` — 빌드+기동+health 체크)

```yaml
# ─────────────────────────────────────────────────────────────
# WebMCP Auto — 언어 사일로 분리 배포 (완전 독립 스택)
# ─────────────────────────────────────────────────────────────
# 언어마다 DB·백엔드·프론트·포트가 완전히 분리되어 별도 사이트처럼 동작한다.
#   한국어 사일로: http://localhost:8080  (WEBMCP_LANG=ko,  DB: webmcp_ko)
#   영어   사일로: http://localhost:8081  (WEBMCP_LANG=en,  DB webmcp_en)
#
# 실행:
#   cd docker
#   ./build.sh --run            # ko + en 사일로 모두 빌드·기동 + health 체크 (권장)
#   docker compose -f docker-compose.silo.yml up -d --build   # compose 직접 실행
#
# 언어별 엔진 분리는 saas/backend/.env 에서:
#   GEMINI_API_KEY_EN=...        (en 사일로 전용 키, 없으면 전역 키 폴백)
#   GEMINI_MODEL_EN=gemini-2.0-flash
#   OPENROUTER_MODEL_EN=openai/gpt-4o-mini
#   WEBMCP_LANGS=ko,en           (이 배포가 지원하는 언어)
# ─────────────────────────────────────────────────────────────

x-backend-env: &backend-env
  DJANGO_DEBUG: "false"
  # http(LAN 192.168.x.x) 접속에서 브라우저가 세션/CSRF 쿠키를 저장하도록 Secure 속성을 끈다.
  # 인터넷 공개(https) 시 true 로 되돌릴 것 (settings.SECURE_COOKIES, 기본값 true)
  SECURE_COOKIES: "false"
  # LAN(192.168.x.x) 원격 접속 허용 — 네트워크가 바뀌면 이 목록과 아래 CSRF에도 IP 추가 필요
  # (보안 유의: 이 값은 로컬/사내망 공유용. 인터넷 공인 노출 시엔 공인 도메인으로 교체할 것)
  ALLOWED_HOSTS: "127.0.0.1,localhost,backend,192.168.31.248,192.168.64.1"
  TERSER_CMD: "terser"
  GUNICORN_WORKERS: "2"
  GUNICORN_THREADS: "2"

services:
  # ── 한국어 사일로 (기본) ─────────────────────────────────────
  postgres-ko:
    image: postgres:18-alpine
    container_name: webmcp-postgres-ko
    environment:
      - POSTGRES_USER=webmcp
      - POSTGRES_PASSWORD=webmcp_dev_pass
      - POSTGRES_DB=webmcp_ko
    volumes:
      - postgres_data_ko:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U webmcp -d webmcp_ko"]
      interval: 5s
      timeout: 5s
      retries: 10
    expose: ["5432"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  backend-ko:
    build:
      context: ../
      dockerfile: docker/Dockerfile.backend
    container_name: webmcp-ko-backend
    env_file: [../saas/backend/.env]
    environment:
      <<: *backend-env
      WEBMCP_LANG: ko
      WEBMCP_LANGS: ko
      DATABASE_URL: postgres://webmcp:webmcp_dev_pass@postgres-ko:5432/webmcp_ko
      # 위젯 assetBase/proxyEndpoint 에 박제되는 공개 주소 — LAN 접속자도 이 주소로 위젯 로드
      SAAS_PUBLIC_URL: http://192.168.31.248:8080
      CSRF_TRUSTED_ORIGINS: http://localhost:8080,http://127.0.0.1:8080,http://192.168.31.248:8080
    depends_on:
      postgres-ko: { condition: service_healthy }
    expose: ["8000"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  worker-ko:
    build:
      context: ../
      dockerfile: docker/Dockerfile.backend
    container_name: webmcp-ko-worker
    command: ["python", "manage.py", "run_pipeline_worker", "--interval", "2.0"]
    env_file: [../saas/backend/.env]
    environment:
      <<: *backend-env
      WEBMCP_LANG: ko
      WEBMCP_LANGS: ko
      DATABASE_URL: postgres://webmcp:webmcp_dev_pass@postgres-ko:5432/webmcp_ko
      SAAS_PUBLIC_URL: http://192.168.31.248:8080
      CSRF_TRUSTED_ORIGINS: http://localhost:8080,http://127.0.0.1:8080,http://192.168.31.248:8080
    depends_on:
      postgres-ko: { condition: service_healthy }
    expose: ["8000"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  frontend-ko:
    build:
      context: ../
      dockerfile: docker/Dockerfile.frontend
      args: { API_HOST: "http://backend-ko:8000" }
    container_name: webmcp-ko-frontend
    environment:
      - NUXT_PUBLIC_SILO_LANG=ko
    depends_on: [backend-ko]
    expose: ["3000"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  nginx-ko:
    image: nginx:stable-alpine
    container_name: webmcp-ko-nginx
    depends_on: [backend-ko, frontend-ko]
    ports: ["8080:80"]
    volumes: ["./nginx-ko.conf:/etc/nginx/nginx.conf:ro"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  # ── 영어 사일로 — 완전히 독립된 DB·백엔드·프론트엔드·포트 ─────
  postgres-en:
    image: postgres:18-alpine
    container_name: webmcp-postgres-en
    environment:
      - POSTGRES_USER=webmcp
      - POSTGRES_PASSWORD=webmcp_dev_pass
      - POSTGRES_DB=webmcp_en
    volumes:
      - postgres_data_en:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U webmcp -d webmcp_en"]
      interval: 5s
      timeout: 5s
      retries: 10
    expose: ["5432"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  backend-en:
    build:
      context: ../
      dockerfile: docker/Dockerfile.backend
    container_name: webmcp-en-backend
    env_file: [../saas/backend/.env]
    environment:
      <<: *backend-env
      WEBMCP_LANG: en
      WEBMCP_LANGS: en
      DATABASE_URL: postgres://webmcp:webmcp_dev_pass@postgres-en:5432/webmcp_en
      # 위젯 assetBase/proxyEndpoint 에 박제되는 공개 주소 — LAN 접속 허용
      SAAS_PUBLIC_URL: http://192.168.31.248:8081
      CSRF_TRUSTED_ORIGINS: http://localhost:8081,http://127.0.0.1:8081,http://192.168.31.248:8081
      # ── 영어 사일로 전용 엔진 (env 접미사 _EN — 없으면 전역 키 폴백) ──
      # GEMINI_MODEL_EN=gemini-2.0-flash
      # GEMINI_API_KEY_EN=...
      # OPENROUTER_MODEL_EN=openai/gpt-4o-mini
      # OPENROUTER_FALLBACK_MODEL_EN=~deepseek/deepseek-chat
    depends_on:
      postgres-en: { condition: service_healthy }
    expose: ["8000"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  worker-en:
    build:
      context: ../
      dockerfile: docker/Dockerfile.backend
    container_name: webmcp-en-worker
    command: ["python", "manage.py", "run_pipeline_worker", "--interval", "2.0"]
    env_file: [../saas/backend/.env]
    environment:
      <<: *backend-env
      WEBMCP_LANG: en
      WEBMCP_LANGS: en
      DATABASE_URL: postgres://webmcp:webmcp_dev_pass@postgres-en:5432/webmcp_en
      SAAS_PUBLIC_URL: http://192.168.31.248:8081
      CSRF_TRUSTED_ORIGINS: http://localhost:8081,http://127.0.0.1:8081,http://192.168.31.248:8081
    depends_on:
      postgres-en: { condition: service_healthy }
    expose: ["8000"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  frontend-en:
    build:
      context: ../
      dockerfile: docker/Dockerfile.frontend
      args: { API_HOST: "http://backend-en:8000" }
    container_name: webmcp-en-frontend
    environment:
      - NUXT_PUBLIC_SILO_LANG=en
    depends_on: [backend-en]
    expose: ["3000"]
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

  nginx-en:
    image: nginx:stable-alpine
    container_name: webmcp-en-nginx
    depends_on: [backend-en, frontend-en]
    ports: ["8081:80"]
    volumes:
      - ./nginx-en.conf:/etc/nginx/nginx.conf:ro
    logging: { driver: json-file, options: { max-size: "10m", max-file: "28" } }

volumes:
  postgres_data_ko:
  postgres_data_en:
```

### 백업 시점 참고 (변경 히스토리)

| 설정값 | 값 | 도입 커밋 |
|---|---|---|
| `SECURE_COOKIES: "false"` | http(LAN) 로그인용 — 스마트폰 쿠키 저장 허용 | `07e19df` |
| `ALLOWED_HOSTS`에 LAN IP | `192.168.31.248, 192.168.64.1` | `597b095` |
| `SAAS_PUBLIC_URL` = LAN | 위젯 assetBase/proxyEndpoint 박제 (LAN 접속자 위젯 로드) | `597b095` |
| `nginx-ko.conf` (backend-ko upstream) | 구 nginx.conf로는 silo 네트워크에 backend 없어 기동 실패 | `caf04fc` |

> **운영 전환 시 참고**: 위값들을 도메인/https로 변경하는 체크리스트는
> [`plan.md`](plan.md) §0.11.7 및 [`DEPLOY_PORUDCTION.md`](DEPLOY_PORUDCTION.md) §5.1 참조.

## 로컬 개발 (SQLite)

```bash
cd saas/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 키 채우기
python manage.py migrate
python manage.py seed_catalogs
python manage.py seed_admin
python manage.py runserver 0.0.0.0:8000
# 별도 터미널: 파이프라인 워커
python manage.py run_pipeline_worker --interval 2.0
```

프론트엔드(Nuxt)는 `saas/frontend`에서 `npm install && npm run dev`로 실행합니다.

## 문서

- [`plan.md`](plan.md) — 전체 설계·구현 현황·API 스펙
- [`docker/HOWTO.md`](docker/HOWTO.md) — Docker 설치·운영·백업
- [`DEPLOY_PORUDCTION.md`](DEPLOY_PORUDCTION.md) — 프로덕션 배포
