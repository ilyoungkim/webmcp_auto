"""기존 프로젝트의 Origin 화이트리스트를 http/https + www/비www 변형으로 보강한다.

배경: _register_origins()가 과거에는 www/비www 변형만 등록해, 사이트가
HTTP→HTTPS 로 전환되면 오리진이 달라져 위젯 채팅이 403(origin_not_allowed)으로
반복되던 문제가 있었다. 이 명령은 기존 프로젝트의 화이트리스트에 누락된
http/https 변형을 일괄 추가한다.

사용:
    python manage.py backfill_origins            # 전체 프로젝트
    python manage.py backfill_origins --lang ko  # 특정 사일로만
    python manage.py backfill_origins --project 4  # 특정 프로젝트만
"""
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand

from core.origins import normalize_origin


def _origin_variants(url: str) -> set:
    """URL 오리진의 http/https + www/비www 변형 집합."""
    base = normalize_origin(url)
    parts = urlsplit(base)
    host = parts.hostname or ''
    suffix = f':{parts.port}' if parts.port else ''

    hosts = {host}
    if host.startswith('www.'):
        hosts.add(host[4:])
    else:
        hosts.add(f'www.{host}')

    schemes = {parts.scheme}
    if not parts.port:
        schemes.add('https' if parts.scheme == 'http' else 'http')

    out = set()
    for s in schemes:
        for h in hosts:
            out.add(f'{s}://{h}{suffix}')
    return out


class Command(BaseCommand):
    help = '기존 프로젝트의 Origin 화이트리스트에 http/https 변형을 보강합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--lang', type=str, default='', help='ko|en — 해당 사일로만 처리')
        parser.add_argument('--project', type=int, default=0, help='특정 프로젝트 id만 처리')

    def handle(self, *args, **options):
        from apps.projects.models import Project, TenantOrigin

        qs = Project.objects.all().order_by('id')
        if options['project']:
            qs = qs.filter(pk=options['project'])
        if options['lang']:
            qs = qs.filter(lang=options['lang'])

        added_total = 0
        for p in qs:
            variants = _origin_variants(p.url)
            added = 0
            for org in variants:
                if not org:
                    continue
                _, created = TenantOrigin.objects.get_or_create(origin=org, defaults={'project': p})
                if created:
                    added += 1
            added_total += added
            self.stdout.write(f'{p.id} {p.name}: +{added} origins ({", ".join(sorted(variants))})')

        self.stdout.write(self.style.SUCCESS(f'완료 — 총 {added_total}개 origin 추가'))
