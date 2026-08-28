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
