import unittest
from unittest.mock import Mock
import numpy as np
from attendance_app.domain.errors import AppError
from attendance_app.domain.face_templates import encode_embedding
from attendance_app.recognition.engine import MODEL_ID, ALIGNMENT_ID, Analysis, FaceEngine, RecognitionError
from attendance_app.recognition.matching import RecognitionEngine
from attendance_app.recognition.worker import RecognitionWorker
from attendance_app.configuration.settings import EnrollmentConfig


def row(identity=1, vector=None):
    return dict(person_id=identity, first_name='حسین', last_name='افشار',
                embedding=encode_embedding(np.eye(128)[0] if vector is None else vector),
                dimensions=128, dtype='<f4', model_id=MODEL_ID, alignment_id=ALIGNMENT_ID)


def analysis(vector, x=0):
    face = np.zeros((1,15), np.float32)
    face[0,:4] = [x,0,100,100]
    return Analysis(face, 'ready', '', 0, embedding=vector)


class MatchingTests(unittest.TestCase):
    def test_known_unknown_two_faces_and_order_changes(self):
        matcher = RecognitionEngine([row()])
        known, unknown = analysis(np.eye(128)[0]), analysis(np.eye(128)[1], 200)
        for _ in range(2):
            self.assertEqual([r.state for r in matcher.recognize([known,unknown])], ['unknown','unknown'])
        results = matcher.recognize([unknown,known])
        self.assertEqual([r.state for r in results], ['unknown','known'])
        self.assertIsNone(results[0].person_id)
        self.assertEqual(results[1].person_name, 'حسین افشار')
        self.assertEqual(results[1].person_id, 1)
        self.assertEqual(results[1].bbox, (0,0,100,100))

    def test_no_face_rejection_and_identity_change_reset_confirmation(self):
        matcher = RecognitionEngine([row(),row(2,np.eye(128)[1])])
        a, b = analysis(np.eye(128)[0]), analysis(np.eye(128)[1])
        matcher.recognize([a]); matcher.recognize([a])
        self.assertEqual(matcher.recognize([]), [])
        self.assertEqual(matcher.recognize([a])[0].state, 'unknown')
        matcher.recognize([a])
        self.assertEqual(matcher.recognize([a])[0].state, 'known')
        self.assertEqual(matcher.recognize([b])[0].state, 'unknown')
        self.assertEqual(matcher.recognize([analysis(None)])[0].state, 'unknown')

    def test_weak_ambiguous_empty_incompatible_and_invalid(self):
        matcher = RecognitionEngine([row()])
        weak = np.eye(128)[0]*.49 + np.eye(128)[1]*np.sqrt(1-.49**2)
        self.assertEqual(matcher.match(weak,(0,0,100,100)).state, 'unknown')
        self.assertEqual(RecognitionEngine([row(),row(2)]).match(np.eye(128)[0],(0,0,100,100)).state,'unknown')
        for rows in ([], [dict(row(),model_id='old')], [dict(row(),embedding=b'bad')]):
            with self.assertRaises(AppError): RecognitionEngine(rows)
        with self.assertRaises(RecognitionError): matcher.match(np.full(128,np.nan),(0,0,1,1))

    def test_all_faces_extract_independently_with_shared_quality_checks(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine.config = EnrollmentConfig()
        faces = np.zeros((2,15),np.float32)
        faces[:,:4] = [[10,10,100,100],[150,10,100,100]]
        engine.detector = Mock()
        engine.detector.detect.return_value = (1,faces)
        engine.recognizer = Mock()
        engine.recognizer.feature.side_effect = [np.eye(128)[0],np.eye(128)[1]]
        frame = np.random.default_rng(3).integers(60,180,(240,320,3),dtype=np.uint8)
        results = engine.analyze_all(frame)
        self.assertEqual(len(results),2)
        self.assertEqual(engine.recognizer.feature.call_count,2)
        self.assertEqual(engine.detector.detect.call_count,1)
        self.assertEqual(RecognitionEngine([row()]).recognize(results)[1].state,'unknown')
        engine.detector.detect.return_value = (1,None)
        self.assertEqual(engine.analyze_all(frame),[])

    def test_worker_failures_release_and_clear_results(self):
        repository = Mock()
        repository.list_active.return_value = [row()]
        camera = Mock()
        camera.__enter__ = Mock(return_value=camera)
        camera.__exit__ = Mock(return_value=False)
        camera.read.side_effect = RecognitionError('دریافت تصویر متوقف شد')
        factory = Mock(return_value=camera)
        worker = RecognitionWorker('.',repository,engine_factory=Mock(),camera_factory=factory)
        failures = []
        worker.failed.connect(failures.append)
        worker.run()
        self.assertEqual(len(failures),1)
        camera.__exit__.assert_called_once()
        self.assertIsNone(worker.take_latest())
        repository.list_active.return_value = []
        factory.reset_mock()
        worker.run()
        factory.assert_not_called()
        self.assertIn('ثبت نشده',failures[-1])

    def test_gallery_reuses_saved_templates_and_excludes_archived_people(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from attendance_app.storage.database import Database
        from attendance_app.storage.repositories.people import PeopleRepository
        from attendance_app.storage.repositories.face_templates import FaceTemplateRepository
        from attendance_app.application.people_service import PeopleService
        from attendance_app.application.enrollment_service import EnrollmentService
        from attendance_app.domain.people import PersonInput
        with TemporaryDirectory() as directory:
            database = Database(Path(directory)/'test.db')
            database.initialize()
            people = PeopleService(PeopleRepository(database))
            templates = FaceTemplateRepository(database)
            person = people.create(PersonInput('حسین','افشار','0001'))
            EnrollmentService(people,templates).save(person,[np.eye(128)[0]]*3)
            rows = templates.list_active()
            self.assertEqual(len(rows),3)
            self.assertEqual(RecognitionEngine(rows).match(np.eye(128)[0],(0,0,100,100)).person_id,person.id)
            people.archive(person.id)
            self.assertEqual(templates.list_active(),[])
            self.assertEqual(len(templates.list_for_person(person.id)),3)
