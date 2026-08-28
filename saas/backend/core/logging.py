"""라인 수 기반 및 날짜/넘버링 백업 로그 핸들러."""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path


class LineCountRotatingFileHandler(logging.FileHandler):
    """지정된 최대 라인 수(max_lines)를 초과하면 새 파일을 열고

    기존 파일은 django_YYYYMMDD_N.log (날짜 및 넘버링) 형식으로 백업합니다.
    """

    def __init__(
        self,
        filename: str | Path,
        max_lines: int = 2000,
        encoding: str = 'utf-8',
        delay: bool = False,
    ) -> None:
        self.max_lines = max_lines
        self._current_lines = 0
        self.base_filename = os.path.abspath(str(filename))
        Path(self.base_filename).parent.mkdir(parents=True, exist_ok=True)
        self._init_line_count()
        super().__init__(self.base_filename, mode='a', encoding=encoding, delay=delay)

    def _init_line_count(self) -> None:
        """기존 파일이 존재하면 라인 수를 카운트."""
        if os.path.exists(self.base_filename):
            try:
                with open(self.base_filename, 'rb') as f:
                    self._current_lines = sum(1 for _ in f)
            except Exception:
                self._current_lines = 0
        else:
            self._current_lines = 0

    def should_rollover(self, record: logging.LogRecord) -> bool:
        """메시지에 포함된 줄바꿈을 고려하여 라인 수 초과 여부 확인."""
        msg = self.format(record)
        lines_in_msg = msg.count('\n') + 1
        return (self._current_lines + lines_in_msg) > self.max_lines

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self.should_rollover(record):
                self.do_rollover()
            super().emit(record)
            msg = self.format(record)
            self._current_lines += msg.count('\n') + 1
        except Exception:
            self.handleError(record)

    def do_rollover(self) -> None:
        """현재 로그 파일을 닫고 django_YYYYMMDD_N.log 형태로 백업한 뒤 새 파일 생성."""
        if self.stream:
            self.stream.close()
            self.stream = None

        if os.path.exists(self.base_filename):
            today_str = datetime.now().strftime('%Y%m%d')
            dir_path = Path(self.base_filename).parent
            stem = Path(self.base_filename).stem  # e.g. django
            ext = Path(self.base_filename).suffix  # e.g. .log

            # 넘버링 탐색 (1부터 시작)
            seq = 1
            while True:
                backup_name = dir_path / f'{stem}_{today_str}_{seq}{ext}'
                if not backup_name.exists():
                    break
                seq += 1

            shutil.move(self.base_filename, backup_name)

        self._current_lines = 0
        if not self.delay:
            self.stream = self._open()
