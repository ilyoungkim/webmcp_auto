from django.conf import settings
from django.db import models

from apps.projects.models import Project


class SiteContent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='contents')
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=255, blank=True, default='')
    markdown = models.TextField()
    char_count = models.IntegerField(default=0)
    source_urls = models.JSONField(default=list, blank=True)  # 크롤링된 실제 소스 URL 목록
    failed_urls = models.JSONField(default=list, blank=True)  # 재시도 후에도 실패한 URL + 오류 목록
    crawled_at = models.DateTimeField(auto_now_add=True)


class PageKnowledge(models.Model):
    """Tier 2 지식 — 크롤링된 개별 페이지 단위의 원문 마크다운.

    get_page_answer(page, question) 도구가 이 테이블을 조회해
    해당 페이지 내용만을 컨텍스트로 답변을 생성한다.
    (전체 사이트 요약이 아닌 페이지 단위 검색 자료로 사용)
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='page_knowledge')
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=255, blank=True, default='')
    markdown = models.TextField()
    char_count = models.IntegerField(default=0)
    # 관리자 입력 추가 지식 — 크롤된 페이지 원문에 이어 컨텍스트로 주입된다.
    # (사이트에 없거나 크롤이 놓친 정보: 최신 이벤트·가격 개편·예약 규정 등)
    extra_md = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['project', 'url'])]

    def __str__(self):
        return f'{self.project_id}:{self.title or self.url}'

    def knowledge_text(self) -> str:
        """답변 생성용 본문 = 크롤 원문 + (있으면) 관리자 추가 지식."""
        if not (self.extra_md or '').strip():
            return self.markdown
        return (
            f'{self.markdown}\n\n'
            '## [관리자 제공 추가 정보]\n'
            '(크롤링 이후 사이트 운영자가 직접 입력한 최신 정보로, 페이지 원문보다 우선한다)\n\n'
            f'{self.extra_md.strip()}'
        )


class GeneratedQnA(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='qna')
    menu_label = models.CharField(max_length=64)
    question = models.CharField(max_length=255)
    answer_md = models.TextField()
    model = models.CharField(max_length=64, blank=True, default='')
    # Tier 1 WebMCP 도구명 (core.tooltypes.tool_for_menu 로 결정). 비면 JS 폴백 명명.
    tool_name = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']


class PipelineJob(models.Model):
    STATUS = [('queued', 'queued'), ('running', 'running'), ('completed', 'completed'), ('failed', 'failed')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='jobs')
    status = models.CharField(max_length=16, choices=STATUS, default='queued')
    attempt = models.IntegerField(default=0)
    locked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    selected_urls = models.JSONField(default=list, blank=True)  # 사용자가 선택한 크롤링 대상 URL 목록
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def lock_expired(self) -> bool:
        if self.status != 'running' or self.locked_at is None:
            return False
        from django.utils import timezone
        return (timezone.now() - self.locked_at).total_seconds() > settings.JOB_LOCK_MINUTES * 60
