"""Isolated real-camera enrollment-to-recognition smoke check.
Run: .venv/Scripts/python.exe tests/manual/validate_live_recognition.py
Keep one person facing the camera. No raw images are retained. This checks
same-person matching only; unknown and mixed-person accuracy need operator tests.
Add --attendance to also check transactional attendance in the temporary DB.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from attendance_app.application.enrollment_service import EnrollmentService
from attendance_app.application.people_service import PeopleService
from attendance_app.application.attendance_service import AttendanceService
from attendance_app.application.attendance_recorder import AttendanceRecorder
from attendance_app.configuration.settings import AppConfig
from attendance_app.domain.people import PersonInput
from attendance_app.recognition.camera import Camera
from attendance_app.recognition.engine import FaceEngine, RecognitionError
from attendance_app.recognition.matching import RecognitionEngine
from attendance_app.storage.database import Database
from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
from attendance_app.storage.repositories.people import PeopleRepository
from attendance_app.storage.repositories.attendance import AttendanceRepository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attendance', action='store_true')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='recognition-check-') as directory:
        database = Database(Path(directory)/'test.db')
        database.initialize()
        templates = FaceTemplateRepository(database)
        people = PeopleService(PeopleRepository(database))
        person = people.create(PersonInput('آزمایش', 'دوربین', 'LIVE-RECOGNITION'))
        enrollment = EnrollmentService(people, templates)
        engine = FaceEngine(AppConfig().model_dir)
        counts, samples = Counter(), []
        start, last = monotonic(), float('-inf')
        recorder, notifications = None, []
        try:
            with Camera(0) as camera:
                while len(samples) < 3 and monotonic()-start < 15:
                    result = engine.analyze(camera.read(), extract=True)
                    if result.embedding is not None and monotonic()-last >= .5:
                        samples.append(result.embedding)
                        last = monotonic()
                if len(samples) != 3:
                    print(json.dumps({'enrolled':False, 'samples':len(samples)}))
                    return 2
                enrollment.save(person, samples)
                matcher = RecognitionEngine(templates.list_active())
                if args.attendance:
                    recorder = AttendanceRecorder(AttendanceService(AttendanceRepository(database)), notifications.append)
                start = monotonic()
                while monotonic()-start < 6:
                    frame = camera.read()
                    observed_at = datetime.now().astimezone()
                    results = matcher.recognize(engine.analyze_all(frame))
                    if recorder is not None:
                        recorder.submit(results, observed_at)
                    counts['frames'] += 1
                    if not results: counts['no_face'] += 1
                    for result in results:
                        counts[result.state] += 1
                        if result.state == 'known' and result.person_id != person.id:
                            raise AssertionError('Wrong identity')
            if recorder is not None:
                recorder.close()
                recorder = None
            with database.connect() as connection:
                attendance_count = connection.execute('SELECT count(*) FROM attendance').fetchone()[0]
            print(json.dumps(dict(counts, enrolled=True, camera_released=True,
                                  attendance_count=attendance_count, attendance_notifications=len(notifications))))
            return 0 if counts['known'] and (not args.attendance or attendance_count == 1) else 2
        except RecognitionError as error:
            print(json.dumps({'error':str(error)}, ensure_ascii=True))
            return 1
        finally:
            if recorder is not None:
                recorder.close()


if __name__ == '__main__':
    raise SystemExit(main())
