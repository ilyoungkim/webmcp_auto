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
| ko | http://localhost:8080 | 한국어 콘솔·위젯 (도메인 25종) |
| en | http://localhost:8081 | English console·widget (도메인 15종) |

- en 사일로는 별도 DB(`webmcp_en`)·컨테이너로 완전 분리되어 있습니다.
- **새 언어 추가** (일본어·중국어·프랑스어·스페인어·포르투갈어 등)는
  [`docker/HOWTO.md`](docker/HOWTO.md) §4.0의 4단계 절차를 따릅니다.

수동 실행(스크립트 없이)은 아래와 같습니다:

```bash
cd docker
docker compose up -d --build                # ko 사일로
docker compose -f docker-compose.silo.yml up -d --build   # en 사일로
```

> 관리자 계정: `admin@local` / `.env`의 `ADMIN_SEED_PASSWORD`

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
