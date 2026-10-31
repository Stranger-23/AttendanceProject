# Phase 6 — Dashboard / Attendance Statistics

## Approved scope and prerequisites

Phase 5 History is complete and manually accepted by the user. Phase 6 replaces
the initial `page_dashboard` placeholder, keeping its navigation position and icon.
The approved Dashboard plan was supplied and approved in the conversation; there
was no separate Dashboard planning file in the repository before this phase.

The four metrics are exactly:

| Label | Meaning |
| --- | --- |
| کل افراد ثبت‌شده | All people, including archived people (explicit subtitle) |
| افراد فعال | Current active people, independent of face enrollment |
| حضورهای ثبت‌شده امروز | Rows whose stored attendance_date equals the captured Windows-local day; archived people included |
| کل حضورهای ثبت‌شده | All recorded person-days; archived history included |

Recent attendance is limited to ten rows, explicitly labeled `۱۰ رکورد اخیر`.
The section title is `آخرین حضورهای ثبت‌شده`; its five short headings are name,
public ID, date, time, status. It uses current person identity, numeric Solar Hijri
`YYYY/MM/DD`, saved local `HH:mm:ss`, and the existing `حاضر` badge. No internal
IDs, UTC timestamps, biometric scores or Gregorian dates are shown.

Navigation shortcuts open existing Attendance, People and History pages, without
starting a camera or introducing another workflow. A separate `مشاهده تاریخچه`
button appears below the recent table.

No absence, lateness, attendance rate, ranking, streak, expected attendance,
working-day average, charts, trends, percentage changes or not-yet-attended metric
was added. Reports, Excel, packaging and new backup UI remain outside scope.

## Storage, dates and architecture

- SQLite schema version remains 3. Migrations, indexes, attendance recording,
  recognition, enrollment and People management behavior are unchanged.
- `domain/dashboard.py` defines a frozen DashboardSnapshot with captured_day,
  registered_people, active_people, today_attendance, total_attendance, and a tuple
  of immutable recent attendance records.
- Flow: DashboardPage → DashboardPresenter/DashboardRead → AttendanceService →
  AttendanceRepository → SQLite. Existing composition-root wiring is reused.
- Presenter captures one local Gregorian ISO day per request and passes it through
  the service to the repository. The same day drives the heading via the existing
  attendance_date() formatter. There is no timestamp/timezone reinterpretation of
  historical records or rewriting of stored dates.
- Repository uses one connection and explicit deferred `BEGIN`, the approved scalar
  aggregate SELECT, and one joined recent-row SELECT with parameterized `LIMIT 10`.
  It ends the read transaction before returning. No BEGIN IMMEDIATE, writes,
  persisted statistics cache, migration or new index is used.
- Recent order matches History: attendance_date DESC, saved clock time DESC, id DESC.
  Future-dated stored observations are not silently omitted. No complete History
  download is used to obtain counts.
- Presenter uses one running read, at most one latest pending request, generation
  validation and main-thread signal handling. If the local day changes during a
  read, its obsolete result/error is discarded and a new-day snapshot requested.
- Read failures display Persian feedback and unavailable values (`—`), not zeros.
  Retry replaces the whole snapshot. Empty successful data displays real zeros.
- Refresh occurs on initial navigation, Dashboard entry, explicit refresh, existing
  restore completion, and window reactivation while Dashboard is current. A visible
  page checks for day changes every minute. It does not poll counts continuously.
- Shutdown asynchronously waits for BOTH History and Dashboard readers, including
  pending-read invalidation, without destroying a running QThread.

History's existing status painter was moved unchanged to
`ui/components/attendance_table.py` and imported by both pages. Its search, filters,
headings, sorting, details and date controls are not redesigned. Existing History
and recording regression tests remain included.

## Desktop presentation

Reuse existing Card, IRANSans, purple tokens, table model and RTL conventions.
Four summary cards are arranged right-to-left across a wide content area, switching
to two columns at narrower desktop widths. Large numbers align across cards.
The page scrolls vertically; the read-only recent table scrolls horizontally and
vertically as needed. Numerical dates, saved times and identifiers retain readable
direction and leading zeros. No mobile/tablet navigation or font reduction was added.

The styled isolated shell was rendered and visually inspected at 1280×820 and
960×640, including a QT_SCALE_FACTOR=1.5 run. At the minimum size, scrolling reaches
the recent table and its History action; the table still exposes all ten rows by
scrolling. These are desktop/Qt scaling checks, not a claim of packaged deployment
acceptance on another Windows machine.

## Automated results

Commands from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/unit -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/integration -v
$env:QT_SCALE_FACTOR='1.5'
.\.venv\Scripts\python.exe -m unittest discover -s tests/integration -p test_dashboard.py -v
```

Recorded results:

- **66 unit tests passed** (all 58 previous tests plus 8 Dashboard tests).
- **18 integration/UI tests passed** (all 11 previous tests plus 7 Dashboard tests).
- All 7 Dashboard UI tests also passed at QT_SCALE_FACTOR=1.5.
- A 5,000-row isolated snapshot measurement took approximately **0.006 seconds**
  on this machine; no new index was needed. This is a local fixture measurement,
  not a guarantee for every production dataset or disk.

Coverage includes empty/people-only/older-attendance/all-archived states, current
identity, unenrolled active people, History count agreement, stored-day boundaries
and offsets, future observations, ten-row limit/order, duplicate prevention,
snapshot immutability, date validation, query-only enforcement, unchanged database
dump/indexes, and read failure propagation. A test-only independent writer commits
between the counter and recent queries; the deferred read transaction preserves
the original coherent snapshot.

UI coverage includes numeric Solar Hijri headings/rows, text IDs, loading without
false zeros, retry, coalescing/stale-result rejection, midnight discard/reload,
visible day-change checks, navigation without camera startup, reactivation, restore
refresh and closing with both page readers active. Existing Phase 5 tests verify
its accepted behavior after the shared-delegate extraction.

All fixtures and visual previews used isolated temporary databases. No production
roster, attendance, schema or camera was used. Existing nonfatal OpenCV model-test
warnings remain unchanged. Operator acceptance on the normal profile is pending.

## Manual acceptance setup

Use normal existing data for read-only checks. For exact arithmetic and population
changes, use a prepared test profile with:

- A: active, attendance yesterday and today.
- B: active, no attendance (may have no face enrollment).
- C: archived, attendance today.

Expected baseline: registered **3**, active **2**, today **2**, total attendance **3**.
For the ten-row limit, use a profile containing more than ten attendance records.
Do not edit SQL, alter Windows time, archive real people or restore production data
merely to manufacture test cases. Mark unavailable scenarios NOT RUN. Recognition
or People-management actions intentionally modify whichever profile is being used.

## Manual acceptance checklist

1. Launch the normal application. Dashboard is the initial page, with the same
   sidebar position/icon and Persian RTL layout. The heading date is numeric Solar
   Hijri YYYY/MM/DD with no month name or Gregorian date.
2. Check the four cards against known data. The registered card explicitly includes
   archived people. Active does not imply enrolled/recognition-ready. Today counts
   all stored records for today's local day. Lifetime counts person-days.
3. In the controlled baseline profile, expect 3 / 2 / 2 / 3. Compare today's value
   with History filtered to the corresponding Solar Hijri day and all people.
4. Check recent records against History's default ordering. Current names/IDs,
   leading zeros, saved local times and حاضر must match. Archived rows remain.
   With more than ten rows in storage, Dashboard exposes exactly ten recent rows;
   History continues to expose all matching rows.
5. Verify the three shortcuts and the recent-table History button. They navigate to
   the existing pages and do not automatically open or start a camera.
6. In a test profile, archive A: registered remains 3, active becomes 1, today stays
   2 and total attendance stays 3. Return to Dashboard or refresh to see the update.
7. In a test profile, add a new active person without recording attendance: registered
   and active each increase by one; attendance values do not change. Changing an
   existing person's name/ID is reflected in recent rows after refresh.
8. If testing with a camera, explicitly enter the existing recognition workflow and
   record an eligible person's first attendance today. Return to Dashboard: today
   and lifetime each increase once. Repeat recognition the same day: no extra row
   or counter increase. This step intentionally writes attendance.
9. Navigate away/back, use تازه‌سازی, switch away from the application and return,
   and restart it. Counts and recent rows reflect committed data. Loading shows
   unavailable placeholders rather than temporary zeros or old rows.
10. Verify empty, people-only, older-attendance-only and all-archived test profiles:
    genuine zero counts are shown; existing people/history remain represented;
    empty recent attendance says هنوز حضوری ثبت نشده است.
11. Verify keyboard focus/accessibility, wide four-card and narrow two-column layout,
    960×640 minimum, page/table scrolling and 150% Windows scaling. Controls and
    History access remain reachable without shrinking text.

Read failures, restore refresh, day rollover, obsolete callbacks and slow shutdown
already have isolated automated coverage. Do not damage a production database or
change its timezone/clock to repeat them. If a real read error occurs, expect Persian
feedback, `—` values rather than zero, and recovery through تازه‌سازی.

Report PASS/FAIL/NOT RUN for each applicable step, actual versus expected four
counts, the displayed Solar Hijri day, History comparison, exact Persian errors
and relevant screenshots of controls/table. No face or biometric imagery is needed.
