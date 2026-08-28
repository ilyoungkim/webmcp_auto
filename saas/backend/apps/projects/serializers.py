from rest_framework import serializers

from .models import Project, TenantOrigin


class OriginSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantOrigin
        fields = ['id', 'origin', 'enabled']


class ProjectListSerializer(serializers.ModelSerializer):
    domainTypeCode = serializers.CharField(source='domain_type.code', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'publicId', 'name', 'url', 'status', 'progress', 'domainTypeCode', 'theme', 'createdAt']
        read_only_fields = fields

    publicId = serializers.CharField(source='public_id')
    theme = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at')


class ProjectDetailSerializer(ProjectListSerializer):
    installSnippet = serializers.SerializerMethodField()
    sourceUrls = serializers.SerializerMethodField()
    failedUrls = serializers.SerializerMethodField()

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + ['installSnippet', 'errorMessage', 'sourceUrls', 'failedUrls']
        read_only_fields = fields

    errorMessage = serializers.CharField(source='error')

    def get_installSnippet(self, obj):
        base = self.context.get('public_url', '').rstrip('/')
        return f'<script src="{base}/embed/{obj.public_id}.js" async></script>'

    def get_sourceUrls(self, obj):
        content = obj.contents.first()
        if content and content.source_urls:
            # 신규: [{url, title}] / 구버전: [url] 문자열 모두 호환
            items = []
            for s in content.source_urls:
                if isinstance(s, dict):
                    items.append({'url': s.get('url', ''), 'title': s.get('title', '')})
                else:
                    items.append({'url': s, 'title': ''})
            return items
        return [{'url': obj.url, 'title': ''}] if obj.url else []

    def get_failedUrls(self, obj):
        content = obj.contents.first()
        if content and content.failed_urls:
            items = []
            for f in content.failed_urls:
                if isinstance(f, dict):
                    items.append({'url': f.get('url', ''), 'error': f.get('error', '')})
                else:
                    items.append({'url': f, 'error': ''})
            return items
        return []
