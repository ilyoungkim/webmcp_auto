import json

from django.db import models

from apps.projects.models import Project


class Widget(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='widgets')
    config_json = models.TextField()            # 공개 config
    system_prompt = models.TextField(default='')  # 서버 전용
    version = models.IntegerField(default=1)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def current(cls, project: Project) -> 'Widget | None':
        return cls.objects.filter(project=project, is_current=True).order_by('-version').first()

    def public_config(self) -> dict:
        return json.loads(self.config_json)
