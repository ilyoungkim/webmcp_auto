from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """USERNAME_FIELD=email 에 맞춰 username 을 이메일에서 파생시키는 매니저."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True 여야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True 여야 합니다.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """email 로그인 + SaaS 플랜."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=64, blank=True, default='')
    role = models.CharField(max_length=16, default='user')  # user | admin
    # IP 화이트리스트 — 줄바꿈/콤마 구분. 비어 있으면 제한 없음(모든 IP 허용).
    # 단일 IP(203.0.113.10) 또는 CIDR(203.0.113.0/24) 지원.
    allowed_ips = models.TextField(blank=True, default='')
    plan = models.CharField(max_length=16, default='free')  # free | pro | admin
    must_change_password = models.BooleanField(default=False)

    # 프로필 — 연락처 (전화번호 2개)
    phone1 = models.CharField('대표 전화번호', max_length=32, blank=True, default='')
    phone2 = models.CharField('보조 전화번호', max_length=32, blank=True, default='')

    # 결제 정보 (테스트용 — PayPal/Stripe 연동 전 입력 보관소)
    billing_company = models.CharField('회사명', max_length=128, blank=True, default='')
    billing_contact = models.CharField('결제 담당자', max_length=64, blank=True, default='')
    billing_email = models.EmailField('결제 이메일', blank=True, default='')
    billing_address = models.TextField('결제 주소', blank=True, default='')
    billing_note = models.TextField('결제 비고', blank=True, default='')
    # 월 결제 금액 — 비어 있으면 사일로 기본가(ko: 50,000원, en: $49) 적용.
    # admin 이 엔터프라이즈 금액을 지정할 때 사용.
    monthly_price = models.DecimalField(
        '월 결제 금액', max_digits=12, decimal_places=2, null=True, blank=True,
        default=None,
    )
    monthly_currency = models.CharField('통화', max_length=3, blank=True, default='')  # KRW|USD|...

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
