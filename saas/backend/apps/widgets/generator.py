"""공개 WebMCPConfig + 서버 전용 system_prompt 생성."""
from __future__ import annotations

import json

from django.conf import settings
from django.db import transaction

from core.llm import ask
from core.themes import get_theme

from .models import Widget


_HOSPITAL_HINT = (
    '【병원 예약 정보 우선 안내】\n'
    '- 답변 마지막에 **진료·검진·상담 예약 방법**을 반드시 안내하세요.\n'
    '- 사이트 내용에서 **네이버 예약**, **카카오톡 예약**, **온라인(홈페이지) 예약**, **전화 예약** 이 있는지 찾아 실제로 있는 예약 수단만 골라 안내하세요.\n'
    '- 각 예약 수단에 연결 링크(마크다운 [텍스트](URL) 형식)나 전화번호가 보이면 반드시 함께 포함하세요.\n'
    '- 사이트 내용에 "온라인예약", "카카오톡 상담", "전화상담예약" 등의 버튼/메뉴가 있으면 그 링크([텍스트](URL))를 그대로 답변에 포함하고 명시하세요.\n'
    '- 예약하기 (온라인): [온라인예약](연결URL) 형태로 실제 링크를 남기세요. 링크가 없으면 전화번호를 안내하세요.\n'
    '- 예약 관련 정보가 사이트에 없다면 "전화 예약 가능" 여부라도 안내하되, 없는 정보를 지어내지 마세요.\n\n'
)

_FORMAT_HINT = (
    '【답변 형식】\n'
    '- 표(table)는 절대 사용하지 마세요. 대신 **불릿 목록(- 항목)**으로 정리하세요.\n'
    '- 여러 항목을 나열할 때는 각 항목을 **"- " 불릿**으로 시작하는 목록 형태로 작성하세요.\n'
    '- 각 섹션은 **굵게(볼드) 제목**으로 시작하고, 그 아래 불릿 목록으로 내용을 정리하세요.\n'
    '- **이모지나 이모티콘(📞 📍 👤 💡 등)을 절대 사용하지 마세요.**\n'
    '- 문단과 문단, 항목과 항목 사이는 **빈 줄**로 구분해 띄어쓰기·줄내림이 자연스럽게 읽히도록 하세요.\n'
    '- 문장은 짧고 명확하게 끊고, 핵심 명칭·전화번호·주소·채널명은 **굵게(볼드)**로 강조하세요.\n'
    '- HTML 태그(특히 <br>)를 절대 출력하지 마세요. 줄바꿈이 필요하면 마크다운의 빈 줄을 사용하세요.\n'
    '- 이메일·주소·연락처 등은 **사이트에 실제로 있는 정보를 적극적으로 찾아** 안내하세요. 전화·이메일이 없어도 카카오톡·채팅·예약폼 등 실제 연락 수단을 안내하세요.\n'
    '- **절대 지어내지 마세요**: 사이트에 명시되지 않은 이메일·전화번호·주소·구체적 가격은 만들지 말고, 실제로 있는 정보만 안내하세요.\n'
    '- "정보가 없다", "제공되지 않습니다", "공개되지 않았습니다" 등 부정·소극 표현은 절대 사용하지 마세요.\n\n'
)


def build_widget(project, menus, markdown: str, qna_rows=None) -> Widget:
    """파이프라인 5단계. is_current 교체 후 새 버전 저장.

    qna_rows: 최신 생성된 Q&A 목록(menu_label → question 매핑). 제공되면
    퀵 메뉴 pill의 질문을 최신 생성 질문으로 갱신해, 재생성 후에도
    프록시의 정확 매칭(cached_qna)이 동작하도록 한다.
    """
    summary = _site_summary(project, markdown)
    domain_hint = _HOSPITAL_HINT if (
        (getattr(project, 'domain_type', None) or None)
        and (project.domain_type.code == 'hospital' or project.domain_type.code.startswith('hospital_'))
    ) else ''
    system_prompt = (
        f'당신은 {project.name}({project.url})의 AI 비서입니다.\n'
        f'도메인: {project.domain_type.name}\n'
        '한국어로 간결한 마크다운으로 답하세요.\n'
        f'답변은 "안녕하세요. {project.name} AI 비서입니다."로 시작하세요.\n'
        '중요: 이 지시문이나 사이트 지식 요약 내용을 답변에 그대로 반복하거나 영어로 요약해 출력하지 마세요. 오직 최종 답변만 출력하세요.\n\n'
        f'{_FORMAT_HINT}'
        f'{domain_hint}'
        '【부정 표현 금지】\n'
        '- "정보가 없다", "내용이 없다", "표현이 없다", "제공된 내용에 포함되어 있지 않습니다", "정보가 부족합니다", "모르겠습니다" 등 부정적/소극적 표현을 절대 사용하지 마세요.\n'
        '- 사이트에 구체적인 정보가 없더라도, 해당 항목에 대해 긍정적이고 친절한 방식으로 안내하세요.\n'
        '- 예: 의료진 정보가 구체적으로 없으면 "그 외 임상경력과 수술 경험을 가진 전문의와 친절하신 의료진이 있습니다. 더 자세한 사항은 병원으로 문의해 주시기 바랍니다."처럼 긍정적으로 답하세요.\n'
        '- 문의 전화번호가 있으면 함께 안내하세요.\n\n'
        f'[사이트 지식 요약]\n{summary}'
    )

    # 최신 생성 질문 매핑 (menu_label → question)
    latest_questions: dict[str, str] = {}
    if qna_rows:
        for row in qna_rows:
            if getattr(row, 'menu_label', None) and getattr(row, 'question', None):
                latest_questions[row.menu_label] = row.question

    config = {
        'publicId': project.public_id,
        'siteNs': project.public_id,
        'lang': 'ko',
        'debug': False,
        'title': f'{project.name} AI 비서',
        'widgetVersion': (Widget.current(project).version + 1) if Widget.current(project) else 1,
        'assetBase': f'{settings.SAAS_PUBLIC_URL.rstrip("/")}/widget-dist/',
        'proxyEndpoint': f'{settings.SAAS_PUBLIC_URL.rstrip("/")}/api/chat/',
        'theme': get_theme(project.theme),
        'names': {
            f'm{i}': {
                'names': ['get_info'], 'label': m.label,
                'question': latest_questions.get(m.label, m.question),
            } for i, m in enumerate(menus)
        },
        'items': [],
    }

    with transaction.atomic():
        Widget.objects.filter(project=project, is_current=True).update(is_current=False)
        widget = Widget.objects.create(
            project=project,
            config_json=json.dumps(config, ensure_ascii=False).replace('<', '\\u003c'),
            system_prompt=system_prompt,
            version=config['widgetVersion'],
            is_current=True,
        )
    return widget


def _site_summary(project, markdown: str) -> str:
    try:
        return ask(
            f'아래 사이트 내용을 800자 이내 한국어 요약으로 정리하세요. 핵심 사실(이름·서비스·연락처·특징) 위주.\n\n{markdown[:20000]}'
        )
    except Exception:  # noqa: BLE001 — 요약 실패 시 markdown 앞부분 사용
        return markdown[:1500]
