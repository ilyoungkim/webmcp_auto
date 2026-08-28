from django.conf import settings
from django.db import models


class UsageEvent(models.Model):
    KIND = [('chat', 'chat'), ('crawl', 'crawl'), ('preview', 'preview'), ('download', 'download')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey('projects.Project', null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=16, choices=KIND)
    units = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class RequestLog(models.Model):
    ts = models.DateTimeField(auto_now_add=True)
    origin = models.CharField(max_length=255, blank=True, default='')
    public_id = models.CharField(max_length=32, blank=True, default='')
    ip = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True, default='')
    verdict = models.CharField(max_length=16)  # ok | blocked_401 | blocked_403 | blocked_429
    reason = models.CharField(max_length=255, blank=True, default='')


class ChatErrorReport(models.Model):
    """위젯 챗 오류 신고. 사용자가 '오류 신고하기'를 누르면 저장된다."""

    STATUS = [('new', 'new'), ('read', 'read'), ('resolved', 'resolved')]

    project = models.ForeignKey('projects.Project', null=True, blank=True, on_delete=models.SET_NULL)
    public_id = models.CharField(max_length=32, blank=True, default='')
    origin = models.CharField(max_length=255, blank=True, default='')
    question = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    error_detail = models.TextField(blank=True, default='')
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default='')
    status = models.CharField(max_length=16, choices=STATUS, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.status}] {self.public_id} {self.error_message[:50]}'
