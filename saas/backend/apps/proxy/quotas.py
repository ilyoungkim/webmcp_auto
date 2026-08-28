"""쿼터 — 플랜별 분당/월간 한도."""
from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from .models import UsageEvent


def per_minute_ok(user, project=None) -> bool:
    plan = settings.PLANS.get(getattr(user, 'plan', 'free') or 'free', settings.PLANS['free'])
    limit = plan['per_minute']
    if limit is None:
        return True
    since = timezone.now() - timezone.timedelta(seconds=60)
    qs = UsageEvent.objects.filter(kind='chat', created_at__gte=since)
    if user and user.pk:
        qs = qs.filter(user=user)
    return qs.count() < limit


def monthly_ok(user) -> bool:
    plan = settings.PLANS.get(getattr(user, 'plan', 'free') or 'free', settings.PLANS['free'])
    limit = plan['monthly_chat']
    if limit is None:
        return True
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = UsageEvent.objects.filter(kind='chat', user=user, created_at__gte=month_start).count()
    return used < limit


def record(user, project, kind: str, units: int = 1) -> None:
    UsageEvent.objects.create(user=user, project=project, kind=kind, units=units)
