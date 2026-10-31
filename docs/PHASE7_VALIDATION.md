# Phase 7 — Attendance Reports and Excel Export

## Scope and existing behavior

Phase 6 Dashboard was manually accepted by the user. Phase 7 replaces only the
Reports placeholder at its existing navigation position. Reports are presence-only.
The status choices are exactly `همه وضعیتها` and `حاضر`, following the approved
Phase 7 plan. Neither choice introduces absence, lateness or unknown records.

Reports reuse History's normalization, current-person identity, archived-history
inclusion, typed sorting, numeric Solar Hijri controls, date conversion, and the
same AttendanceService/AttendanceRepository query. Search, person and inclusive
date restrictions combine with AND. Initial filters are all dates/all people.
The person selector includes people with attendance, including archived people.
The two summaries are matching attendance person-days and distinct represented
people, calculated from the exact same records as the preview.

There are no migrations or new indexes. Schema version remains 3. Recognition,
enrollment, daily attendance recording, History, Dashboard, People management,
backup format, runtime locations and stored timestamps retain their behavior.
Packaging, preferences, permanent deletion, class/session rules, entry/exit,
absence, lateness, percentages, charts and PDF reports remain outside this phase.

## Architecture and snapshot contract

- `domain/reports.py`: frozen filters and immutable report snapshots.
- `application/report_service.py`: delegates validation/search to AttendanceService;
  no alternate reporting SQL or database writes.
- `application/export_service.py`: prepares display values and metadata, stages
  output beside its destination, and publishes only a closed successful workbook.
- `reporting/excel.py`: XlsxWriter implementation, independent of Qt and SQLite.
- `ui/pages/reports.py`: reuses History controls/model/delegate through a subclass;
  History itself is unchanged. Reports adds summaries, status and export controls.
- `ui/presenters/reports.py`: reuses the bounded History read lifecycle, with a
  report-specific worker and a separate single-export worker.
- Bootstrap wires the services. MainWindow adds Reports navigation refresh,
  restore invalidation and close coordination with History/Dashboard/Reports
  readers and the export worker.

A filter edit clears preview/export eligibility immediately. A successful read
creates a snapshot; the export action captures its records in current table sort
order. Export never re-queries SQLite. New attendance or identity edits require
refresh before they appear. A restore invalidates pending reads and the current
preview; the existing missing-person fallback re-queries all people. An export
already started finishes its captured snapshot without holding a DB connection.
Nested Save/confirmation dialogs cannot start an export after their report was
invalidated. Closing waits asynchronously for active work, without terminating
threads or abandoning a partially published workbook.

Loading/errors show unavailable summaries (`—`), not false zeros or old rows.
Valid empty reports show real zeros and disable export. Read errors permit retry.
Export has separate busy/success/error feedback and prevents duplicate exports.
Save cancellation and replacement refusal make no file changes.

## Workbook contract

Runtime dependency: XlsxWriter 3.2.9. Development verification: openpyxl 3.1.5.
These are declared in pyproject.toml. Network installation was unavailable in the
agent environment; the exact versions were available in the bundled runtime and
copied into the project virtual environment for verification. Runtime dependency
directories were not modified. Normal installation uses the declared dependencies.

The workbook contains:

1. `اطلاعات گزارش`: applied search/person/date/status filters, captured local
   snapshot creation time, numeric record/person counts, and snapshot basis.
2. `حضورهای ثبت‌شده`: name, public ID, attendance date, attendance time, status.

Both worksheets are RTL. Attendance headings are frozen and have Excel filtering;
columns have readable widths. IDs, Solar Hijri `YYYY/MM/DD`, and saved `HH:mm:ss`
are explicit text. Counts are numeric. User text is written with write_string;
automatic formula/URL/number conversion is disabled. No internal identity keys,
UTC observations, biometric scores/templates or optional personal notes are exported.
The writer rejects excessive rows or cell text instead of silently truncating.

The destination must be `.xlsx`. Existing files require explicit replacement
confirmation. Windows rename publishes new files without clobbering a destination
that appeared after Save; replace publishes an authorized overwrite. Generation,
close or publication failures preserve the existing destination and clean staging
files. A POSIX no-clobber hard-link path is included, but Windows is the target.
Success is reported only after publication succeeds. A process/power failure is
not claimed to provide filesystem durability or automatic orphan-file recovery.

## Automated validation

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/unit -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/integration -v
$env:QT_SCALE_FACTOR='1.5'
.\.venv\Scripts\python.exe -m unittest discover -s tests/integration -p test_reports.py -v
Remove-Item Env:QT_SCALE_FACTOR
```

Recorded results: **74 unit tests and 25 integration/UI tests passed**, including
all 66 prior unit tests and all 18 prior UI tests. All **7 Reports UI tests** also
passed at QT_SCALE_FACTOR=1.5. All databases and workbooks used isolated fixtures.
No production profile, real roster, attendance or camera was used.

New tests cover shared filters/normalization, summaries, current identities,
archived history, snapshot immutability, invalid/empty filters and unchanged DB
dumps. Workbook verification independently reads saved files with openpyxl and
checks exact rows/order, Persian values, text IDs, long IDs, formula/URL-like
input, numeric counts, RTL, frozen headings, filtering, Solar Hijri leap-day
output, saved local clock values and 5,003-row completeness. It checks row/text
limit rejection, replacement refusal, a destination appearing during generation,
generation/publication failure, actual Windows open-file rejection and cleanup.

UI tests cover combined filters/reset, date validation, empty/read-error/retry,
obsolete read rejection, slow work, preview-versus-later-data consistency, sorting,
Save cancellation, declined overwrite, export failure/recovery, duplicate export
prevention, nested dialog invalidation, navigation, real isolated backup restore,
and closing the main window while export is running. Existing acceptance tests
continue to cover History's date boundaries and normalization in detail.

`tests/manual/validate_reports_preview.py <output-directory>` renders a styled
isolated shell at 1280×820 and 960×640 and writes a synthetic workbook. It uses a
temporary DB and never opens the production profile. Top/bottom desktop renders
were visually inspected, including 150% Qt scaling: controls remain readable,
page scrolling reaches export, and table scrolling exposes remaining rows/columns.
This does not establish Excel application rendering or packaged deployment.

Existing nonfatal OpenCV graph-engine warnings remain unchanged.

## Manual operator acceptance — pending

Use normal data only for read-only comparisons and choose a new export filename.
Use an isolated test profile for identity, recording and restore scenarios.
Do not alter real attendance or restore production just to create fixtures.

1. Open Reports. Verify Persian RTL, keyboard focus, two status choices, all dates
   and all people. Compare the preview with History and verify both summaries.
2. Search names and public IDs, including leading zeros, Arabic/Persian character
   variants and literal `%`, `_`, `\`. Combine search with person/date filters.
3. Select an archived person with attendance. Confirm history remains included
   and current name/ID agrees with History. Unenrolled people with history remain.
4. Check a known day, equal range endpoints, both inclusive boundaries, and a
   Solar Hijri year/leap transition. Reverse endpoints: validation, no export.
5. Check no attendance and no matches in prepared profiles. Expect genuine zero
   summaries and disabled export. Reset restores default filters and all records.
6. Sort the preview, export a new `.xlsx`, and open it in Excel or an available
   compatible viewer. Verify both Persian sheets, RTL, five attendance columns,
   frozen headings, filtering, exact row order/count and distinct-person count.
7. Verify leading-zero/long IDs and numeric Solar Hijri dates/saved local times.
   Formula-like names/IDs remain literal text. No technical/biometric fields appear.
8. Cancel Save and decline replacement of a disposable existing workbook. Verify
   no file changes. Approve replacement and verify the workbook updates.
9. Keep a disposable destination open in Excel and try replacement. If Windows
   locks it, expect Persian error feedback and the old workbook preserved. Close
   it and retry successfully. Do not fill disks or damage production to test errors.
10. In a test profile, record attendance or edit an identity after preview. Export
    must retain that preview. Refresh: the new committed data appears. Returning
    to Reports also refreshes. Existing daily duplicate prevention remains.
11. In an isolated profile, restore a prepared backup. Verify Reports refreshes,
    including fallback if its selected person no longer exists. Already started
    exports retain their captured data; a new export uses the refreshed preview.
12. Check 960×640, 150% Windows scaling, page/table scrolling and keyboard access.
    Export remains reachable and the UI responsive during slow work. Closing the
    app during export waits for completion without a thread warning or partial file.

Record PASS/FAIL/NOT RUN, selected filters, expected/actual counts, workbook/viewer
used, exact Persian errors and relevant screenshots. No biometric imagery is needed.
