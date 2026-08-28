from rest_framework import serializers

from .models import DomainType, QuickMenu


class QuickMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickMenu
        fields = ['id', 'label', 'question', 'promptHint', 'sortOrder']
        read_only_fields = ['id']

    promptHint = serializers.CharField(source='prompt_hint')
    sortOrder = serializers.IntegerField(source='sort_order')


class DomainTypeSerializer(serializers.ModelSerializer):
    menus = QuickMenuSerializer(many=True, read_only=True)

    class Meta:
        model = DomainType
        fields = ['id', 'code', 'name', 'description', 'icon', 'category', 'menus']
