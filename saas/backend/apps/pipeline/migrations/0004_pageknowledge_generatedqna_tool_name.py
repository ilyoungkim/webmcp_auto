# Tier 2 페이지 지식 모델 + Tier 1 도구명 필드 추가

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0003_sitecontent_failed_urls'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageKnowledge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=500)),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('markdown', models.TextField()),
                ('char_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_knowledge', to='projects.project')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.AddIndex(
            model_name='pageknowledge',
            index=models.Index(fields=['project', 'url'], name='pipeline_pa_project_ebd87a_idx'),
        ),
        migrations.AddField(
            model_name='generatedqna',
            name='tool_name',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
