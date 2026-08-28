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
    plan = models.CharField(max_length=16, default='free')  # free | pro | admin
    must_change_password = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
