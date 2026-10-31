"""Opt-in real webcam check. Uses an isolated temporary DB, never the real roster.

Run with --auto-capture to exercise real-camera enrollment programmatically.
Without that flag, the operator captures samples and saves manually.
No frames, screenshots, or embeddings are printed or retained after exit.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from time import monotonic

from PySide6.QtCore import QTimer

from attendance_app.bootstrap import create_application
from attendance_app.configuration.settings import AppConfig
from attendance_app.domain.people import PersonInput
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.ui.dialogs.enrollment import FaceCaptureDialog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auto-capture', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='SmartAttendance-live-') as directory:
        @dataclass(frozen=True)
        class TestConfig(AppConfig):
            @property
            def data_dir(self): return Path(directory)
        config = TestConfig()
        app, window = create_application([], config)
        window.show()
        window.navigate(2)
        page = window.people_page
        person = page.service.create(PersonInput('آزمایش', 'دوربین', 'LIVE-CHECK'))
        person, previous = page.enrollment_service.begin(person.id)
        dialog = FaceCaptureDialog(config.model_dir, page.enrollment_service, person, previous, parent=window)
        start, ticks, last_sample = monotonic(), [], [float('-inf')]
        timer = QTimer()
        timer.setInterval(100)

        def tick():
            ticks.append(monotonic())
            if monotonic() - start > 35:
                dialog.reject()
            elif args.auto_capture:
                if dialog.save_button.isEnabled():
                    dialog.save_button.click()
                elif dialog.capture_button.isEnabled() and monotonic()-last_sample[0] > 1:
                    last_sample[0] = monotonic()
                    dialog.capture_button.click()

        timer.timeout.connect(tick)
        timer.start()
        dialog.show()
        dialog.start_button.click()
        dialog.finished.connect(app.quit)
        app.exec()
        timer.stop()
        # Ensure no live camera thread can outlive the UI/temporary database.
        if dialog.worker is not None:
            raise RuntimeError('Camera thread did not finish')
        rows = page.enrollment_service.templates.list_for_person(person.id)
        reopened = Database(config.database_path)
        reopened.initialize()
        assert FaceTemplateRepository(reopened).list_for_person(person.id) == rows
        print(json.dumps({'accepted': bool(dialog.result()), 'saved_templates': len(rows),
                          'camera_worker_stopped': dialog.worker is None, 'gui_timer_ticks': len(ticks),
                          'max_gui_timer_gap_ms': max(((b-a)*1000 for a,b in zip(ticks,ticks[1:])), default=0),
                          'elapsed_seconds': monotonic()-start, 'status': dialog.status.text()}, ensure_ascii=True))
        window.close()
        app.processEvents()
        import logging
        logger = logging.getLogger('attendance_app')
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        return 0 if len(rows) == 3 else 1


if __name__ == '__main__':
    raise SystemExit(main())
