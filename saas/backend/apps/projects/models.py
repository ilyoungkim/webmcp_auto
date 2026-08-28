import secrets

from django.conf import settings
from django.db import models

from apps.catalogs.models import DomainType


def gen_public_id() -> str:
    return secrets.token_urlsafe(9)  # 12자 수준 urlsafe


class Project(models.Model):
    STATUS_CHOICES = [
        ('queued', 'queued'), ('crawling', 'crawling'),
        ('generating', 'generating'), ('completed', 'completed'), ('failed', 'failed'),
    ]

    public_id = models.CharField(max_length=32, unique=True, default=gen_public_id)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=128)
    url = models.URLField(max_length=500)
    origin = models.CharField(max_length=255, blank=True, default='')
    domain_type = models.ForeignKey(DomainType, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='queued')
    status_message = models.CharField(max_length=255, blank=True, default='')
    progress = models.IntegerField(default=0)
    error = models.TextField(blank=True, default='')
    menus_edited = models.BooleanField(default=False)  # 빠른메뉴 질문 편집 1회 제한
    theme = models.CharField(max_length=32, blank=True, default='blue_sky')  # 위젯 테마 코드
    enabled = models.BooleanField(default=True)  # 사용중지 여부 (False = 위젯 서빙 중지)

    # ── 테넌트(프로젝트)별 Gemini 설정 ─────────────────────────
    # 비어 있으면 전역 settings(.env) 값을 사용한다. 관리자가 프로젝트별로
    # Gemini API 키/모델을 지정하면 해당 프로젝트의 Gemini 호출에 우선 적용된다.
    # (OpenRouter는 전역 .env 로만 관리한다.)
    gemini_api_key = models.CharField(max_length=512, blank=True, default='')
    gemini_model = models.CharField(max_length=128, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.public_id})'


class TenantOrigin(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='origins')
    origin = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.origin


class DownloadLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_type = models.CharField(max_length=16)  # config_js | bundle_zip
    downloaded_at = models.DateTimeField(auto_now_add=True)


class SupportTicket(models.Model):
    """고객센터 Q&A 게시판 — 사용자가 질문을 올리면 관리자가 답변한다."""
    STATUS_CHOICES = [
        ('pending', 'pending'),   # 답변 대기
        ('answered', 'answered'), # 답변 완료
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='support_tickets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    question = models.TextField()
    answer = models.TextField(blank=True, default='')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.project.name} / {self.question[:30]}'
