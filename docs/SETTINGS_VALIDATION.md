# Settings & Persistent Camera Preferences

This is the next approved scope after manually accepted Reports and Excel Export;
it is not an officially numbered Phase 8.

## Implementation

- Migration 4 (`settings`) adds a local text key/value table. Existing migrations
  and attendance rules are unchanged. No camera row means camera index 0.
- SettingsRepository uses Database connections; SettingsService validates integer
  indices 0 through 16 and reads the database on demand without a preference cache.
  Boolean, fractional, string and out-of-range save inputs are rejected.
- The Persian RTL Settings page adds the default camera selector, explicit save
  feedback, and application name/version/description. Existing backup/restore
  controls remain. The page scrolls at smaller desktop sizes.
- Enrollment and Recognition read the same service when opening their dialogs.
  Existing dialogs retain their selected camera; no active camera is switched.
  Dialog overrides remain temporary and never update the saved default.
- Unavailable cameras follow the existing failure/retry/release lifecycle and do
  not change the preference. Invalid stored preferences produce a Persian error
  and can be corrected in Settings rather than silently overwriting stored data.
- Full database backups naturally include preferences. Restore refreshes the
  Settings selector and preserves existing page refresh signals. The next camera
  dialog reads the restored value. Older backups are migrated privately before
  restore; a backup without preferences restores the camera default of 0.

## Automated verification

Run with the project virtual environment, using temporary fixture databases only:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/unit -q
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/integration -q
```

Added six settings unit tests and five Settings/camera UI tests. Coverage includes
default without writes, save/reload, a separate Python process restart, invalid
input/stored values, existing-service refresh after restore, version-3 backup
upgrade, Settings feedback/About, both camera entry points, unchanged open dialogs,
worker camera indices and simulated unavailable-camera recovery, and real restore
through the Settings page followed by a new camera dialog.

Existing schema assertions in test_storage_people.py and test_enrollment.py now
expect the deliberately added fourth migration. No prior checks were removed.

Final results: **80 unit tests passed**, **30 integration/UI tests passed**.
All **5 new Settings UI tests passed at QT_SCALE_FACTOR=1.5** as well. Expected
failure-scenario diagnostics and existing nonfatal OpenCV warnings appeared in
the unit run. No automated test failures remain.

Isolated styled Settings screenshots were inspected at 1280x820 and 960x640;
the smaller page scrolls to reach About. No production profile or camera was used.

## Manual acceptance remaining

1. Launch through the project .venv, open Settings and save a supported camera.
2. Restart and verify the selected camera persists.
3. Open Enrollment and Recognition and verify both default to the saved index.
4. Verify an unavailable index produces the existing Persian camera error and
   leaves the saved preference intact; return to an available index and retry.
5. In an isolated profile, back up, change the camera, restore, and confirm the
   Settings selector and subsequently opened camera dialogs use the restored value.
6. Verify keyboard access, save/error feedback, About, scrolling and Windows scaling.
