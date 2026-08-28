from django.db import models


class DomainType(models.Model):
    code = models.CharField(max_length=32, unique=True)   # hospital | company | law
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True, default='')
    icon = models.CharField(max_length=8, default='🏢')
    category = models.CharField(max_length=32, blank=True, default='')  # 상위 카테고리 (hospital|law|edu|company|etc)
    sort_order = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class QuickMenu(models.Model):
    domain_type = models.ForeignKey(DomainType, on_delete=models.CASCADE, related_name='menus')
    label = models.CharField(max_length=64)
    question = models.CharField(max_length=255)
    prompt_hint = models.CharField(max_length=255, blank=True, default='')
    sort_order = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.domain_type.code}/{self.label}'
