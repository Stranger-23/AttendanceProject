# Phase 4.1 — Recognition engine

Implemented 2026-10-24. No attendance records, schema changes, reports, history,
statistics, exports, or attendance de-duplication were added.

## Integration and changed files

- `recognition/engine.py`: shared single-face quality/embedding helper and a
  detect-once, multiple-face analysis path. Enrollment still rejects multiple faces.
- `recognition/matching.py`: immutable RecognitionResult, gallery matching and
  consecutive-frame confirmation, independent of Qt/camera/storage.
- `recognition/worker.py`: recognition thread with existing bounded mailbox,
  thread-owned database reads, camera lifetime, safe errors and stage logging.
- `configuration/settings.py`: RecognitionConfig defaults.
- `storage/repositories/face_templates.py`: read-only active-person gallery query.
- `ui/dialogs/recognition.py`, `ui/pages/recognition.py`, `ui/main_window.py`:
  attendance navigation opens a modal Persian camera preview with start/stop,
  retry, names, ناشناس labels and bounding boxes. Qt paints Persian text;
  camera pixels are not mirrored. The modal prevents roster/restore changes
  while its gallery snapshot is in use; restarting reloads it.
- `tests/unit/test_matching.py`, `tests/integration/test_shell.py`:
  matching, storage integration, worker failures and UI lifecycle checks.
- `tests/manual/validate_live_recognition.py`: temporary enrollment-to-recognition
  camera smoke check; no actual roster changes or retained images/templates.
- This validation document.

Paths above are relative to `src/attendance_app/` except tests and docs.

## Method and safety defaults

Reuse existing YuNet landmarks, SFace alignment/128-dimensional normalized
embeddings and SQLite face_templates. Embeddings retain the existing little-endian
float32 format and model/alignment IDs. Incompatible/corrupt galleries stop with a
Persian error; archived people are excluded. No second template store exists.

Compare cosine similarity against all samples, take the best sample per person,
and accept only at >= 0.50 with >= 0.08 separation from the next person.
Similarity is a score, not a calibrated probability. Quality gates reuse enrollment
(minimum size 80px, blur variance 60, brightness 40–215, detector score 0.9).

Require the same accepted identity in three consecutive analyzed frames using
unambiguous one-to-one bounding-box IoU >= 0.4 with the immediately previous frame.
Detector ordering may change. Lost/no-face/ambiguous/rejected faces reset agreement;
uncertain current frames immediately return unknown with no identity. No stale
known identity is carried through uncertainty. Crossing/overlapping faces reset
confirmation conservatively. This is small spatial association, not full tracking.

Results expose database person ID, full name, known/unknown state, cosine score
when available, and (x,y,width,height) in original image coordinates. Pending
confirmation is unknown. Worker.take_latest() returns the latest (frame, results)
packet; errors/stop clear it and the UI clears previous identities.

## Validation

Run from the project PowerShell using the existing virtual environment:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests/unit -v
.venv/Scripts/python.exe -m unittest discover -s tests/integration -v
.venv/Scripts/python.exe tests/manual/validate_live_recognition.py
```

All 35 unit tests and 5 integration tests passed.

Controlled inputs cover all six requested cases: correct enrolled identity,
unknown rejection, mixed known/unknown faces (including changed detector order),
no face, camera read/open failure and empty enrollment. Additional checks cover
weak/ambiguous matching, corrupt/incompatible templates, archive exclusion,
confirmation reset, multiple independent embeddings, preview Persian labels,
empty-gallery retry and safe close/release. Existing enrollment tests remain green.
These synthetic tests validate logic, not population-level biometric accuracy.

Real DirectShow camera 0/model probe: 94 frames, 94 detected faces, 10 quality-valid
embeddings over approximately 4 seconds; camera released safely.
Temporary real enrollment-to-recognition smoke: three stored samples, 181 recognition
frames over approximately 6 seconds, 89 known and 92 unknown face results; every
known result had the temporary enrolled identity. Camera released and temporary DB
removed. Unknown includes quality rejection and unconfirmed matches; this run does
not measure general recognition accuracy. OpenCV emitted the same nonfatal graph
engine target warnings seen in Phase 3.

## Manual acceptance completed

The user subsequently reported successful manual acceptance for all six cases:

1. Registered person alone — PASS.
2. Unknown person alone — PASS.
3. Registered and unknown people simultaneously — PASS.
4. No face visible — PASS.
5. Camera disconnected/unavailable — PASS.
6. No enrolled face/person — PASS; recognition is prevented with a clear message.

Phase 4.1 is accepted. Phase 4.2 preserves its matching logic, thresholds,
quality gates, and consecutive-frame confirmation without changes.
No population-level false-positive rate is claimed.
Strict quality/confirmation gates can frequently return unknown. There is no
liveness protection. Gallery scanning is linear in stored samples and snapshots
are refreshed on camera start. Default-profile startup remains subject to the
restricted session filesystem limitation documented in Phase 3.

Use attendance navigation → باز کردن دوربین تشخیص چهره → شروع دوربین. Test a known
person, an unenrolled person, both together, an empty frame, then unplug the camera.
Names must appear only for confirmed known faces; unknown faces must stay ناشناس.
After an error, reconnect and restart. An empty active gallery must give a Persian
message before opening the camera.

## Phase 4.2

The user authorized daily transactional presence recording after stable recognition,
with one record per person per calendar day, no unknown/absence records, and no
entry/exit tracking. See `PHASE4_2_VALIDATION.md` for implementation and testing.
The no-recording statements above describe the original Phase 4.1 scope;
the main application now records attendance through the Phase 4.2 integration.
