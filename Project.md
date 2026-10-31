# Smart Attendance Management System

## 1. Project Overview

This project is a **Windows Desktop Application** for managing attendance using **face recognition**.

The application should allow users to register people, capture their facial data, recognize them through a webcam, automatically record attendance, view attendance history, generate reports, and export attendance data to Excel.

The application is intended for a university project and should be a functional, locally running desktop application rather than a simple visual prototype.

### Platform

**Windows Desktop only**

The project does NOT require:

- Web application
- Mobile application
- Android
- iOS
- Cloud deployment
- Online services

---

# 2. Main Goals

The application should provide the following core functionality:

- Register new people
- Store personal information
- Register/capture facial data
- Access the computer webcam
- Detect and recognize registered faces
- Automatically record attendance after successful recognition
- Store date and time of attendance
- View attendance history
- Search and filter attendance records
- Generate attendance reports
- Export attendance data to Excel
- Manage registered people
- Provide a modern and easy-to-use user interface

The application should feel like a real desktop product rather than a basic university demo.

---

# 3. UI / Design References

## Current reliable design references

**DESIGN REFERENCE:** `UI_SPEC.md` is the primary written UI/design-system specification. `design-reference/` contains visual screenshots exported from the supplied Figma UI Kit. Use these two local sources together as the current source of truth for visual implementation.

The Figma share link is not currently a reliable source for direct automated inspection. Do not depend on opening or reading the Figma file directly, and do not block development on Figma access. The links below are retained for provenance and possible later refinement.

Read `PROJECT.md`, `TECHNICAL_PLAN.md`, and `UI_SPEC.md`, and inspect every image in `design-reference/` before implementation changes. Keep these specification files and the reference directory in the project root.

**APPLICATION FUNCTIONALITY:** This is a Face Recognition Attendance System, not a Courses Dashboard. Functional requirements remain webcam access, face enrollment and recognition, student/person management, attendance recording and history, reports, local SQLite storage, and real Excel (`.xlsx`) export.

### Visual direction and screenshot usage

Follow the supplied UI Kit's visual language as documented in `UI_SPEC.md`:

- Light desktop SaaS dashboard style adapted to a Windows desktop application
- Purple primary accent
- White cards on a light gray page background
- Rounded cards and controls
- Clean typography using the supplied IRANSans font
- Subtle borders and shadows
- Spacious layout and clear visual hierarchy
- Consistent outline icons

Use every supplied image as a visual reference:

- `design-reference/Light Mode Desktop - Dashboard.png`: navigation, header, cards, spacing, hierarchy, and calendar styling
- `design-reference/Light Mode Desktop - Add New Event.png`: dimmed overlay, drawer, stacked fields, and primary action placement
- `design-reference/Light Mode Desktop - Checkout (Subscription).png`: form grouping, labels, inputs, buttons, and card composition
- `design-reference/Light Mode Desktop - Sign Up.png`: typography, form spacing, controls, and primary/secondary action hierarchy

These are examples of the design language, not application screens to copy literally. Do not copy Courses branding, course content or functionality, subscriptions, premium promotions, payment/checkout logic, or social sign-in. Adapt the components to the attendance application's actual features.

### Scope and document alignment

- The English/LTR positions in the screenshots and `UI_SPEC.md` describe the reference product. Adapt navigation, forms, tables, dialogs/drawers, and directional icons to the Persian RTL application; do not mirror camera imagery simply because the layout is RTL.
- Tablet/mobile examples in `UI_SPEC.md` do not expand the Windows-only scope. Apply resizing/reflow principles to desktop window sizes and Windows display scaling.
- The font fallback in `UI_SPEC.md` allows the project's existing font; use `Font/Iransans/` rather than introducing Inter or another font unnecessarily.
- Suggested absent/late statistics, schedules, class filters, and attendance-rule controls do not establish new business rules. The attendance period, expected roster, and late/absence cutoffs remain decisions to clarify before implementing those features. Do not infer them from a visual example.
- The illustrative Confirm/Register action in `UI_SPEC.md` does not replace automatic attendance recording after confident recognition and successful storage. Any manual attendance workflow requires an explicit functional decision.
- `TECHNICAL_PLAN.md` records the earlier recommendation and Figma-access limitation. Its pending direct-Figma review wording is superseded by the local-reference workflow above; exact Figma tokens/assets may be incorporated later without blocking the first implementation.
- Preserve the existing technical architecture. Explain unresolved specification conflicts before making architectural changes; visual examples must not silently add application functionality.

## UI Kit

Figma UI Kit:

https://www.figma.com/design/FY9a4DiZGFGiFAIn2P0CIB/Courses---Courses-Dashboard-UI-KIT?node-id=86-2234&t=6Bo5A2zBtCw5LVcN-1

Use `UI_SPEC.md` and the exported screenshots from this UI Kit as the current references for:

- Layout
- Cards
- Buttons
- Forms
- Tables
- Navigation
- Spacing
- Border radius
- Typography hierarchy
- Colors
- General visual language

The UI Kit is English, but the final application must be **Persian and RTL**.

Do not blindly copy components that are irrelevant to an attendance management system. Adapt the design system to the actual requirements of this project.

---

## Icon Pack

Figma Icon Pack:

https://www.figma.com/design/KWeVoT9NO59pBUEfaSGNeQ/Orbicon---Essential-UI-Icons-Set?node-id=12310-10061&t=DefeSySH6EU0Ij5G-1

This icon pack remains a reference for later refinement. Exact Figma icons are **not required for the first implementation**, and their unavailability must not block development.

Use one consistent, modern outline icon library that visually matches the local UI references. Do not create random custom SVG icons or mix unrelated icon families. Keep stroke weight and sizing consistent: approximately 20–24px for navigation and 16–20px for compact controls, as described in `UI_SPEC.md`.

Keep icons modular and replaceable through a shared icon provider/mapping and centralized assets. Exact Figma icons should be swappable later without restructuring views. Use supplied matching assets when available. If no suitable library is installed, select one consistent library for the first implementation rather than blocking on unavailable assets.

---

# 4. Fonts

A `Font/Iransans/` folder exists inside the project.

The folder currently contains **IranSans** font files.

Use the provided font when appropriate for the Persian user interface.

The font folder may be expanded later with additional fonts if needed.

Do not download or introduce a different font unnecessarily when the provided font is suitable.

---

# 5. Language and RTL

The final user interface must be completely **Persian (Farsi)**.

The entire application should use **RTL (Right-to-Left)** layout.

This applies to:

- Navigation
- Forms
- Tables
- Buttons
- Dialogs
- Notifications
- Search fields
- Reports
- Dashboard
- Settings
- Empty states
- Error messages
- Success messages

Do not simply translate English text into Persian.

The layout itself must be properly adapted for RTL.

Icons that have directional meaning should also be mirrored or adjusted when necessary.

---

# 6. Main Application Screens

The following screens should be included in the initial application.

The exact layout can be refined during development.

## 6.1 Dashboard

The main overview screen.

Possible information:

- Total registered people
- Today's attendance count
- Today's absent count
- Recent attendance records
- General attendance statistics
- Quick actions

The dashboard should provide a clear overview without unnecessary information.

---

## 6.2 Attendance / Face Recognition

The main screen for recording attendance using the webcam.

Features:

- Webcam preview
- Face detection
- Face recognition
- Recognition status
- Recognized person's name
- Live current Jalali date (`YYYY/MM/DD`) and Windows local 24-hour time (`HH:mm:ss`) inside the Recognition dialog, refreshed once per second independently of camera state. This display is presentation-only and does not determine attendance timestamps.
- Attendance confirmation
- Clear success/failure feedback

The UI should clearly communicate when the system is:

- Waiting for a face
- Detecting a face
- Processing recognition
- Successfully recognizing a person
- Unable to recognize a person

---

## 6.3 People Management

A page containing all registered people.

Features:

- View people
- Search people
- View details
- Add a new person
- Edit person
- Deactivate/archive person
- Manage/update facial data

The list should be clean and easy to navigate.

In the initial release, removal means deactivation/archival. Deactivation removes the person from the active list and excludes them from future recognition, attendance recording, and face enrollment. Personal information, facial templates, and historical attendance are retained. Permanent deletion and reactivation are outside the initial release.

---

## 6.4 Add Person

A form for registering a new person.

Suggested information:

- First name
- Last name
- Person ID / Student ID / Employee ID
- Optional additional information
- Facial data

The face registration process should be simple and clearly explained to the user.

---

## 6.5 Person Details

Display detailed information about a selected person.

Possible information:

- Name
- ID
- Registration date
- Facial data status
- Attendance statistics
- Attendance history

---

## 6.6 Attendance History

Display all attendance records.

Suggested columns:

- Person name
- Person ID
- Date
- Time
- Status

Features:

- Search
- Person filter
- Date filter
- Date range filter
- Sorting
- View details

---

## 6.7 Reports

A reporting section for analyzing attendance.

Users should be able to filter reports by:

- Person
- Date
- Date range
- Attendance status

Reports should be clear and suitable for university/project presentation.

---

## 6.8 Excel Export

Users should be able to export attendance records to an Excel file.

The exported file should be structured and readable.

At minimum, it should contain:

- Person name
- Person ID
- Date
- Attendance time
- Status

The user should preferably be able to select the desired date range before exporting.

---

## 6.9 Settings

A simple settings section.

Possible settings:

- Camera selection
- Application preferences
- Data management
- About the application

Do not add unnecessary settings.

---

# 7. Face Recognition Workflow

The general workflow should be:

1. Access the webcam.
2. Capture frames from the camera.
3. Detect faces.
4. Extract facial features/embeddings.
5. Compare the detected face against registered people.
6. Identify the person if the confidence/similarity threshold is sufficient.
7. Display the recognized person's identity.
8. Record attendance.
9. Save the attendance record locally.
10. Display a clear confirmation to the user.

If the system cannot confidently identify a person, it must **not automatically record attendance**.

The recognition threshold should be configurable in code and chosen carefully to reduce false positives.

---

# 8. Duplicate Attendance Prevention

The system should prevent accidental duplicate attendance records.

For example, if the same person remains in front of the camera for several seconds, the application should not create dozens of attendance records.

Implement a reasonable cooldown/de-duplication mechanism.

The exact logic can be determined during development.

---

# 9. Local Data Storage

The application should work locally.

No online server or cloud database is required.

The application should store:

- Registered people
- Facial recognition data
- Attendance records
- Application settings

Keep **SQLite** as the application's internal database, following `TECHNICAL_PLAN.md`. It stores people, facial recognition data, attendance records, and application settings locally.

**Excel is the report/export format, not the internal database.** SQLite does not replace the required Excel export.

The intended data flow is:

```text
Face Recognition
→ Attendance Event
→ SQLite
→ Reports
→ Excel Export (.xlsx)
```

The solution should be:

- Free
- Reliable
- Easy to maintain
- Suitable for a Windows desktop application
- Suitable for a university project

---

# 10. Excel Export

The application must support Excel export.

The implementation should generate a real `.xlsx` file.

The exported data should have:

- Proper column names
- Readable formatting
- Correct Persian text encoding
- Dates and times in a consistent format
- No unnecessary technical/internal fields

---

# 11. Technology Stack

The programming language and technology stack were not predetermined in the original requirements. The recommendation is now documented in `TECHNICAL_PLAN.md`: Python, PySide6 Widgets, OpenCV YuNet/SFace, SQLite, and XlsxWriter. Do not restart stack selection or introduce major architectural changes as part of the UI-reference update. SQLite remains the internal database and Excel export remains required. Main implementation remains a separate stage after review.

Before implementation, review the project requirements and the documented technology recommendation together.

Consider:

- Windows Desktop development
- Webcam access
- Face recognition
- Local database
- Excel export
- Modern UI
- Persian/RTL support
- Easy packaging into a Windows executable
- Free/Open Source libraries
- Stability
- Ease of development and maintenance
- Suitability for a university project

Before writing the main application code, explain:

1. Recommended programming language
2. Recommended desktop framework
3. Face recognition solution
4. Database solution
5. Excel library
6. Important dependencies
7. Application architecture
8. Packaging/distribution approach

Do not choose a technology simply because it is popular. Choose it because it fits the actual requirements of this project.

---

# 12. Important Constraints

This is a university project.

Avoid unnecessary complexity.

Do NOT introduce:

- Paid APIs
- Paid AI services
- Cloud services
- Online authentication
- Unnecessary microservices
- Web technologies unless they are genuinely required by the selected desktop framework
- Features unrelated to attendance management

Prefer free and open-source technologies whenever practical.

The final application should be understandable and explainable during a university project presentation.

---

# 13. Application Architecture

The project should use a clean and maintainable architecture.

Separate major responsibilities such as:

- UI
- Application/business logic
- Face recognition
- Database/storage
- Excel export
- Configuration
- Utilities

Avoid putting the entire application logic into a single file.

Use clear naming conventions and a logical folder structure.

---

# 14. Development Process

Before starting the main implementation:

### Step 1 — Analyze

Read this project specification, `TECHNICAL_PLAN.md`, and `UI_SPEC.md`, and inspect every screenshot in `design-reference/`. Use `UI_SPEC.md` plus the local screenshots for the current UI workflow; direct access to the Figma links is not a prerequisite.

### Step 2 — Propose

Propose:

- Technology stack
- Architecture
- Folder structure
- Required dependencies
- Database structure
- Face recognition approach
- Main application flow

### Step 3 — Validate

Identify technical risks and potential problems, especially:

- Webcam access
- Face recognition performance
- Persian/RTL UI
- Local data storage
- Excel export
- Windows packaging

### Step 4 — Implement

After the architecture is clear, implement the application in logical stages.

Do not attempt to build everything blindly in one step.

---

# 15. Development Philosophy

The priority is:

1. Correct face recognition
2. Reliable attendance recording
3. Reliable local data storage
4. Correct Excel export
5. Good user experience
6. Modern UI
7. Visual polish

The application should be functional first and polished second.

However, the final interface should still look professional enough for a university project presentation.

---

# 16. Final Product

The final result should be a functional Windows desktop attendance application with:

- Persian RTL interface
- Modern UI
- Webcam support
- Face recognition
- Person management
- Attendance recording
- Attendance history
- Reports
- Excel export
- Local data storage
- Windows executable/distributable application

The application should be designed as a real, coherent product rather than a collection of disconnected demo screens.
