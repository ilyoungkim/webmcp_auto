"""
Django settings — WebMCP Auto SaaS (검증 단계: SQLite)
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# ── env ──────────────────────────────────────────────────────
def env(key, default=''):
    return os.environ.get(key, default)

SECRET_KEY = env('DJANGO_SECRET_KEY', 'dev-only-insecure-key-change-me')
DEBUG = env('DJANGO_DEBUG', 'true').lower() == 'true'
ALLOWED_HOSTS = [h for h in env('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h]

# ── apps ─────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    # saas apps
    'apps.accounts',
    'apps.catalogs',
    'apps.projects',
    'apps.pipeline',
    'apps.widgets',
    'apps.proxy',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ]},
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── DB ────────────────────────────────────────────────────────
# DATABASE_URL 가 있으면 (Docker 등) PostgreSQL, 없으면 SQLite(로컬 검증).
# 예: postgres://user:pass@host:5432/dbname
_DATABASE_URL = env('DATABASE_URL', '')
if _DATABASE_URL:
    from urllib.parse import urlsplit
    _dbu = urlsplit(_DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': (_dbu.path or '/webmcp').lstrip('/'),
            'USER': _dbu.username or '',
            'PASSWORD': _dbu.password or '',
            'HOST': _dbu.hostname or 'localhost',
            'PORT': _dbu.port or 5432,
            'CONN_MAX_AGE': 60,
            'OPTIONS': {'connect_timeout': 10},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
                'init_command': "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;",
            },
        }
    }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
]

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── DRF ──────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser',
}

CSRF_COOKIE_HTTPONLY = False          # Nuxt가 읽어 X-CSRFToken 헤더로 전달
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ── SaaS 설정 ────────────────────────────────────────────────
GEMINI_API_KEY = env('GEMINI_API_KEY')
GEMINI_MODEL = env('GEMINI_MODEL', 'gemini-3.5-flash-lite')
GEMINI_BASE = env('GEMINI_BASE', 'https://generativelanguage.googleapis.com/v1beta')
OPENROUTER_API_KEY = env('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = env('OPENROUTER_MODEL', 'mistralai/mistral-nemo')
OPENROUTER_FALLBACK_MODEL = env('OPENROUTER_FALLBACK_MODEL', '~deepseek/deepseek-v4-flash-latest')
OPENROUTER_BASE = env('OPENROUTER_BASE', 'https://openrouter.ai/api/v1')
SAAS_PUBLIC_URL = env('SAAS_PUBLIC_URL', 'http://127.0.0.1:53300')
ADMIN_SEED_EMAIL = env('ADMIN_SEED_EMAIL', 'admin@local')
ADMIN_SEED_PASSWORD = env('ADMIN_SEED_PASSWORD', '')
JOB_LOCK_MINUTES = int(env('JOB_LOCK_MINUTES', '15'))
# 문의/오류 안내에 노출되는 대표 연락처 (관리자 프로필 페이지에서 수정 가능,
# 값이 비으면 이 기본값 사용. .env 의 SUPPORT_PHONE 으로 초기 기본값 지정 가능)
SUPPORT_PHONE = env('SUPPORT_PHONE', '02-888-9999')
# ── 다국어 사일로 ────────────────────────────────────────────
# 이 컨테이너가 담당하는 언어 및 지원 언어 목록 (ko | en, 콤마 구분).
# ko 컨테이너는 lang='ko' 카탈로그만, en 컨테이너는 lang='en' 카탈로그만 노출한다.
WEBMCP_LANG = env('WEBMCP_LANG', 'ko')
WEBMCP_LANGS = env('WEBMCP_LANGS', 'ko')

# ── 위젯 번들 난독화 ─────────────────────────────────────────
# bundle.zip 의 JS 파일을 terser 로 난독화+최적화한다.
# terser 가 없으면 원본 JS 를 그대로 넣는다 (폴백).
# terser 실행 파일 경로 (npx --no-install 로 node_modules 의 terser 사용).
TERSER_CMD = env('TERSER_CMD', 'npx --no-install terser')
# terser 를 찾을 작업 디렉터리 (frontend/node_modules 에 terser 가 설치되어 있음)
TERSER_CWD = env('TERSER_CWD', str(Path(BASE_DIR).parent / 'frontend'))

# 개발: Nuxt(53300)가 /api 를 Django(8000)로 프록시할 때 브라우저 Origin 이
# 53300 이므로 CSRF 오리진 검증을 위해 신뢰 오리진에 추가한다.
# CSRF_TRUSTED_ORIGINS env(콤마 구분)가 있으면 우선 사용하고, 없으면 SAAS_PUBLIC_URL 기반으로 구성한다.
_csrf_env = env('CSRF_TRUSTED_ORIGINS', '')
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [SAAS_PUBLIC_URL]
    if '127.0.0.1' in SAAS_PUBLIC_URL:
        CSRF_TRUSTED_ORIGINS.append('http://localhost:53300')

PLANS = {
    'free':  {'max_projects': 5,   'monthly_chat': 200,   'per_minute': 10, 'concurrent_jobs': 1},
    'pro':   {'max_projects': 5,   'monthly_chat': 5000,  'per_minute': 60, 'concurrent_jobs': 2},
    'admin': {'max_projects': None, 'monthly_chat': None, 'per_minute': 120, 'concurrent_jobs': 4},
}

# ── 로깅 (콘솔 + 파일) ───────────────────────────────────────
# 500 에러 등은 logs/django.log 에도 기록되어 상황 파악이 가능합니다.
# 2000줄 초과 시 django_YYYYMMDD_N.log 형식으로 일자/넘버링 백업 후 새 파일을 생성합니다.
# 백업 로그는 retention_days(기본 28일 = 4주)가 지나면 자동 삭제됩니다.
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_RETENTION_DAYS = int(env('LOG_RETENTION_DAYS', '28'))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {pathname}:{lineno} — {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {
            'class': 'core.logging.LineCountRotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'max_lines': 2000,
            'retention_days': LOG_RETENTION_DAYS,
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'django.request': {'handlers': ['console', 'file'], 'level': 'ERROR', 'propagate': False},
    },
}
