# WebMCP Auto — Docker 설치 · 사용 방법 (HOWTO)

본 문서는 WebMCP Auto SaaS를 **Docker 기반으로 실행**하는 방법을 설명합니다.
`docker/` 폴더에 있는 `docker-compose.yml`을 중심으로 전체 스택(Django + Nuxt + PostgreSQL + nginx + pipeline worker)을 한 번에 띄울 수 있습니다.

---

## 1. 구성 개요

`docker compose up`으로 아래 5개 컨테이너가 함께 기동됩니다.

| 컨테이너 | 역할 | 내부 포트 | 외부 노출 |
|----------|------|-----------|-----------|
| `webmcp-postgres` | PostgreSQL 16 (DB) | 5432 | 없음 |
| `webmcp-backend` | Django + DRF + gunicorn (API) | 8000 | 없음 |
| `webmcp-worker` | 파이프라인 워커 (크롤→Q&A→위젯) | - | 없음 |
| `webmcp-frontend` | Nuxt 3 콘솔 (SSR/CSR) | 3000 | 없음 |
| `webmcp-nginx` | 리버스 프록시 (진입점) | 80 | **8080** |

```
브라우저 ──> nginx:8080
              ├── /api, /django-admin, /embed, /preview, /widget-dist, /health, /ready → backend:8000
              └── 그 외 (콘솔 페이지·자산) → frontend:3000
```

**최종 접속 주소: `http://localhost:8080`**

---

## 2. 사전 준비

### 2.1 Docker 설치 (아직 없을 때)

- **macOS**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치 후 앱 실행
- **Windows**: Docker Desktop (WSL2 백엔드) 설치
- **Linux(Ubuntu/Debian)**: 아래 예시
  ```bash
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  ```

### 2.2 설치 확인

```bash
docker --version        # Docker 24+
docker compose version  # Compose v2
```

macOS의 경우 Docker Desktop이 **실행 중**이어야 daemon이 연결됩니다.
아래 명령으로 daemon 연결을 확인합니다.

```bash
docker info --format '{{.ServerVersion}}'
# 오류(Cannot connect)가 나면 Docker Desktop을 실행 후 다시 시도
```

---

## 3. 최초 설정

### 3.1 백엔드 환경변수 (`.env`)

`docker compose`는 `saas/backend/.env`를 읽어 컨테이너에 주입합니다.
아래 항목을 **실제 값**으로 채워주세요. (파일이 없으면 `.env.example`을 복사)

```bash
cd saas/backend
cp .env.example .env
# 편집: GEMINI_API_KEY, OPENROUTER_API_KEY 등 채우기
```

| 변수 | 필수 | 설명 |
|------|:----:|------|
| `GEMINI_API_KEY` | ✅ | 실시간 채팅·사이트 요약용 (Gemini) |
| `OPENROUTER_API_KEY` | ✅ | Q&A 배치 생성용 (OpenRouter) |
| `OPENROUTER_MODEL` | | Q&A 생성 모델 (기본 `openai/gpt-oss-120b`) |
| `ADMIN_SEED_EMAIL` | | 관리자 이메일 (기본 `admin@local`) |
| `ADMIN_SEED_PASSWORD` | ✅* | 관리자 초기 비밀번호 (*비워두면 관리자 시드 생략) |
| `GEMINI_MODEL` | | 채팅 모델 (기본 `gemini-3.5-flash-lite`) |

> **테넌트(프로젝트)별 Gemini 설정**: 관리자는 콘솔 `/admin/projects` → 프로젝트의 **"⚙ LLM 설정"** 에서 프로젝트 단위로 Gemini API 키/모델을 지정할 수 있습니다. 비워두면 위 `.env`의 전역 값을 사용합니다. **OpenRouter는 전역 `.env`로만 관리**되며 테넌트에서 변경할 수 없습니다.

> `DATABASE_URL`은 compose에서 자동으로 PostgreSQL(`webmcp:webmcp_dev_pass@postgres:5432/webmcp`)로 주입됩니다. **`.env`에 따로 넣지 마세요.**

---

## 4. 빌드 & 실행

### 4.1 이미지 빌드

```bash
cd webMCP_Auto/docker   # docker-compose.yml 위치
docker compose build
```

### 4.2 전체 스택 시작

```bash
docker compose up -d
```

- `-d`: 백그라운드 실행
- 첫 실행 시 PostgreSQL·nginx 이미지를 pull하고, backend에서
  `migrate → seed_catalogs(25종 도메인) → seed_admin → collectstatic → gunicorn`이 자동 수행됩니다.

### 4.3 상태 확인

```bash
docker compose ps
```

모든 컨테이너가 `Up` 상태여야 합니다. (postgres는 `(healthy)`)

| 상태 | 의미 |
|------|------|
| `Up` | 실행 중 |
| `(healthy)` | 헬스체크 통과 (postgres) |
| `Restarting` / `Exited` | 로그 확인 필요 (§7 참고) |

### 4.4 접속

| 대상 | 주소 |
|------|------|
| 콘솔(랜딩/대시보드/관리자) | `http://localhost:8080` |
| Django Admin | `http://localhost:8080/django-admin/` |
| 상태 확인 (health) | `http://localhost:8080/health/` |
| Gemini 키 준비 여부 | `http://localhost:8080/ready/` |

---

## 5. 파이프라인 워커

`webmcp-worker` 컨테이너가 **프로젝트 생성 → 크롤 → LLM Q&A → 위젯 생성** 파이프라인을
2초 간격으로 폴링하며 처리합니다. 별도 실행이 필요 없습니다.

- **로그 확인**
  ```bash
  docker compose logs -f worker
  ```
- **동작 확인**: 콘솔에서 프로젝트를 생성하면 `queued → crawling → generating → completed`로 진행됩니다.

---

## 6. 데이터 · 볼륨

- PostgreSQL 데이터는 **명명 볼륨 `docker_postgres_data`** 에 저장됩니다.
  ```bash
  docker volume ls | grep postgres_data
  ```
- `docker compose down`은 데이터를 **삭제하지 않습니다.**
- 데이터까지 완전 삭제하려면:
  ```bash
  docker compose down -v
  ```

---

## 7. 자주 쓰는 명령

| 작업 | 명령 |
|------|------|
| 백그라운드 시작 | `docker compose up -d` |
| 로그 실시간 확인 | `docker compose logs -f <backend\|worker\|nginx>` |
| 컨테이너 안 셸 | `docker compose exec backend sh` |
| Django 관리 커맨드 | `docker compose exec backend python manage.py <cmd>` |
| 관리자 비밀번호 초기화 | `docker compose exec backend python manage.py reset_password admin@local <newpw> --no-force-change` |
| DB 직접 조회 | `docker compose exec postgres psql -U webmcp -d webmcp` |
| 중지 (데이터 유지) | `docker compose down` |
| 완전 삭제 (데이터 포함) | `docker compose down -v` |
| 이미지 재빌드 | `docker compose build --no-cache backend` |

---

## 8. 문제 해결

### 8.1 컨테이너가 계속 재시작됨
```bash
docker compose logs backend
```
- `OperationalError: connection ... postgres` → backend가 postgres보다 먼저 떠서 연결 실패.
  `docker compose up -d`를 다시 실행하면 헬스체크 후 연결됩니다.
- GEMINI/OPENROUTER 키 오류 → `.env` 값 확인 후 `docker compose restart backend worker`

### 8.2 로그인이 안 됨 (관리자)
Docker의 관리자는 `.env`의 `ADMIN_SEED_PASSWORD`로 시드됩니다.
비밀번호를 모르면 초기화:
```bash
docker compose exec backend python manage.py reset_password admin@local test1234 --no-force-change
```

### 8.3 포트 8080 충돌
다른 프로그램이 8080을 쓰면 `docker-compose.yml`의 `ports: "8080:80"`을
예: `"9080:80"`으로 바꾼 뒤 `docker compose up -d`로 재시작.

### 8.4 위젯 채팅 403 "사용이 중지된 위젯입니다."
해당 프로젝트가 `enabled=false`(사용중지) 상태입니다. 콘솔 `/admin/projects`에서 "사용재개"를 누르세요.

---

## 9. 로컬 개발(SQLite)과의 차이

| 항목 | Docker | 로컬 개발 |
|------|--------|-----------|
| DB | PostgreSQL (DATABASE_URL) | SQLite (`db.sqlite3`) |
| 서버 | gunicorn + Nuxt build + nginx | `manage.py runserver` + `nuxt dev` |
| 접속 | `http://localhost:8080` | `http://127.0.0.1:53300` |
| 관리자 비밀번호 | `.env`의 `ADMIN_SEED_PASSWORD` | 로컬 DB의 계정 |

두 환경은 **별도 DB**를 사용하므로 데이터가 공유되지 않습니다.

---

## 10. 디렉터리 구조

```
webMCP_Auto/
├── docker/                     # Docker 구성 (docker compose 실행 위치)
│   ├── docker-compose.yml     # 5개 서비스 정의 (postgres/backend/worker/frontend/nginx)
│   ├── .dockerignore          # 빌드에서 제외할 파일
│   ├── Dockerfile.backend     # Django + gunicorn + terser(난독화) + psycopg
│   ├── Dockerfile.frontend    # Nuxt 빌드 + node 서버
│   ├── docker-entrypoint.sh   # migrate → seed → collectstatic → gunicorn
│   ├── nginx.conf             # 리버스 프록시 라우팅
│   └── HOWTO.md               # 본 문서
└── saas/                      # 소스 (backend/frontend/widget-dist)
```
