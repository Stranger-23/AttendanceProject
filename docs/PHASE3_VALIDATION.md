# Phase 3: technical validation and enrollment

## Run

From the project root, using the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m attendance_app.recognition.validation --models-only
.\.venv\Scripts\python.exe -m attendance_app.recognition.validation --seconds 15
.\.venv\Scripts\python.exe -m attendance_app.recognition.validation --preview
.\.venv\Scripts\python.exe -m unittest discover -s tests/unit -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/integration -v
.\.venv\Scripts\python.exe tests/manual/validate_live_enrollment.py
```

The standalone preview is an explicitly started technical test, not an
attendance workflow. Its capture samples remain in memory and are discarded.
The manual enrollment test uses a temporary database outside the source tree;
it never modifies the real roster. `--auto-capture` explicitly opts into
programmatic clicks against the real camera for an end-to-end integration
check. It does not verify operator-guided pose variation.

In the application: select an active person in **افراد**, select
**ثبت / جایگزینی چهره**, start the camera, capture three suitable samples with
slightly varied pose, then save. Replacing existing facial data requires
confirmation. Cancel leaves the previous templates intact. Archived people
cannot enroll. Person details show actual enrollment status.

## Boundaries and storage

Camera opening, reading, model loading, detection, alignment and embedding
extraction belong to the camera QThread. Frames go through a one-slot mailbox
polled by the UI, not an unbounded signal queue. The worker owns and releases
the camera; closing the dialog requests interruption and defers disposal until
the thread finishes. A driver that blocks indefinitely in `read()` can delay
closing; threads are never forcibly terminated. DirectShow is the selected
Windows backend after the Media Foundation probe failed on this laptop.

Only explicit sample requests can generate enrollment samples. No-face and
multiple-face frames reject capture. Initial, configurable quality gates are
80px minimum face side, Laplacian variance 60, mean grayscale brightness
40–215, and a 0.5-second sample interval. These are engineering capture
defaults requiring field evaluation, not calibrated identity thresholds.
YuNet's detection-score gate 0.9 is unrelated to identity acceptance.

Migration 002 adds only `face_templates`, referencing `people.id`. Templates
are normalized 128-value little-endian float32 blobs (512 bytes), with dtype,
dimensions, model SHA-based ID, alignment model ID, and UTC creation time.
Replacement deletes/inserts within one transaction after checking active
state, person registration and expected prior template IDs. Failed saves
roll back; stale sessions are rejected. No raw frames/crops are saved and no
embeddings or person information are logged. SQLite/backups remain unencrypted.

Runtime data remains `%LOCALAPPDATA%\SmartAttendance\smart_attendance.db`.
Version-1 backups are validated against the version-1 schema, migrated only
in a private snapshot, then restored after preserving a recovery backup.
Existing backup files themselves are not rewritten.

Models are lazy-loaded only for camera use, from `assets/models/`. Startup has
no model downloads. See `assets/models/SOURCES.md` for provenance/licenses.
An API/model error is surfaced with the exact OpenCV error text; models and
graph engines are never silently switched. Models must be bundled at this
relative location during the later packaging phase; standalone wheel/EXE
distribution is not claimed validated in this phase.

## Observations on the connected Windows laptop (2026-10-24)

- Both SHA-256 hashes and sizes matched. Both APIs loaded with OpenCV 5.0.0.
- DirectShow camera 0 opened, supplied 640×480 BGR frames, and released.
  Media Foundation reported it could not capture by index on this machine.
- Initial 90-frame probe observed 88 no-face frames and 2 one-face frames.
  Landmarks contained ten coordinates; alignment was 112×112; SFace output
  was finite, shape 1×128. A pair of live samples gave cosine 0.78869.
- Reusable 10-second validation run: 275 frames, 10.255 seconds, 26.815 FPS;
  capture-plus-processing median 32.064ms, p95 47.832ms; 273 ready frames,
  2 blurred frames; two embeddings gave cosine 0.92160. Numbers vary with
  lighting, pose, startup, and hardware load. They are not accuracy results.
- A controlled frame containing two side-by-side copies of a live single-face
  frame produced two detections at 1280×480. This validates the multiple-face
  input path; two different people live in the camera remain a manual check.
- End-to-end real-camera UI check saved three templates in an isolated DB,
  verified them through a reopened storage instance, and stopped its worker.
  One run took 3.704 seconds; GUI timer maximum gap was 125ms. No biometric
  test artifacts are retained after the temporary database is removed.
- All 29 unit/model/storage tests and 4 UI integration tests passed. The UI
  suite and real-camera enrollment check also passed with `QT_SCALE_FACTOR=1.5`.
  The People page and camera-off enrollment dialog were rendered and visually
  inspected at that scale; no face images were saved for visual inspection.
- A default-profile startup probe was blocked by this session's filesystem
  permissions on `C:\Users\Lenovo\AppData\Local\SmartAttendance\logs\application.log`.
  Production paths were not redirected or changed. The actual Qt shell and
  live-camera tests above ran with explicitly isolated temporary configurations.
  Default-profile startup/migration must therefore be rechecked outside the
  restricted agent session on the user's Windows desktop.
- OpenCV emitted nonfatal warnings that the new graph engine does not support
  preferable targets yet. Inference still completed. No alternate engine,
  model, or package was selected to suppress the warning.

## Remaining manual acceptance

Run the preview with no one visible, one person, and two different people.
Test dim/bright light, motion blur, camera busy/unplug/reconnect, stop/restart,
cancel, replacement confirmation, operator-guided pose changes and 150%
Windows display scaling. The automated suites cover their state/transaction
paths with controlled inputs, but do not replace these physical-device checks.
No final identity threshold, recognition accuracy, or liveness/anti-spoofing
claim is made. No attendance recording, rules, history, reports, Excel export,
or attendance statistics have been implemented.
