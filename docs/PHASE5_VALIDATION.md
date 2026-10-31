# Phase 5 — Attendance History / Search / Date Filtering

## Scope and prerequisites

The user reported that the Phase 4.2 manual database-lock/recovery test passed.
Phase 5 implements a read-only History page at the existing `page_history`
navigation position. Reports, dashboard/statistics, Excel export, new backup UI,
packaging and attendance-rule changes are outside this phase.

The approved presentation is Persian Solar Hijri, numeric `YYYY/MM/DD` only
(for example `1405/08/05`). SQLite attendance dates remain Gregorian ISO
`YYYY-MM-DD`; schema version 3 and migrations 001–003 are unchanged. Historical
days and local clock times are never recalculated using today's timezone.

## Implementation

- Reuse `AttendanceService`, `AttendanceRepository`, the existing database wrapper,
  registered `normalize_search`, and the existing composition-root service wiring.
- Join attendance to the person's CURRENT name and public text identifier. Include
  archived people and history without requiring current facial enrollment.
- Table columns: name, public identifier, Solar Hijri date, saved `HH:mm:ss`, and
  `حاضر`. Internal IDs, raw UTC values and similarity are not shown. Details add
  saved UTC offset and the person's current active/archive state, without Gregorian
  dates or biometric information.
- Search uses full-name OR public-ID substring matching with exactly the existing
  normalization: trim/collapse whitespace, casefold, Arabic/Persian yeh/kaf mapping,
  literal `%`, `_`, `\`. No digit conversion, fuzzy matching, token search or new
  half-space semantics. Empty search leaves other restrictions intact. Debounce:
  180 ms.
- Person selector includes every person with attendance, including archived people,
  and uses internal IDs as values. Search, person and date filters combine with AND.
- Date modes: `همه تاریخها`, `یک روز`, `بازه تاریخ`. Boundaries are inclusive;
  reversed ranges report validation without querying. Reset clears all filters.
- Qt's installed `QCalendar.System.Jalali` provides conversion without dependencies.
  Numeric section date editors use year/month/day and arrow controls; no popup
  calendar or month names are introduced. Set/select the year, month or day section
  to edit it. Internally each QDate remains an absolute day and is converted to
  Gregorian ISO only when constructing query filters.
- Initial order is date descending, saved local clock time descending, row ID
  descending. Table headers sort typed underlying values; IDs remain text. Sorting
  is retained through refresh. All matching rows are available by scrolling; no
  pagination or hidden cap.
- One asynchronous read at a time, one newest pending request, generation checks
  to reject obsolete outcomes. Loading disables details. Read failures have Persian
  feedback and a refresh/retry action. Shutdown waits asynchronously for a running
  read before closing the main window.
- Entering History and explicit refresh reload committed rows. Existing restore
  completion also refreshes History and invalidates older requests; a restored-away
  person selection falls back to all people and re-queries.

## Automated verification

Run in the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/unit -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/integration -v
```

Recorded result: **58 unit tests and 11 integration/UI tests passed**, including all
49 earlier unit tests and 6 earlier integration tests. Fixtures use isolated
temporary databases; no production roster/attendance was changed.

New cases cover:

- Current identity, archived people, text IDs, selector eligibility, exact search
  normalization/literal escaping, invalid input and combined filters.
- Inclusive dates, empty/future dates, reversed ranges, deterministic sorting,
  read-only database dump equality and safe read failures.
- Known Gregorian/Solar Hijri pairs including `2026-10-27` / `1405/08/05`, Nowruz,
  Esfand leap days, reverse conversion and invalid non-leap dates.
- Table/detail numeric dates, numeric picker keyboard editing, leap-year boundary,
  empty/error/recovery states, filter reset, archived selector labels and selection.
- Slow reads, obsolete result rejection, current identity after refresh, existing
  backup restore refresh, navigation reload and main-window close during a read.
- A 5,003-row fixture confirms no silent result truncation and model population.

The existing nonfatal OpenCV graph-engine target warnings still occur in model
tests. No recognition packages or models were changed.

The isolated styled shell was rendered and visually inspected at normal and
minimum 960×640 desktop sizes, including a QT_SCALE_FACTOR=1.5 run. Filters remain
accessible and tables scroll at the minimum size. No live-camera or production
data was required. Operator acceptance on the normal deployment profile is pending.

## Manual acceptance

1. Open `تاریخچه حضور و غیاب`. Confirm Persian RTL, the five columns and committed
   attendance with current names/IDs. Date format must be numeric Solar Hijri only;
   time must match the stored local observation time and status must be `حاضر`.
2. Search a partial name and a public identifier (including leading zeros), then
   clear it. Check Arabic/Persian letter variants and whitespace. Literal `%`, `_`
   and `\` must not act as wildcards.
3. Select one person and confirm other people's rows disappear. Archived people
   with attendance must be listed and marked; their history remains available.
4. Select `یک روز`. Select/edit numeric year, month and day sections for a known
   recorded Solar Hijri day: only that day's rows should appear. Select an empty
   day (or future day): show filtered-empty feedback without an error.
5. Select `بازه تاریخ`; verify both endpoints, equal endpoints, and a range across
   month/year boundaries. Reverse the endpoints: show date validation, not records
   for a silently swapped range.
6. Combine search, person and date restrictions, then choose `پاک کردن فیلترها`.
   All records return with empty search, all people and all dates selected.
7. Sort date/time/name/ID headers and open a selected row's details. Dates must
   remain numeric Solar Hijri. No Gregorian dates, technical row IDs or similarity
   percentages should appear. Details should show the saved UTC offset.
8. Navigate away/back and restart the app: committed history remains. After a new
   real attendance recording, return to History and verify the row once. This
   last recording step intentionally adds attendance through the existing workflow.
9. Verify keyboard navigation, narrow desktop window and Windows display scaling.
   During loading, controls stay responsive and stale rows/details are unavailable.

Report PASS/FAIL/NOT RUN by step, the visible date/time for a known record, filters
used for boundary/empty cases, any exact Persian errors, and relevant screenshots
of the table/filter controls. Face imagery and biometric data are unnecessary.
Read-error recovery, restore and slow-close paths already have isolated automated
coverage; do not corrupt or alter the production database to repeat those tests.
