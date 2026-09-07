"""기존 프로젝트의 위젯 config를 새 generator 구조로 재생성한다.

배경: 위젯 config는 생성 시점의 스냅샷이라, generator 코드가 바뀌어도
기존 프로젝트는 재생성 전까지 구버전 구조(pageAnswerEndpoint/pages/새 names 없음)를 유지한다.
이 명령은 Q&A 재생성(LLM 호출) 없이 config만 새 구조로 갱신한다.

사용:
    python manage.py rebuild_widgets            # 전체 프로젝트
    python manage.py rebuild_widgets --lang ko  # 특정 사일로만
    python manage.py rebuild_widgets --project 3  # 특정 프로젝트만
    python manage.py rebuild_widgets --with-pages  # PageKnowledge도 함께 복원 후 재생성
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '기존 프로젝트의 위젯 config를 새 구조로 재생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--lang', type=str, default='', help='ko|en — 해당 사일로만 처리')
        parser.add_argument('--project', type=int, default=0, help='특정 프로젝트 id만 처리')
        parser.add_argument(
            '--with-pages', action='store_true',
            help='SiteContent.markdown에서 PageKnowledge를 복원한 뒤 위젯을 재생성한다.',
        )

    def handle(self, *args, **options):
        from apps.catalogs.models import QuickMenu
        from apps.pipeline.models import PageKnowledge, SiteContent
        from apps.pipeline.runner import _save_page_knowledge
        from apps.projects.models import Project
        from apps.widgets.generator import build_widget

        qs = Project.objects.all().order_by('id')
        if options['project']:
            qs = qs.filter(pk=options['project'])
        if options['lang']:
            qs = qs.filter(lang=options['lang'])
        with_pages = options['with_pages']

        ok, skipped = 0, 0
        for p in qs:
            sc = SiteContent.objects.filter(project=p).first()
            if not sc or not sc.markdown:
                self.stdout.write(f'skip {p.id} {p.name}: 콘텐츠 없음')
                skipped += 1
                continue
            menus = list(QuickMenu.objects.filter(domain_type=p.domain_type, enabled=True))
            if not menus:
                self.stdout.write(f'skip {p.id} {p.name}: 메뉴 없음')
                skipped += 1
                continue
            if with_pages:
                PageKnowledge.objects.filter(project=p).delete()
                _save_page_knowledge(p, sc.markdown, {})
            build_widget(p, menus, sc.markdown)
            pages = PageKnowledge.objects.filter(project=p).count()
            self.stdout.write(
                self.style.SUCCESS(f'rebuilt {p.id} {p.name} (pages={pages})')
            )
            ok += 1
        self.stdout.write(self.style.SUCCESS(f'완료: {ok}건 재생성, {skipped}건 건너뜀'))
