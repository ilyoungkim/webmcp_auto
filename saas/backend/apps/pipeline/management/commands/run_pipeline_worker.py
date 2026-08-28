"""pipeline_jobs 폴링 워커 — Celery 없이 재시작 내성 확보."""
import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.pipeline.models import PipelineJob
from apps.pipeline.runner import run_job


class Command(BaseCommand):
    help = 'pipeline_jobs 를 폴링해 실행합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=float, default=2.0)

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.SUCCESS('pipeline worker 시작'))
        while True:
            # 만료된 running 정리
            for job in PipelineJob.objects.filter(status='running'):
                if job.lock_expired():
                    job.status = 'failed'
                    job.last_error = 'lock expired'
                    job.save(update_fields=['status', 'last_error', 'updated_at'])
                    p = job.project
                    if p.status not in ('completed',):
                        p.status = 'failed'
                        p.error = '워커 잠금 만료'
                        p.save(update_fields=['status', 'error', 'updated_at'])

            with transaction.atomic():
                job = (
                    PipelineJob.objects.select_for_update()
                    .filter(status='queued')
                    .order_by('created_at')
                    .first()
                )
                if job is not None:
                    job.status = 'running'
                    job.locked_at = timezone.now()
                    job.save(update_fields=['status', 'locked_at', 'updated_at'])

            if job is None:
                time.sleep(interval)
                continue

            try:
                run_job(job)
            except Exception as e:  # noqa: BLE001 — 워커 생존 보장
                job.status = 'failed'
                job.last_error = str(e)[:2000]
                job.save(update_fields=['status', 'last_error', 'updated_at'])
                self.stderr.write(str(e))
