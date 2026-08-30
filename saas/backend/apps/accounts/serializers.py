from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[UniqueValidator(User.objects.all())])
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')


class PasswordChangeSerializer(serializers.Serializer):
    current = serializers.CharField(write_only=True)
    new = serializers.CharField(min_length=8, write_only=True)

    def validate_current(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('현재 비밀번호가 다릅니다.')
        return value


class MeSerializer(serializers.ModelSerializer):
    mustChangePassword = serializers.BooleanField(source='must_change_password')

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'plan', 'mustChangePassword']


class ProfileSerializer(serializers.ModelSerializer):
    """프로필 페이지용 — 본인만 접근. 휴대폰 2개 + 결제 정보."""

    email = serializers.EmailField(read_only=True)  # 아이디(로그인 ID)는 변경 불가 표시용
    monthlyPrice = serializers.DecimalField(
        source='monthly_price', max_digits=12, decimal_places=2,
        read_only=True, allow_null=True,
    )  # 본인 수정 불가 (admin 전용)
    monthlyCurrency = serializers.CharField(source='monthly_currency', read_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'name', 'role', 'plan',
            'phone1', 'phone2',
            'billing_company', 'billing_contact', 'billing_email',
            'billing_address', 'billing_note',
            'monthlyPrice', 'monthlyCurrency',
        ]
        read_only_fields = ['email', 'role', 'plan', 'monthlyPrice', 'monthlyCurrency']

    def update(self, instance, validated_data):
        # 이메일/역할/플랜/결제금액은 read_only 로 자동 제외됨
        return super().update(instance, validated_data)
