import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '.env의 ADMIN_SEED_* 로 관리자 계정을 시드합니다.'

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.environ.get('ADMIN_SEED_EMAIL', 'admin@local')
        password = os.environ.get('ADMIN_SEED_PASSWORD', '')
        if not password:
            self.stderr.write(self.style.ERROR('ADMIN_SEED_PASSWORD 가 비어 있습니다. .env 를 채우세요.'))
            raise SystemExit(1)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'name': '관리자',
                'role': 'admin',
                'plan': 'admin',
                'must_change_password': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        user.set_password(password)
        user.role = 'admin'
        user.plan = 'admin'
        user.must_change_password = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'{"생성" if created else "갱신"}: {email}'))
