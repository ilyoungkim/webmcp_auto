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


class GeneratedQnA(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='qna')
    menu_label = models.CharField(max_length=64)
    question = models.CharField(max_length=255)
    answer_md = models.TextField()
    model = models.CharField(max_length=64, blank=True, default='')
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
