"""Gemini 클라이언트 (동기 httpx). 기존 webmcp/backend/app.py call_gemini 계승."""
from __future__ import annotations

import re
import time

import httpx
from django.conf import settings


class GeminiError(RuntimeError):
    pass


_HANGUL = re.compile(r'[가-힯]')

# 반복(degenerate) 출력 감지: 12자 이상 구절이 4회 이상 연속 반복되면 반복으로 판단
_REPEAT_PATTERN = re.compile(r'(.{12,}?)\1{3,}', re.DOTALL)


def _is_repetitive(text: str) -> bool:
    """모델이 특정 구절을 무한 반복한 출력인지 감지한다."""
    if not text:
        return False
    # 전체가 짧으면 반복 판단 제외
    if len(text) < 200:
        return False
    return bool(_REPEAT_PATTERN.search(text))

# 지시문 echo에서 흔히 나타나는 영어 지시 줄 패턴
_INSTRUCTION_LINE = re.compile(
    r'^\W*(?:\*+\s*)*(?:'
    r'\*?[A-Z][A-Za-z ()/&-]+:\*?'
    r'|AI Assistant for'
    r'|Answer \*?only|Answer based'
    r'|Concern Reminder|Constraint Reminder'
    r'|Concise Markdown|Korean Markdown'
    r'|If information is missing'
    r'|\(Self-Correction\)|\(Note\)'
    r'|Role:|Source:|Missing info:|Format:|Task:|Input:|Output:'
    r'|Greeting:|Introduction:|Key Features:|Contact Info:|Closing:|Capabilities:|Capability:'
    r')'
)


def _hangul_count(text: str) -> int:
    return len(_HANGUL.findall(text))


def _trim_to_body(text: str) -> str:
    """줄 단위로 앞쪽 지시 블록을 건너뛰고 첫 실질 한국어 줄부터 반환.

    - 마크다운 헤더(#)는 즉시 본문 시작으로 간주.
    - 일반 줄은 한글이 10자 이상이고 지시 줄 패턴이 아니어야 본문 시작.
    - 영어 비중이 높은 줄(한글 < 해당 줄 문자의 30%)은 시작 후에도 앞부분에서는 제외 안 함(본문 보존).
    """
    lines = text.split('\n')
    start_idx: int | None = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        if s.startswith('#'):
            start_idx = i
            break
        if _INSTRUCTION_LINE.match(s):
            continue
        hangul = _hangul_count(s)
        if hangul >= 10 and hangul * 3 >= len(s):
            start_idx = i
            break
    if start_idx is None:
        return ''
    return '\n'.join(lines[start_idx:]).strip()


def strip_instruction_echo(text: str) -> str:
    """모델(gemma)이 지시문/계획을 echo 또는 thinking으로 앞에 붙이는 경우 제거.

    전략:
    - '안녕하세요'가 2회 이상 등장 = 앞쪽은 thinking/init-draft → 마지막 구간이 최종 답변.
    - 1회 등장 = 그 위치부터 잘라내되 인사 직후 영어 지시 줄들을 건너뜀.
    - 미등장 = 줄 스캔으로 첫 실질 한국어 줄/헤더부터.
    - 안전장치: 결과 한글이 너무 적으면 '' 반환(호출부에서 원문 사용).
    """
    if not text:
        return text
    first = text.find('안녕하세요')
    last = text.rfind('안녕하세요')
    if last > first >= 0:
        body = text[last:]
    else:
        body = _trim_to_body(text[first:] if first >= 0 else text)
    if _hangul_count(body) < 20:
        return ''
    return body.strip()


def ask(prompt: str, *, temperature: float = 0.2, retries: int = 1, timeout: float = 60.0,
        max_tokens: int = 1024) -> str:
    """단일 프롬프트 → 텍스트 응답 (Gemini).

    max_tokens: 생성 토큰 상한. 응답이 길어질수록 지연이 커지므로
    채팅 등 실시간 응답은 적당한 상한(기본 1024)으로 제한해 속도를 확보한다.
    429(분당 요청 한도)는 백오프를 늘려가며 최대 4회 재시도한다.
    """
    url = f'{settings.GEMINI_BASE}/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}'
    payload = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperature, 'topK': 3, 'maxOutputTokens': max_tokens},
    }
    last_err: Exception | None = None
    # 429(rate limit)는 더 길게 백오프하며 재시도
    max_attempts = max(retries + 1, 4)
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 429:
                # 분당 한도 초과 — 백오프 후 재시도
                last_err = GeminiError(f'Gemini 429: {resp.text[:200]}')
                if attempt < max_attempts - 1:
                    time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code != 200:
                raise GeminiError(f'Gemini {resp.status_code}: {resp.text[:300]}')
            data = resp.json()
            parts = data['candidates'][0]['content']['parts']
            text = ''.join(p.get('text', '') for p in parts).strip()
            if not text:
                raise GeminiError('빈 응답')
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise GeminiError(str(last_err))


def ask_openrouter(prompt: str, *, temperature: float = 0.2, retries: int = 1,
                   timeout: float = 90.0, max_tokens: int = 16384,
                   model: str | None = None) -> str:
    """단일 프롬프트 → 텍스트 응답 (OpenRouter, OpenAI 호환 API).

    위젯 생성(Q&A) 및 빠른메뉴 질문 편집에 사용된다.
    Gemini 대비 더 긴 답변을 위해 max_tokens 기본값을 16384로 설정.

    모델 폴백: 주 모델(OPENROUTER_MODEL)이 실패하면
    폴백 모델(OPENROUTER_FALLBACK_MODEL)로 자동 전환해 재시도한다.
    """
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        raise GeminiError('OPENROUTER_API_KEY가 설정되지 않았습니다.')
    primary_model = model or getattr(settings, 'OPENROUTER_MODEL', 'mistralai/mistral-nemo')
    fallback_model = getattr(settings, 'OPENROUTER_FALLBACK_MODEL', '~deepseek/deepseek-v4-flash-latest')
    base = getattr(settings, 'OPENROUTER_BASE', 'https://openrouter.ai/api/v1')

    # 주 모델 → 실패 시 폴백 모델 순서로 시도
    models_to_try = [primary_model]
    if fallback_model and fallback_model != primary_model:
        models_to_try.append(fallback_model)

    last_err: Exception | None = None
    for model in models_to_try:
        try:
            return _openrouter_call(
                api_key, base, model, prompt, temperature=temperature,
                retries=retries, timeout=timeout, max_tokens=max_tokens,
            )
        except GeminiError as e:
            last_err = e
            # 폴백 모델이 남아있으면 다음 모델로 전환
            continue
    raise GeminiError(str(last_err))


def _openrouter_call(api_key: str, base: str, model: str, prompt: str, *,
                     temperature: float, retries: int, timeout: float,
                     max_tokens: int) -> str:
    """단일 모델로 OpenRouter 호출 (재시도 포함)."""
    url = f'{base}/chat/completions'
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    last_err: Exception | None = None
    max_attempts = max(retries + 1, 4)
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 429:
                last_err = GeminiError(f'OpenRouter 429: {resp.text[:200]}')
                if attempt < max_attempts - 1:
                    time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code != 200:
                raise GeminiError(f'OpenRouter {resp.status_code}: {resp.text[:300]}')
            data = resp.json()
            msg = data['choices'][0]['message']
            text = (msg.get('content') or '').strip()
            if not text:
                # reasoning 모델 등 content가 비어있으면 reasoning 텍스트 활용
                text = (msg.get('reasoning') or '').strip()
            if not text:
                raise GeminiError('빈 응답')
            # 반복(degenerate) 출력 감지 — 재시도로 정상 출력 확보
            if _is_repetitive(text):
                last_err = GeminiError('반복 출력 감지, 재시도')
                if attempt < max_attempts - 1:
                    time.sleep(2 * (attempt + 1))
                continue
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise GeminiError(str(last_err))
