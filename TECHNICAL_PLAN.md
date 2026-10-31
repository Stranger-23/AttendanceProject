I read [Project.md](F:/AttendanceProject/Project.md) carefully and treated it as the main specification. **I recommend Python + PySide6 Widgets + OpenCV YuNet/SFace + SQLite + XlsxWriter.** This provides the best balance of offline recognition, desktop UI, Persian support, development effort, and explainability for a university project.

**No project files were created or modified.**

The Figma review is incomplete: I attempted to open both the [UI Kit](https://www.figma.com/design/FY9a4DiZGFGiFAIn2P0CIB/Courses---Courses-Dashboard-UI-KIT?node-id=86-2234) and [Icon Pack](https://www.figma.com/design/KWeVoT9NO59pBUEfaSGNeQ/Orbicon---Essential-UI-Icons-Set?node-id=12310-10061), but neither was accessible through the web reader, and no browser connection was available. Consequently, I cannot verify their exact colors, spacing, components, or icon style. Screenshots or exported reference frames would allow that review before UI implementation.

**1. Technology comparison**

These are the most suitable candidates; the assessments below are engineering judgments for this project.

| Option | Advantages | Main drawbacks | Fit |
|---|---|---|---|
| **Python + PySide6 Widgets** | Direct OpenCV integration; mature forms and tables; one language for UI and recognition | Requires deliberate styling; packaging includes Python and native libraries | **Best overall balance** |
| **C# + WPF** | Strong Windows tooling; XAML styling; excellent desktop architecture and RTL facilities | Recognition requires OpenCV bindings or explicit model preprocessing/inference integration | Strong second choice |
| **Python + Qt Quick/QML** | Flexible custom visuals and animation; direct Python recognition backend | Adds QML and extra integration work for tables and camera display | Suitable if visual customization dominates |
| **C++ + Qt** | Direct OpenCV integration; strong runtime performance | More development and memory-management complexity | Excessive for this scope |
| **Electron/Tauri + recognition backend** | Flexible dashboard styling | Adds web tooling and potentially another language/process | Little benefit for this specification |

WPF is a credible alternative: Microsoft documents inherited RTL layout through `FlowDirection` and bidirectional text support. I would favor it if learning C# or deeper Windows integration were an explicit project objective. [WPF documentation](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/advanced/bidirectional-features-in-wpf-overview)

For the stated priorities, Python reduces the work needed to build and validate the most important feature: face recognition.

**2. Recommended language and desktop framework**

Use **64-bit Python with PySide6**, the official Qt Python bindings.

Use **Qt Widgets**, including:

- `QMainWindow` and stacked pages for the application shell.
- Standard forms and dialogs.
- `QTableView` with table models for people, history, and reports.
- Qt signals and worker threads for camera processing.
- Shared stylesheets and reusable components for the visual design.

Widgets suit this application’s emphasis on forms, searchable tables, filters, and reporting. Modern appearance will come from consistent typography, spacing, colors, icons, and component styling.

Choose and lock a mutually compatible Python/PySide6/OpenCV version set during the first validation stage; do not independently select every newest release. [Qt for Python](https://doc.qt.io/qtforpython-6/index.html)

**3. Face detection and recognition**

Use **OpenCV with YuNet for detection and SFace for recognition**.

These are separate operations:

- **YuNet:** finds faces and facial landmarks.
- **Alignment:** normalizes each detected face using its landmarks.
- **SFace:** produces a facial embedding.
- **Matching:** compares that embedding against enrolled people using cosine similarity.

OpenCV exposes this workflow through `FaceDetectorYN` and `FaceRecognizerSF`, using pretrained ONNX models. OpenCV can run the models directly, so a separate ONNX Runtime dependency is unnecessary initially. [OpenCV tutorial](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html)

Proposed enrollment flow:

1. Enter and validate personal information.
2. Require exactly one face.
3. Capture several clear samples with slight pose variation.
4. Reject unsuitable samples, such as very small or blurred faces.
5. Generate and store embeddings with model-version metadata.
6. Commit the person and facial data together.

Proposed attendance flow:

1. Open the selected webcam.
2. Show a continuous preview.
3. Process the latest available frame without accumulating a backlog.
4. Detect, align, and embed the face.
5. Compare against active enrolled people.
6. Require a calibrated similarity threshold, separation from competing identities, and repeated agreement across frames.
7. Save attendance transactionally.
8. Show success **only after the database commit succeeds**.

For the initial version, require one person at a time. If multiple faces appear, prompt the user instead of recording attendance.

The threshold must be calibrated on the actual camera and a representative consented test group. Published benchmark thresholds are starting points, not guaranteed operating thresholds.

I would not begin with the Python `face_recognition` package: its own documentation says Windows is not officially supported. [Project documentation](https://github.com/ageitgey/face_recognition)

YuNet and SFace have model-specific license files, which should accompany the selected model artifacts. [YuNet license](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/LICENSE), [SFace license](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/LICENSE)

**4. Local database and attendance rules**

Use **SQLite through Python’s built-in `sqlite3` module**.

It fits a local application without requiring a database server. Use parameterized SQL, foreign keys, transactions, indexes, and numbered schema migrations. A small repository layer is sufficient; an ORM would add little value initially. [SQLite guidance](https://www.sqlite.org/whentouse.html)

Proposed database structure:

| Table | Main contents |
|---|---|
| `people` | Internal ID, unique student/person ID, names, optional information, creation time, active/archive state |
| `face_templates` | Person reference, embedding bytes, dimensions, model version, creation time |
| `attendance` | Person reference, UTC timestamp, local attendance date, recognition score, source |
| `settings` | Camera choice and supported application preferences |
| `schema_migrations` | Applied database migrations |

Store IDs as **text**, preserving leading zeros. Store embeddings in an explicit numeric format rather than executable serialization such as pickle.

My proposed initial attendance policy is:

- One successful attendance record per person per local calendar day.
- A database unique constraint on person and attendance date.
- A short recognition cooldown to prevent repeated processing and notifications.
- Archived people remain in historical reports.
- The initial release uses archival/deactivation only for person removal. Archived people leave the active list and are excluded from future recognition, attendance recording, and face enrollment; personal information, facial templates, and historical attendance are retained. Permanent deletion requires a separately approved retention policy and is outside this release. Reactivation is also outside the initial release.

**Absence needs additional meaning.** Without a roster, schedule, and cutoff, the application can show “not yet recorded today,” but cannot reliably claim a person is absent. Late/absent statuses should only be introduced with corresponding rules.

Daily attendance is a proposed scope decision. If attendance actually belongs to university classes, sessions, or check-in/check-out periods, the schema should reflect that before implementation.

**5. Excel export**

Use **XlsxWriter**.

The requirement is to create new `.xlsx` reports, which suits this library. It supports worksheet RTL direction and cell reading order. [XlsxWriter documentation](https://xlsxwriter.readthedocs.io/worksheet.html#worksheet-right-to-left)

Exports should include:

- Persian column headings.
- Name, person ID, date, attendance time, and status.
- The same filters used by the report screen.
- RTL worksheet layout, readable widths, frozen headings, and filtering.
- IDs written as text.
- User-entered text written explicitly as strings.
- Consistent date/calendar labels and time formats.
- No embeddings or internal database fields.

Excel does not need to be installed to generate the workbook. `openpyxl` can be a development dependency for independently checking exported values.

**6. UI technology and Persian adaptation**

Use **Qt Widgets + Qt stylesheets + SVG icons + the existing IRANSans fonts**.

The actual directory is `Font/Iransans`, and it contains regular, light, medium, bold, black, and Persian-numeral variants. Reuse these assets.

The UI plan is:

- Right-side navigation.
- Persian labels, validation, notifications, errors, and empty states.
- Proper RTL forms, tables, dialogs, and keyboard navigation.
- Explicit handling of mixed Persian text, Latin identifiers, and file paths.
- Directional icons mirrored individually.
- Camera imagery handled separately from layout mirroring.
- Resizable layouts checked at common Windows display scaling levels.

Qt exposes layout-direction controls, but setting layout direction alone does not resolve every text-layout issue; mixed text and dialogs need verification. [Qt widget documentation](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html#PySide6.QtWidgets.QWidget.layoutDirection)

Once the Figma resources are accessible, extract shared design tokens and adapt the relevant components. Use Orbicon SVG assets where permitted; otherwise select one visually compatible icon set after reviewing the reference.

I propose Jalali dates for Persian presentation, with canonical UTC timestamps and explicit local-date handling internally. Calendar choice is a proposal, since Persian language does not itself mandate a calendar.

The approved initial release displays the current Jalali date (`YYYY/MM/DD`) and Windows local 24-hour time (`HH:mm:ss`) below the Recognition dialog guidance and above camera controls. A separate dialog-owned timer refreshes this presentation once per second, including while the camera is stopped or unavailable, and stops when the dialog closes. Existing attendance timestamp capture and daily attendance semantics are unchanged.

**7. Project architecture**

Use **one desktop process with clear responsibility boundaries**:

```text
Views and presenters
        |
Application services
        |
Domain rules
        |
SQLite repositories / recognition / Excel export
```

Responsibilities:

- **UI:** presentation, input, navigation, feedback.
- **Application services:** enrollment, attendance recording, reporting, export.
- **Domain:** person validation, attendance policy, recognition acceptance rules.
- **Infrastructure:** camera access, OpenCV, SQLite, filesystem, workbook generation.
- **Configuration:** paths, model metadata, thresholds, preferences.

Camera capture and inference run outside the UI thread. Workers communicate through signals; they never directly modify widgets. Database connections belong to their owning threads, with short, serialized write operations.

History, dashboard statistics, reports, and export should share query/filter logic so their totals agree.

**8. Proposed folder structure**

This is a proposal only; these files have not been created.

```text
AttendanceProject/
├── Project.md
├── Font/
│   └── Iransans/
├── pyproject.toml
├── src/
│   └── attendance_app/
│       ├── main.py
│       ├── bootstrap.py
│       ├── ui/
│       │   ├── pages/
│       │   ├── dialogs/
│       │   ├── components/
│       │   ├── presenters/
│       │   ├── table_models/
│       │   └── styles/
│       ├── application/
│       ├── domain/
│       ├── recognition/
│       ├── storage/
│       │   ├── repositories/
│       │   └── migrations/
│       ├── reporting/
│       └── configuration/
├── assets/
│   ├── icons/
│   └── models/
├── tests/
│   ├── unit/
│   └── integration/
├── packaging/
└── docs/
```

Writable runtime data should live under `%LOCALAPPDATA%\SmartAttendance\`, separate from installed files and source code.

**9. Required dependencies**

| Dependency | Purpose |
|---|---|
| `PySide6` | UI, threading/signals, SVG rendering, application resources |
| `opencv-python` | Webcam capture, image processing, YuNet/SFace inference |
| `numpy` | Embeddings and similarity calculations |
| `XlsxWriter` | Excel generation |
| Standard-library `sqlite3` | Database access |
| Standard-library logging, datetime, pathlib | Diagnostics, timestamps, paths |
| YuNet and SFace ONNX files | Bundled recognition models |

Development/build dependencies:

- `pytest` and `pytest-qt`.
- `openpyxl` for export verification.
- `ruff` for formatting/static checks.
- `PyInstaller` for Windows packaging.

Use Qt’s Persian-calendar facilities where practical; only add a calendar package if the validation stage identifies a concrete need. GPU frameworks, pandas, cloud SDKs, and a backend server are unnecessary for the initial scope.

**10. Windows packaging and distribution**

Start with **PyInstaller in one-folder mode**, built on Windows x64.

Bundle Python, Qt plugins, OpenCV/native dependencies, models, fonts, icons, and license notices. Users will not need a separate Python installation. PyInstaller documents both folder and single-file distribution. [PyInstaller documentation](https://pyinstaller.org/en/stable/operating-mode.html)

Deliver a ZIP containing the executable folder for the university demonstration. An installer can follow if required.

Before delivery:

- Test on a clean Windows machine without development tools.
- Verify camera access and fully offline recognition.
- Verify models and fonts load from packaged paths.
- Verify database writes work without administrator privileges.
- Verify upgrades preserve user data.
- Provide backup/restore using SQLite’s backup facilities.

Qt’s `pyside6-deploy` is a credible alternative if the packaging trial finds a specific advantage. [Qt deployment documentation](https://doc.qt.io/qtforpython-6/deployment/index.html)

**11. Technical risks and limitations**

| Risk | Planned response |
|---|---|
| Camera unavailable, busy, or disconnected | Clear Persian errors, retry/release handling, backend testing on target hardware |
| False recognition | Conservative calibration, ambiguity rejection, repeated agreement, unknown-person tests |
| Poor lighting, pose, glasses, or blur | Enrollment quality checks and practical camera guidance |
| Photo/video spoofing | Explicitly document that the initial version has no robust liveness guarantee |
| UI freezes or growing frame delay | Worker processing and a bounded latest-frame buffer |
| Duplicate attendance | Cooldown plus a transactional database uniqueness constraint |
| Database loss/corruption | Migrations, safe backup/restore, interruption testing |
| Biometric data exposure | Store locally, avoid retaining raw frames by default, exclude templates from logs/exports |
| Persian date/search inconsistencies | Central formatting and search normalization, including Arabic/Persian character variants |
| Packaging failures or unsigned-app warnings | Early packaged trial and clean-machine verification |
| Asset licensing | Include applicable library/model notices and verify font/icon redistribution rights |

The base SQLite database is not encrypted. Local storage should not be described as encrypted biometric protection.

Recognition throughput and accuracy remain unverified until measured on the target laptop. Initial acceptance should prioritize avoiding incorrect attendance over recognizing every difficult frame.

**12. Step-by-step development plan**

1. **Approve scope and attendance semantics.**  
   Confirm daily versus session attendance, date presentation, expected roster size, and target Windows hardware.

2. **Complete the visual-reference review.**  
   Inspect accessible Figma frames/exports and document tokens, components, and icon usage.

3. **Validate the core technical path.**  
   After approval, build a small camera/detection/recognition experiment on the target laptop. Measure latency and recognition behavior.

4. **Validate packaging early.**  
   Package that experiment with models and fonts; run it offline on a clean Windows machine.

5. **Create the application foundation.**  
   Establish module boundaries, configuration, Persian text handling, logging, and the RTL shell.

6. **Implement storage and people management.**  
   Add migrations, validation, repositories, archiving, and backup/restore.

7. **Implement face enrollment.**  
   Add capture guidance, quality checks, embedding storage, and facial-data replacement.

8. **Implement reliable attendance recording.**  
   Add recognition states, calibrated acceptance, duplicate prevention, and commit-aware success feedback.

9. **Implement history, dashboard, and reports.**  
   Add consistent search, date filters, sorting, summaries, and person history.

10. **Implement Excel export.**  
    Validate Persian text, RTL layout, IDs, date boundaries, and agreement with report results.

11. **Apply and verify visual polish.**  
    Refine all specified screens, keyboard access, scaling, dialogs, and error states.

12. **Perform final acceptance and distribution.**  
    Test unknown faces, repeated appearances, restarts, camera failures, storage failures, backup recovery, and the packaged offline workflow.

The proposed stack is ready for review. **Implementation has not started; Figma visual verification remains outstanding.**
