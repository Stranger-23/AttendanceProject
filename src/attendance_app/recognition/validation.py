"""Isolated, non-persisting validation: python -m attendance_app.recognition.validation."""
import argparse
from collections import Counter
import json
from time import perf_counter

import numpy as np

from attendance_app.configuration.settings import AppConfig
from attendance_app.recognition.camera import Camera
from attendance_app.recognition.engine import FaceEngine, RecognitionError, verify_models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--models-only', action='store_true')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    config = AppConfig()
    if args.preview:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from attendance_app.ui.styles.theme import apply_theme
        from attendance_app.ui.dialogs.enrollment import FaceCaptureDialog
        app = QApplication([])
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        apply_theme(app, config.font_dir)
        dialog = FaceCaptureDialog(config.model_dir, camera_index=args.camera)
        return dialog.exec()
    try:
        verify_models(config.model_dir)
        engine = FaceEngine(config.model_dir)
        blank = engine.analyze(np.zeros((480, 640, 3), np.uint8))
        report = {'models_verified': True, 'models_loaded': True, 'blank_status': blank.status}
        if args.models_only:
            print(json.dumps(report))
            return 0
        counts, times, features = Counter(), [], []
        detection_times, embedding_times = [], []
        start = perf_counter()
        paired_count = None
        with Camera(args.camera) as camera:
            while perf_counter() - start < max(1, args.seconds):
                before = perf_counter()
                frame = camera.read()
                result = engine.analyze(frame, extract=len(features) < 2)
                counts[result.status] += 1
                times.append((perf_counter() - before)*1000)
                detection_times.append(result.detection_ms)
                if result.embedding is not None:
                    embedding_times.append(result.embedding_ms)
                if len(result.faces) == 1 and paired_count is None:
                    paired_count = len(engine.analyze(np.concatenate((frame, frame), axis=1)).faces)
                if result.embedding is not None and len(features) < 2:
                    features.append(result.embedding)
        elapsed = perf_counter() - start
        report.update(frames=len(times), elapsed_seconds=elapsed, fps=len(times)/elapsed,
                      capture_processing_median_ms=float(np.median(times)) if times else None,
                      capture_processing_p95_ms=float(np.percentile(times,95)) if times else None,
                      detection_median_ms=float(np.median(detection_times)) if detection_times else None,
                      embedding_median_ms=float(np.median(embedding_times)) if embedding_times else None,
                      states=dict(counts), controlled_duplicate_frame_face_count=paired_count,
                      embeddings=len(features), cosine=engine.similarity(*features) if len(features)==2 else None,
                      camera_embedding_path_validated=bool(times and len(features)==2))
        print(json.dumps(report))
        return 0 if times and len(features)==2 else 2  # Observed frames alone do not validate embeddings.
    except RecognitionError as error:
        print(str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
