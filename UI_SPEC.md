chcp 65001# UI_SPEC.md — Courses Dashboard UI Reference

## 1. Purpose

This document translates the supplied Figma/UI Kit reference screens into implementation guidance for Codex.

**Primary goal:** reproduce the visual language and component patterns of the reference UI in the attendance/face-recognition application.

The reference is a **desktop light-mode dashboard UI**. Do not copy the Courses product's content or business logic; reuse its visual system, layout principles, components, spacing, states, and interaction patterns.

### Reference screens provided

- Dashboard
- Schedule / Add New Event modal
- Checkout / form screen
- Sign Up screen

---

# 2. Global Visual Direction

## Overall style

- Modern SaaS dashboard
- Light theme
- Clean, spacious layout
- Rounded cards and containers
- Purple as the primary brand/accent color
- Very light gray page background
- White surfaces/cards
- Dark near-black primary text
- Muted gray secondary text
- Thin light-gray borders
- Soft, restrained shadows
- Rounded controls and buttons
- Simple outline icons

The UI should feel polished and friendly rather than corporate/heavy.

Avoid:
- Dense layouts
- Strong gradients unless specifically required
- Excessive shadows
- Sharp rectangular cards
- Too many accent colors
- Decorative effects that compete with the content

---

# 3. Color System

The screenshots indicate the following approximate palette.

> These values are visual approximations from the supplied screenshots. If exact Figma design tokens are available later, replace these values with the exact tokens.

## Primary

```text
Primary Purple:       #6C5CE7 / approximately
Primary Purple Dark:  #5B4BD6
Primary Purple Light: #F0EDFF
```

Use the primary purple for:
- Primary buttons
- Active navigation item
- Active tabs
- Important links
- Selected calendar dates
- Selected/active states
- Important icons
- Progress indicators

## Neutral colors

```text
Page Background:      #F7F8FA
Surface / Card:       #FFFFFF
Primary Text:         #111111
Secondary Text:       #777B84
Muted Text:           #AEB3BC
Border:               #E4E6EA
Input Background:     #F1F3F5
Divider:              #E7E8EB
```

## Status colors

```text
Success:              #2DBE60
Warning:              #F2B705
Error:                #E5484D
Info:                 #4A90E2
```

Status colors should be used sparingly and should not replace the primary purple system.

---

# 4. Typography

The reference uses a modern sans-serif UI typeface.

Preferred implementation:

```text
Font family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

If the project already has a defined font, use the project's font consistently instead.

## Typography hierarchy

### Page title

- Large
- Bold / semibold
- Near-black
- Approx. 28–32px desktop

### Section title

- Bold / semibold
- Approx. 20–24px

### Card title

- Medium / semibold
- Approx. 16–18px

### Body

- Regular
- Approx. 14–16px

### Secondary text

- Regular
- Approx. 13–15px
- Muted gray

### Small labels

- Approx. 12–14px
- Medium when used for metadata

Do not use excessive font weights. Most UI text should use regular, medium, semibold, and bold only where necessary.

---

# 5. Layout System

## Desktop canvas

The reference screenshots are approximately:

```text
2048 × 1456
```

The design uses a persistent left sidebar and a flexible main content area.

## Main structure

```text
┌────────────────────────────────────────────────────────────┐
│ Sidebar │ Main content                                    │
│         │ ┌────────────────────────────────────────────┐   │
│         │ │ Top header                                 │   │
│         │ └────────────────────────────────────────────┘   │
│         │                                                  │
│         │ Content / cards / tables / panels               │
│         │                                                  │
└────────────────────────────────────────────────────────────┘
```

### Sidebar

Reference characteristics:

- White background
- Fixed left column
- Approximately 275px wide at the reference desktop size
- Generous horizontal padding
- Logo at top
- Navigation grouped into sections
- Premium/promotional card at bottom
- Navigation icon + label
- Active item uses a very light purple background and primary purple text/icon

For the attendance application, preserve this pattern but replace the Courses navigation labels with the application's actual sections.

Suggested attendance app navigation:

```text
GENERAL
Dashboard
Live Attendance
Students

REPORTS
Attendance History
Excel Reports

OTHER
Settings
Support
```

Only include sections that actually exist in the application.

---

# 6. Sidebar Components

## Logo

Reference:
- Purple outline/book icon
- Bold black brand name
- Icon positioned left of wordmark

For the attendance application:
- Use the application's own logo/name.
- Preserve the same visual balance: icon + bold wordmark.

## Navigation item

Normal:

```text
Icon   Label
```

Characteristics:
- Muted gray icon
- Muted gray text
- Comfortable vertical padding
- Rounded container

Active:

```text
Icon   Label
```

Characteristics:
- Very light purple background
- Purple icon
- Purple text
- Semibold label
- Rounded corners

Do not use a strong purple fill for the entire active navigation item.

## Section label

Examples in reference:

```text
GENERAL
COURSES
OTHER
```

Style:
- Uppercase
- Small
- Muted gray
- Medium/semibold
- More spacing above than below

---

# 7. Top Header

The dashboard reference has a large white rounded header/card.

Characteristics:
- White surface
- Rounded corners around 20–24px
- Generous horizontal padding
- Height roughly 90px
- Positioned near the top of the main content
- Search/action icons on the right
- Avatar at far right

For the attendance application, use:

```text
Page title / breadcrumb                 Actions / user
```

Possible actions:
- Search
- Notifications
- User/profile

Do not include unnecessary ecommerce actions such as shopping basket unless the application actually needs them.

---

# 8. Cards

Cards are a major part of the visual language.

## Card style

```text
background: white
border-radius: approximately 20–24px
border: subtle or none
shadow: very soft
padding: 20–28px
```

Cards should have clear internal spacing.

Avoid:
- hard black borders
- small corner radii
- excessive shadows

---

# 9. Buttons

## Primary button

Reference appearance:

- Purple background
- White text
- Rounded corners
- Medium/semibold text
- Full-width in forms when appropriate
- Height roughly 48–56px

Example:

```text
┌──────────────────────────────┐
│            Save              │
└──────────────────────────────┘
```

Use for:
- Save
- Add Student
- Start Attendance
- Export Excel
- Confirm
- Submit

## Secondary button

- White or very light surface
- Gray/purple border
- Dark text
- Same height system as primary

## Disabled

- Reduced contrast
- Muted background/text
- No strong shadow

## Destructive

Use the red status color only for destructive operations such as deleting a student.

---

# 10. Inputs

The reference uses large, comfortable input fields.

Characteristics:
- White or very light gray background
- Thin gray border
- Rounded corners approximately 10–12px
- Height around 48–52px
- Comfortable horizontal padding
- Clear labels above fields
- Placeholder/secondary text in muted gray

Example:

```text
Label
┌─────────────────────────────────┐
│ Placeholder                      │
└─────────────────────────────────┘
```

For attendance forms:
- Student name
- Student ID
- Camera/device
- Date
- Time range
- Search
- Filters

Labels should remain visible instead of relying only on placeholders.

---

# 11. Search

The reference uses a simple outline search icon.

For the application:
- Search should use an icon inside/next to the input.
- Search fields should have the same radius and height language as other inputs.
- Search should be visually secondary to primary actions.

---

# 12. Tables

The reference UI is card-based, but the attendance application needs tables for attendance records.

Use the same visual language:

```text
┌────────────────────────────────────────────────────────────┐
│ Student       ID        Date        Time       Status       │
├────────────────────────────────────────────────────────────┤
│ Ali Ahmadi    1024      21 Oct      08:31      Present     │
│ Sara Mohammadi 1025     21 Oct      08:35      Present     │
└────────────────────────────────────────────────────────────┘
```

Table rules:
- Put table inside a white rounded card.
- Header text is muted/darker gray and medium weight.
- Rows have comfortable vertical padding.
- Use subtle dividers.
- Avoid heavy grid lines.
- Status should use small pills/badges.
- Keep columns aligned and readable.

---

# 13. Status Badges

Use compact rounded pills.

Example:

```text
Present
```

Recommended:
- Present → subtle green background + green text
- Absent → subtle red background + red text
- Unknown → subtle gray background + gray text
- Late → subtle yellow background + dark/yellow text

Do not use saturated backgrounds unless necessary.

---

# 14. Dashboard Pattern

The supplied Dashboard screen establishes the main composition.

Pattern:

```text
Top header

Main area:
┌─────────────────────────────┬─────────────────────┐
│ Main cards / information    │ Secondary panel     │
│                             │                     │
├─────────────────────────────┴─────────────────────┤
│ Recent activity / list / table                    │
└───────────────────────────────────────────────────┘
```

For the attendance application, adapt this into:

### Top area

```text
Welcome / page title
Quick actions
```

### Summary cards

Suggested:

```text
Today's Attendance
Present
Absent
Late
Total Students
```

### Main content

Possible:

- Today's attendance overview
- Recent attendance records
- Camera/live recognition status
- Quick actions

Do not copy the Courses dashboard's content. Only reuse its layout style.

---

# 15. Attendance Dashboard

Recommended visual hierarchy:

```text
Welcome back

┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Students    │ Present     │ Absent      │ Late        │
│ 32          │ 27          │ 3           │ 2           │
└─────────────┴─────────────┴─────────────┴─────────────┘

┌───────────────────────────────────────┬───────────────┐
│ Live Attendance / Camera              │ Today's       │
│                                       │ summary       │
│           Camera preview              │               │
│                                       │               │
└───────────────────────────────────────┴───────────────┘

Recent Attendance
┌────────────────────────────────────────────────────────┐
│ ... table ...                                           │
└────────────────────────────────────────────────────────┘
```

---

# 16. Modal / Drawer

The Add New Event reference shows a large right-side modal/drawer.

Important characteristics:

- Background page becomes dimmed
- Drawer is white
- Large rounded top-left/bottom-left corners
- Width roughly 40–50% of desktop screen
- Content has generous padding
- Close button in top-right
- Primary action fixed/near bottom
- Form fields vertically stacked

For attendance application use this pattern for:
- Add student
- Edit student
- Attendance details
- Add/edit schedule
- Filters
- Confirmation dialogs when appropriate

## Overlay

Use:

```text
rgba(0,0,0,0.15–0.25)
```

The underlying page should remain visible but clearly inactive.

## Drawer

Use:
- White background
- Radius approximately 24px
- 24–32px padding
- Clear title
- Close icon
- Primary action at bottom

---

# 17. Calendar

The reference uses a clean calendar card.

Characteristics:
- White rounded card
- Month title centered or balanced
- Previous/next controls
- Weekday labels muted
- Current/selected day displayed as a purple circular/rounded highlight
- Lots of whitespace

For attendance:
- Use calendar for date selection/filtering.
- Selected date should use primary purple.
- Do not fill the whole calendar with accent colors.

---

# 18. Forms

The Sign Up and Checkout screens establish a consistent form language.

Form pattern:

```text
Heading
Supporting text

Social/alternative action (if needed)

Divider

Label
Input

Label
Input

Primary button

Secondary/link action
```

For the attendance app:
- Prefer simple, task-focused forms.
- Keep labels above inputs.
- Use one primary action per form.
- Avoid excessive fields in one screen.

---

# 19. Checkboxes

Reference checkbox:
- Square outline
- Purple when selected
- Simple check mark
- Small radius

Use for:
- Confirmations
- Bulk selection
- Preferences

For bulk student selection, use the same style.

---

# 20. Icons

The reference uses thin/medium outline icons with rounded visual language.

Preferred icon style:
- Outline
- Simple geometry
- Consistent stroke width
- No mixed icon families
- Approximately 20–24px in navigation
- 16–20px for compact controls

Important:
**Do not invent random icon styles.** Use one consistent icon library throughout the application.

If the project already contains supplied SVG icons, use those assets instead of recreating them.

For missing icons, use a consistent icon library already installed in the project.

---

# 21. Avatars

Reference avatar:
- Circular
- Approximately 48–56px in header
- Positioned at far right
- Can contain profile image or initials

For the attendance app:
- User/admin avatar may be used.
- Student avatars can be circular thumbnails if needed.
- Do not use avatars where they do not provide useful information.

---

# 22. Illustrations and Images

The reference uses illustrations in promotional areas.

For the attendance application:
- Do not copy the Courses illustrations.
- Use application-specific visuals only when useful.
- Camera/face-recognition imagery can be used in empty states or onboarding.
- Keep illustrations secondary to actual application data.

---

# 23. Spacing

Use a consistent spacing scale.

Recommended base:

```text
4px
8px
12px
16px
20px
24px
32px
40px
48px
64px
```

Common usage:

```text
8px   icon-to-text
12px  small internal gaps
16px  input/row spacing
20px  card internal spacing
24px  card padding
32px  section spacing
40px+ page-level separation
```

Avoid arbitrary one-off spacing values.

---

# 24. Border Radius

Reference uses noticeably rounded UI.

Recommended:

```text
Small controls:       8–12px
Inputs:               10–12px
Buttons:              10–14px
Cards:                20–24px
Large panels:         24px+
Pills:                999px
Avatar:               50%
```

Keep the radius system consistent.

---

# 25. Shadows

Shadows should be subtle.

Recommended concept:

```text
0 4px 20px rgba(0,0,0,0.04)
```

Use shadows mainly to distinguish floating cards/modals from the page.

Do not make every card visibly shadowed.

---

# 26. Responsive Behavior

The supplied references are desktop-first.

The implementation should still be responsive.

### Desktop

- Persistent sidebar
- Multi-column dashboard
- Large cards
- Full table

### Tablet

- Reduce sidebar width
- Reduce card gaps
- Allow two-column layouts to collapse

### Mobile

- Sidebar becomes a drawer/bottom navigation
- Cards stack vertically
- Tables become horizontally scrollable or transform into compact cards
- Drawer/modal becomes nearly full screen
- Header actions remain accessible

Do not simply shrink desktop layouts. Reflow the content.

---

# 27. Interaction States

Every interactive component should have:

```text
Default
Hover
Active / Selected
Focus
Disabled
Error (when relevant)
Success (when relevant)
```

### Hover

Use a subtle background or elevation change.

### Focus

Use a visible purple focus ring.

### Active

Use primary purple or light-purple background.

### Disabled

Reduce contrast but maintain readability.

---

# 28. Accessibility

Maintain:
- Sufficient text/background contrast
- Visible keyboard focus
- Semantic buttons and inputs
- Labels for form controls
- Tooltips/accessible labels for icon-only buttons
- Do not communicate status only through color

For example:

```text
Green badge + "Present"
```

is preferable to a green dot alone.

---

# 29. Attendance Application Adaptation

The visual reference is a Courses Dashboard, but the final application is:

**Face Recognition Attendance System**

Therefore, Codex MUST NOT copy:
- Courses branding
- Course names
- Subscription/payment business logic
- Premium banners
- Course-specific illustrations
- Ecommerce checkout behavior

Instead, reuse:
- Sidebar architecture
- Header architecture
- Card styling
- Form styling
- Modal/drawer pattern
- Calendar styling
- Table styling
- Typography hierarchy
- Purple accent system
- Spacing
- Radius
- Icon treatment
- Light-mode visual language

---

# 30. Recommended Application Pages

Use the reference style to build approximately these screens:

## 01 — Dashboard

Contains:
- Today's attendance summary
- Total students
- Present/absent/late statistics
- Live recognition status
- Recent attendance
- Quick actions

## 02 — Live Attendance

Contains:
- Camera preview
- Recognition status
- Detected student
- Current date/time
- Attendance confirmation
- Recent recognized students

## 03 — Students

Contains:
- Student list/table
- Search
- Filter
- Add student
- Edit student
- Delete student
- Student ID
- Face registration status

## 04 — Attendance History

Contains:
- Date filter
- Student filter
- Status filter
- Attendance table
- Export to Excel

## 05 — Reports / Excel Export

Contains:
- Date range
- Class/student filters
- Preview of report
- Export Excel button

## 06 — Settings

Contains:
- Camera/device settings
- Attendance rules
- Recognition settings
- Application preferences

Only implement screens required by the project scope. Do not create unnecessary features just to imitate the reference.

---

# 31. Excel Export UI

Excel is the report/output format, not the visual design language.

The UI should provide a clear primary action:

```text
[ Export Excel ]
```

The export area should follow the same white-card + purple-button pattern.

Suggested flow:

```text
Choose date range
       ↓
Choose optional filters
       ↓
Preview report
       ↓
[ Export Excel ]
```

---

# 32. Face Recognition UI

The face-recognition screen is the most important custom screen.

Recommended structure:

```text
┌─────────────────────────────────────────────────────────────┐
│ Header                                                      │
├───────────────────────────────┬─────────────────────────────┤
│                               │ Recognition Status          │
│                               │                             │
│       Camera Preview          │ Detected Student            │
│                               │ Name                        │
│                               │ Student ID                  │
│                               │ Status                      │
│                               │ Time                        │
│                               │                             │
│                               │ [ Confirm / Register ]      │
└───────────────────────────────┴─────────────────────────────┘
```

Use the reference UI language:
- White cards
- Rounded corners
- Purple actions
- Muted secondary text
- Clear hierarchy

Do not put decorative UI over the camera feed unless it communicates recognition state.

---

# 33. Empty States

Use the same clean card language.

Example:

```text
        [simple illustration/icon]

       No attendance records

    There are no records for the
          selected date.

          [ Change Date ]
```

Keep empty states centered and concise.

---

# 34. Error / Success Feedback

Use compact toast/snackbar or inline feedback.

Success:
- Subtle green
- Clear message

Error:
- Subtle red
- Explain what went wrong

Example:

```text
✓ Attendance recorded successfully.
```

Avoid intrusive popups for routine successful actions.

---

# 35. Implementation Rules for Codex

1. Treat this file as the primary **visual implementation reference**.
2. Do not invent a different design system.
3. Reuse components instead of creating visually inconsistent duplicates.
4. Keep spacing, radius, typography and colors consistent.
5. Use the same icon family throughout the application.
6. Prefer local SVG assets when supplied.
7. Do not copy Courses-specific business logic.
8. Adapt the visual language to the attendance application's content.
9. Build responsive layouts rather than fixed screenshots.
10. Keep the UI simple enough for the scope of the university project.
11. Do not add unnecessary animations.
12. Do not replace the supplied visual direction with a generic admin template.
13. When a component is needed that is not explicitly documented here, derive it from the closest existing reference pattern rather than inventing a completely new style.

---

# 36. Visual Priority

When implementation decisions conflict, prioritize in this order:

```text
1. Usability
2. Consistency with this UI system
3. Clear information hierarchy
4. Accessibility
5. Responsive behavior
6. Decorative details
```

The goal is not pixel-perfect imitation of the Courses product.

The goal is a **coherent attendance application that feels like it belongs to the same design system.**
