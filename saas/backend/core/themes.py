"""위젯 테마 정의.

각 테마는 위젯 config 의 `theme` 객체와 1:1 대응한다.
프로젝트 생성/수정 시 선택되며, 위젯 빌드 시 반영된다.
"""

# 기본 테마 (기존 기본값)
DEFAULT_THEME = {
    'primary': '#0e7490', 'primary2': '#06b6d4', 'bg': '#f0f9ff',
    'surface': '#ffffff', 'text': '#1f2937', 'textMuted': '#6b7280',
    'textFaint': '#9ca3af', 'border': '#e5e7eb', 'codeBg': '#f3f4f6',
    'pillBg': '#cffafe', 'errorBg': '#fef2f2', 'errorBorder': '#fca5a5',
    'errorText': '#b91c1c',
}

THEMES = {
    'blue_sky': {
        'label': 'Blue Sky',
        'theme': {
            'primary': '#0284c7', 'primary2': '#38bdf8', 'bg': '#f0f9ff',
            'surface': '#ffffff', 'text': '#0f172a', 'textMuted': '#64748b',
            'textFaint': '#94a3b8', 'border': '#e0f2fe', 'codeBg': '#f0f9ff',
            'pillBg': '#e0f2fe', 'errorBg': '#fef2f2', 'errorBorder': '#fca5a5',
            'errorText': '#b91c1c',
        },
    },
    'red_orange': {
        'label': 'Red Orange',
        'theme': {
            'primary': '#dc2626', 'primary2': '#f97316', 'bg': '#fff7ed',
            'surface': '#ffffff', 'text': '#1c1917', 'textMuted': '#78716c',
            'textFaint': '#a8a29e', 'border': '#ffedd5', 'codeBg': '#fff7ed',
            'pillBg': '#ffedd5', 'errorBg': '#fef2f2', 'errorBorder': '#fca5a5',
            'errorText': '#b91c1c',
        },
    },
    'white_snow': {
        'label': 'White Snow',
        'theme': {
            'primary': '#334155', 'primary2': '#64748b', 'bg': '#f8fafc',
            'surface': '#ffffff', 'text': '#0f172a', 'textMuted': '#64748b',
            'textFaint': '#94a3b8', 'border': '#e2e8f0', 'codeBg': '#f1f5f9',
            'pillBg': '#e2e8f0', 'errorBg': '#fef2f2', 'errorBorder': '#fca5a5',
            'errorText': '#b91c1c',
        },
    },
    'banana_pink': {
        'label': 'Banana Pink',
        'theme': {
            'primary': '#db2777', 'primary2': '#f9a8d4', 'bg': '#fdf2f8',
            'surface': '#ffffff', 'text': '#500724', 'textMuted': '#9d174d',
            'textFaint': '#f9a8d4', 'border': '#fce7f3', 'codeBg': '#fdf2f8',
            'pillBg': '#fce7f3', 'errorBg': '#fef2f2', 'errorBorder': '#fca5a5',
            'errorText': '#b91c1c',
        },
    },
    'black_neon': {
        'label': 'Black Neon',
        'theme': {
            'primary': '#22d3ee', 'primary2': '#a855f7', 'bg': '#0b0f19',
            'surface': '#111827', 'text': '#f9fafb', 'textMuted': '#9ca3af',
            'textFaint': '#6b7280', 'border': '#1f2937', 'codeBg': '#1f2937',
            'pillBg': '#164e63', 'errorBg': '#450a0a', 'errorBorder': '#ef4444',
            'errorText': '#fca5a5',
        },
    },
}

# 테마 코드 목록 (선택 UI용)
THEME_CODES = list(THEMES.keys())


def get_theme(theme_code: str | None) -> dict:
    """테마 코드 → theme dict. 없거나 알 수 없으면 기본 테마."""
    if not theme_code:
        return dict(DEFAULT_THEME)
    entry = THEMES.get(theme_code)
    if entry is None:
        return dict(DEFAULT_THEME)
    return dict(entry['theme'])
