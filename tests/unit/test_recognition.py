from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import numpy as np

from attendance_app.configuration.settings import AppConfig, EnrollmentConfig
from attendance_app.recognition.engine import FaceEngine, RecognitionError, verify_models
from attendance_app.recognition.camera import Camera


class RecognitionTests(unittest.TestCase):
    def engine_with_faces(self, faces, config=None):
        engine = FaceEngine.__new__(FaceEngine)
        engine.config = config or EnrollmentConfig()
        engine.detector = Mock()
        engine.detector.detect.return_value = (1, faces)
        engine.recognizer = Mock()
        engine.recognizer.alignCrop.return_value = np.zeros((112, 112, 3), np.uint8)
        engine.recognizer.feature.return_value = np.ones((1, 128), np.float32)
        return engine

    def test_no_face_and_multiple_never_extract(self):
        for faces, status in ((None, 'no_face'), (np.ones((2, 15), np.float32), 'multiple_faces')):
            engine = self.engine_with_faces(faces)
            self.assertEqual(engine.analyze(np.zeros((480, 640, 3), np.uint8), extract=True).status, status)
            engine.recognizer.feature.assert_not_called()

    def test_quality_alignment_and_valid_embedding(self):
        face = np.array([[80, 80, 200, 200, 120, 120, 220, 120, 170, 170, 130, 220, 210, 220, .99]], np.float32)
        frame = np.random.default_rng(12).integers(60, 180, (480, 640, 3), dtype=np.uint8)
        engine = self.engine_with_faces(face)
        result = engine.analyze(frame, extract=True)
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.embedding.shape, (128,))
        self.assertAlmostEqual(float(np.linalg.norm(result.embedding)), 1, places=6)  # float32 precision
        engine.recognizer.alignCrop.assert_called_once()
        for frame, status in ((np.full((480,640,3),128,np.uint8),'blurred'), (np.zeros((480,640,3),np.uint8),'lighting')):
            self.assertEqual(engine.analyze(frame, extract=True).status, status)
        face[0, 2] = 20
        self.assertEqual(engine.analyze(frame, extract=True).status, 'small_face')

    def test_camera_release_on_open_and_read_failure(self):
        capture = Mock()
        capture.isOpened.return_value = False
        with patch('attendance_app.recognition.camera.cv2.VideoCapture', return_value=capture):
            with self.assertRaises(RecognitionError):
                with Camera(): pass
        capture.release.assert_called_once()
        capture.reset_mock()
        capture.isOpened.return_value = True
        capture.read.return_value = (False, None)
        with patch('attendance_app.recognition.camera.cv2.VideoCapture', return_value=capture):
            with self.assertRaises(RecognitionError):
                with Camera() as camera: camera.read()
        capture.release.assert_called_once()

    def test_model_hash_failure(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(RecognitionError):
                verify_models(directory)

    def test_real_models_blank_input_dynamic_sizes_and_sface_mechanics(self):
        engine = FaceEngine(AppConfig().model_dir)
        for width, height in ((320,320),(640,480),(1280,480)):
            self.assertEqual(engine.analyze(np.zeros((height,width,3), np.uint8)).status, 'no_face')
        # Synthetic aligned pixels validate API mechanics, not face recognition accuracy.
        crop = np.random.default_rng(9).integers(0,255,(112,112,3), dtype=np.uint8)
        embedding = engine.recognizer.feature(crop)
        self.assertEqual(embedding.shape, (1,128))
        self.assertTrue(np.isfinite(embedding).all())
        self.assertAlmostEqual(engine.similarity(embedding,embedding), 1.0, places=5)
