# PageKnowledge.extra_md — 관리자 페이지별 추가 지식 필드

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0004_pageknowledge_generatedqna_tool_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageknowledge',
            name='extra_md',
            field=models.TextField(blank=True, default=''),
        ),
    ]
