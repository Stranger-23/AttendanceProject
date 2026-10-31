# Phase 4.2 — Transactional attendance recording

Implemented and tested on 2026-10-24. Phase 4.1 has been manually accepted by
the user for all six required scenarios; see `PHASE4_1_VALIDATION.md`.
Its recognition thresholds, quality gates, matching and three-frame stability
logic are unchanged. No Excel, dashboard/statistics, history UI, absence records,
entry/exit tracking or session rules were introduced.

## Changed files

Paths beginning with `src/attendance_app/`:

- `domain/attendance.py`: immutable committed receipt with created/existing status.
- `storage/migrations/m003_attendance.py`: attendance table and daily unique key.
- `storage/migrations/__init__.py`: register migration 003; migrations 001/002 unchanged.
- `storage/repositories/attendance.py`: validated, transactional idempotent insert.
- `application/attendance_service.py`: confirmed-known result gate.
- `application/attendance_recorder.py`: bounded background writer, coalescing,
  successful-write cache, failure backoff and drain-on-close.
- `recognition/worker.py`: submit confirmed results and captured observation time;
  expose attendance feedback without changing recognition results.
- `bootstrap.py`: wire repository/service through the existing composition root.
- `ui/main_window.py`, `ui/pages/recognition.py`, `ui/dialogs/recognition.py`:
  wire attendance service and show Persian guidance and committed/error feedback.
- `storage/backup.py`: validate attendance timestamps in v3 backups.

Tests and documentation:

- `tests/unit/test_attendance.py`: 14 new attendance tests.
- `tests/unit/test_storage_people.py`, `tests/unit/test_enrollment.py`:
  update schema-version expectations to 3; preserve existing behavioral assertions.
- `tests/integration/test_shell.py`: add end-to-end asynchronous persistence/feedback
  and database-error UI test; all previous UI tests retained.
- `tests/manual/validate_live_recognition.py`: optional `--attendance` smoke test
  against a temporary database; default recognition-only mode still supported.
- `docs/PHASE4_1_VALIDATION.md`, this document and `PHASE4_2_TEST_RESULTS.txt`.

## Schema and time policy

Migration 003 adds only `attendance`: id, person_id (foreign key to people.id,
ON DELETE RESTRICT), attendance_date, attendance_time, observed_at, status,
similarity and created_at. `UNIQUE(person_id, attendance_date)` is the final
duplicate guard. Status is constrained to `present`; similarity is optional
cosine score in [-1, 1], not a probability.

Daily boundaries follow the Windows local calendar day, read from an aware local
timestamp immediately after frame capture. Canonical attendance_date is Gregorian
ISO YYYY-MM-DD; attendance_time includes the captured UTC offset. observed_at and
created_at are UTC ISO timestamps. Display calendar conversion is a later UI
concern. Configure Windows date/time/timezone correctly (Iran on this deployment).
No timezone package or new dependency is required. A delayed write uses the
captured observation timestamp, not the date/time when its transaction runs.

Existing v1/v2 databases upgrade transactionally through the current migration
registry. Exact schema/checksum validation, backups and restore support v1/v2/v3;
older backup sources are not modified. Restoring an older backup intentionally
restores its older dataset, with an automatic pre-restore recovery backup.

## Recognition-to-attendance flow and rules

1. Existing camera capture, detection, embedding and recognition continue unchanged.
2. Only `RecognitionEngine.recognize()` results enter the attendance path. Its first
   two tentative matches are unknown, so they cannot record attendance.
3. Each confirmed known face is submitted independently. Unknown/empty results
   never enqueue writes; multiple detections of one identity coalesce.
4. A background writer calls AttendanceService and AttendanceRepository using the
   project's short-lived, thread-owned SQLite connections.
5. BEGIN IMMEDIATE covers active/enrolled-person validation and an INSERT with
   targeted ON CONFLICT(person_id, attendance_date) DO NOTHING, followed by reading
   the created/existing row. No other constraint or database failure is ignored.
6. Only after the transaction context commits can a success receipt be returned.
   Existing rows retain their first observed timestamp and score. Foreign keys
   and a live active/enrolled check prevent stale/ineligible identities being saved.
7. Persian feedback distinguishes newly recorded presence, already-recorded
   presence and failed writes. It uses a separate label from face recognition;
   up to three recent outcomes remain visible for simultaneous people.

One record per person per day is durable across repeated frames, leaving/returning,
camera restarts, application restarts and concurrent independent DB connections.
A small per-session successful-person/day cache avoids repeated DB writes and
notifications; pending tasks are coalesced. The database unique key remains
authoritative even when caches are empty. Midnight allows the next day's record.

The queue holds at most 256 pending observations. Full queues produce a clear
unsaved-state warning; still-visible confirmed faces can resubmit later. Failures
are logged by exception type, report no false success, leave recognition running,
and allow resubmission after a three-second per-person backoff while still confirmed.
Cache/backoff state is pruned on day changes. Accepted queued work drains after
camera release before worker-finished/dialog-close, keeping UI responsive and
preventing writes from outliving the modal roster/backup boundary.

## Automated validation

Commands (existing PowerShell/virtual environment):

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests/unit -v
.venv/Scripts/python.exe -m unittest discover -s tests/integration -v
.venv/Scripts/python.exe tests/manual/validate_live_recognition.py --attendance
```

Final automated result: **49 unit tests and 6 UI integration tests passed;
0 failures, 0 errors, 0 skipped**. The exact named-test transcript is in
`PHASE4_2_TEST_RESULTS.txt`. All 35 pre-existing unit tests and 5 pre-existing
UI tests are included; enrollment and recognition behavior remain green.

New unit cases:

- Confirmed known only after three consecutive frames; date/time/status/identity.
- Repeated frames and reopened service preserve the first daily record.
- Unknown (even with an identity field) and no-face frames create no attendance.
- Two known people each receive one record.
- Known plus unknown creates only the known person's record.
- Concurrent independent connections plus direct SQL uniqueness enforcement.
- Local midnight and writer cache rollover permit a new daily record.
- Invalid timestamp/similarity, inactive and unenrolled identities rejected.
- Transaction failure rolls back; no false success; backoff/recovery succeeds once.
- Slow writer does not block submission; duplicates coalesce; existing-row feedback.
- Recognition worker continues through a database failure and sends only knowns.
- v2 migration preserves people; v3 backup/restore/recovery and v2 source preservation.
- Commit failure returns no success receipt and leaves no row.
- Queue overflow reports unsaved work; other identities can still be recorded.

The new UI test verifies real SQLite writes through the recognition worker, no
feedback before commit, continued camera frames while the write is held, one
success notification after commit, safe close/drain, and Persian failure feedback
while recognition remains running.

## Real-camera smoke result

An isolated temporary person was enrolled with three real-camera samples, then
processed through the unchanged recognizer and background attendance writer:
181 frames, 179 known and 2 initial unknown results, exactly **1 attendance row**
and **1 attendance notification**. Camera released safely; temporary database and
templates removed. No real roster or production attendance was changed.
OpenCV's existing nonfatal graph-engine target warnings still occur.

## Remaining manual checks and limitations

Phase 4.2 implementation and automated validation are complete. Operator acceptance
of the new persistence UI should check prolonged presence, camera/application restart
on the same day, two known people and known-plus-unknown, and database lock/error
recovery on the real deployment profile. These persistence cases are covered with
controlled automated inputs but were not all repeated with live participants.

The Windows local timezone is the day boundary policy; there is no app timezone
selector. Clock/timezone corrections can affect calendar-day grouping. A process
crash can lose queued, uncommitted observations; success is never shown for them.
Database errors require renewed confirmed observations to retry; no durable offline
retry journal is claimed. Close waits for already accepted queued writes; under a
database lock this may take longer, while the UI stays alive. Feedback is a bounded
current-session status area, not attendance history. Existing liveness and linear
gallery-scan limitations remain unchanged.

## Recommended next phase

Perform operator acceptance of Phase 4.2 persistence, then implement a read-only
attendance history view with agreed date presentation/filtering when authorized.
Excel export, dashboards/statistics, absence and entry/exit rules remain later work.
