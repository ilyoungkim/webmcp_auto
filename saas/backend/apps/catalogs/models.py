from django.db import models


class DomainType(models.Model):
    # code + lang 조합이 유니크 — 같은 code라도 언어 사일로별로 별도 레코드
    code = models.CharField(max_length=32)   # hospital | company | law
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True, default='')
    icon = models.CharField(max_length=8, default='🏢')
    category = models.CharField(max_length=32, blank=True, default='')  # 상위 카테고리 (hospital|law|edu|company|etc)
    # 사일로 언어 태그 — 이 카탈로그가 어느 언어 사일로에 속하는지.
    # 언어별로 다른 카탈로그 소스를 사용해 서로 격리된다. (ko | en)
    lang = models.CharField(max_length=8, blank=True, default='ko', db_index=True)
    sort_order = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order']
        constraints = [
            models.UniqueConstraint(fields=['code', 'lang'], name='uniq_domaintype_code_lang'),
        ]

    def __str__(self):
        return f'{self.lang}/{self.name}'


class QuickMenu(models.Model):
    domain_type = models.ForeignKey(DomainType, on_delete=models.CASCADE, related_name='menus')
    label = models.CharField(max_length=64)
    question = models.CharField(max_length=255)
    prompt_hint = models.CharField(max_length=255, blank=True, default='')
    answer_md = models.TextField(blank=True, default='')  # 필수 메뉴의 공통 답변 (DB에서 관리)
    sort_order = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)  # 필수 메뉴 (AI비서란? 등) — 편집/삭제 불가

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.domain_type.lang}/{self.label}'
