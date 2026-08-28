"""비밀번호 초기화 커맨드.

사용법:
    python manage.py reset_password <email> <new_password> [--no-force-change]

- 지정한 이메일의 사용자 비밀번호를 초기화한다.
- 기본적으로 must_change_password=True 로 설정해 다음 로그인 시 비밀번호 변경을
  강제한다. --no-force-change 를 주면 강제 변경 없이 바로 로그인 가능하다.
- 사용자가 없으면 오류로 종료한다.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = '지정한 이메일 사용자의 비밀번호를 초기화합니다.'

    def add_arguments(self, parser):
        parser.add_argument('email', help='초기화할 사용자 이메일')
        parser.add_argument('password', help='새 비밀번호')
        parser.add_argument(
            '--no-force-change',
            action='store_true',
            help='다음 로그인 시 비밀번호 변경을 강제하지 않음',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password']
        force_change = not options['no_force_change']

        if not email or not password:
            raise CommandError('email 과 password 를 모두 입력하세요.')

        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is None:
            raise CommandError(f'사용자를 찾을 수 없습니다: {email}')

        user.set_password(password)
        user.must_change_password = force_change
        user.save(update_fields=['password', 'must_change_password'])

        self.stdout.write(self.style.SUCCESS(
            f'비밀번호 초기화 완료: {email} '
            f'(강제변경={"예" if force_change else "아니오"})'
        ))