"""Read-only gallery matching and conservative consecutive-frame confirmation."""
from dataclasses import dataclass, replace
import numpy as np
from attendance_app.configuration.settings import RecognitionConfig
from attendance_app.domain.face_templates import decode_embedding
from attendance_app.recognition.engine import MODEL_ID, ALIGNMENT_ID, RecognitionError


@dataclass(frozen=True)
class RecognitionResult:
    bbox: tuple[float, float, float, float]
    state: str = 'unknown'
    person_id: int | None = None
    person_name: str | None = None
    similarity: float | None = None


class RecognitionEngine:
    def __init__(self, rows, config=None):
        self.config = config or RecognitionConfig()
        self.gallery = {}
        for row in rows:
            if row['model_id'] != MODEL_ID or row['alignment_id'] != ALIGNMENT_ID:
                raise RecognitionError('نسخه اطلاعات چهره سازگار نیست؛ چهره‌ها را دوباره ثبت کنید.')
            vector = np.asarray(decode_embedding(row['embedding'], row['dimensions'], row['dtype']), np.float32)
            identity = row['person_id']
            name = row['first_name'] + ' ' + row['last_name']
            self.gallery.setdefault(identity, (name, []))[1].append(vector / np.linalg.norm(vector))
        if not self.gallery:
            raise RecognitionError('هیچ چهره‌ای برای افراد فعال ثبت نشده است. ابتدا چهره یک فرد را ثبت کنید.')
        self.previous = []

    def match(self, embedding, bbox):
        result = RecognitionResult(tuple(float(v) for v in bbox))
        if embedding is None:
            return result
        vector = np.asarray(embedding, np.float32).reshape(-1)
        if vector.shape != (128,) or not np.isfinite(vector).all() or np.linalg.norm(vector) <= 0:
            raise RecognitionError('بردار چهره معتبر نیست.')
        vector = vector / np.linalg.norm(vector)
        scores = sorted(((max(float(np.dot(vector, sample)) for sample in samples), identity, name)
                         for identity, (name, samples) in self.gallery.items()), reverse=True)
        score, identity, name = scores[0]
        result = replace(result, similarity=score)
        if score < self.config.cosine_threshold or (len(scores) > 1 and score - scores[1][0] < self.config.ambiguity_margin):
            return result
        return replace(result, state='known', person_id=identity, person_name=name)

    def recognize(self, analyses):
        raw = [self.match(item.embedding, item.faces[0][:4]) for item in analyses]
        current, results = [], []
        for item in raw:
            # Only unambiguous one-to-one overlap with the immediately preceding frame.
            candidates = [old for old in self.previous if overlap(item.bbox, old[0].bbox) >= self.config.overlap_threshold]
            count = 1
            if len(candidates) == 1:
                old, previous_count = candidates[0]
                reverse_count = sum(overlap(other.bbox, old.bbox) >= self.config.overlap_threshold for other in raw)
                if reverse_count == 1 and item.person_id is not None and old.person_id == item.person_id:
                    count += previous_count
            current.append((item, min(count, self.config.consistent_frames)))
            if item.state == 'known' and count < self.config.consistent_frames:
                item = replace(item, state='unknown', person_id=None, person_name=None)
            results.append(item)
        self.previous = current
        return results


def overlap(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0]+a[2], b[0]+b[2]), min(a[1]+a[3], b[1]+b[3])
    intersection = max(0, right-x)*max(0, bottom-y)
    union = a[2]*a[3]+b[2]*b[3]-intersection
    return intersection/union if union > 0 else 0
