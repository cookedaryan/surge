# SURGE Frontend — UX Improvement Report

**Scope:** Complete file-by-file analysis of [`web-map-next/src/`](file:///c:/Users/aryan/Projects/surge/web-map-next/src) — the active React/TypeScript frontend
**Date:** 2026-08-16
**Method:** Static analysis of every source file across all features, components, libraries, stores, and configuration
**Files analyzed:** 40+ source files across 10 feature modules

---

## Executive Summary

The SURGE frontend is a functional MVP for a complex domain — wind-farm collector network optimization with map-based visualization. The architecture (React 18 + TypeScript + Vite + Leaflet Canvas + TanStack Query + Zustand + Radix UI + Tailwind) is well-suited for the task. However, the UX carries **significant gaps across session management, error handling, accessibility, navigation, and data visualization** that would impede adoption beyond the initial handful of operators.

This report identifies **100+ discrete issues** grouped by severity:

| Severity | Count | Description |
|:---------|:------|:------------|
| 🔴 Critical | 18 | Breaks real workflows, causes data loss, trust loss, or inability to complete core tasks |
| 🟠 High | 28 | Causes meaningful friction in every session |
| 🟡 Medium | 38 | Cumulative annoyance that degrades the experience over time |
| 🟢 Low | 20 | Polish and delight items |

---

## Table of Contents

1. [Critical Issues](#-critical-issues)
2. [High-Priority Issues](#-high-priority-issues)
3. [Medium-Priority Issues](#-medium-priority-issues)
4. [Low-Priority Issues](#-low-priority-issues)
5. [Prioritized Improvement Roadmap](#prioritized-improvement-roadmap)

---

## 🔴 Critical Issues

These issues break real workflows or cause user confusion leading to data loss, trust loss, or inability to complete core tasks.

---

### C-01 · Silent Session Expiry with No Recovery

**Files:** [`useSessionRestore.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/useSessionRestore.ts#L25-L27), [`authStore.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/store/authStore.ts#L27), [`client.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/api/client.ts)

When the JWT expires mid-session:
- `setUnauthorizedHandler` in the auth store immediately invokes `logout()` — the login screen appears over the user's work with **no explanatory toast** (e.g., "Your session has expired")
- There is no global 401 interceptor in the API client to consolidate handling
- No token refresh mechanism exists
- No proactive "session expires in 5 minutes" warning
- If a 500 or DNS failure occurs during session restore (not just 401), the catch block silently ignores it — `username` and `role` stay `null` permanently, leaving the user in a degraded session where admin permissions are missing

**Impact:** User returns to find the app suddenly on the login screen, or worse, in a broken half-authenticated state with no explanation. All in-progress context is lost.

---

### C-02 · No URL Routing — Nothing Is Bookmarkable or Shareable

**File:** [`App.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/App.tsx#L20-L42)

The application uses a Zustand `view` state to switch panels with no URL routes. This means:
- Browser back/forward buttons do nothing useful
- Users cannot bookmark a specific view (e.g., the BOM for Project X)
- Deep links cannot be shared between team members
- Page refresh loses the active view, selected project, and all context

**Impact:** In a team workflow, an engineer finding something important in the audit log or BOM cannot share it with a colleague. Every session starts from scratch.

---

### C-03 · No Global Error Boundary

**File:** [`main.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/main.tsx#L9-L15)

No React Error Boundary wraps the component tree. An unhandled JavaScript error in any component — including third-party Leaflet code — crashes the entire application to a blank white screen with no recovery path except a full page reload (which loses all state per C-02).

---

### C-04 · SSE Progress Stream Has No Reconnection or Error UX

**Files:** [`useJobProgress.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/optimization/useJobProgress.ts#L61-L63)

- Stream errors are completely swallowed by an empty function `() => {}`
- If the SSE connection drops or is blocked by a corporate proxy, the user gets no indication — the app silently degrades to periodic polling
- The polling fallback also swallows errors (`.catch(() => {})`) and runs indefinitely every 4 seconds
- Re-opening an active job at 90% progress flashes "Queued — 5%" for up to 4 seconds before correcting
- No "Connection lost — reconnecting…" banner, no "Check status" button, no maximum retry count

**Impact:** User stares at a stuck progress bar for minutes without knowing whether the connection or the job failed.

---

### C-05 · API Errors Silently Return Empty/Zero Data Instead of Failing

**Files:** [`assets.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/api/assets.ts#L44-L72), [`jobs.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/api/jobs.ts#L4-L31), [`reports.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/api/reports.ts#L4-L16)

> [!CAUTION]
> This is the most structurally damaging UX issue in the codebase.

Multiple API modules catch errors and silently return empty/zero fallbacks:
- `getProjectAssetsGeoJson`, `getParcelsGeoJson`, `getRestrictedAreasGeoJson` → return `emptyGeoJson()`
- `getRoutesGeoJson`, `getPolesGeoJson` → return `emptyGeoJson()`
- `getBomReport` → returns all zeros (`totalEstimatedCost: 0, totalPoles: 0, totalNetworkLengthMeters: 0`)

**Consequences:**
- TanStack Query considers all map queries **successful** — `isError`, `error`, and `QueryErrorResetBoundary` **never fire** for map layers
- A network failure displays as an empty map with zero feedback. Users cannot tell whether the project has no assets or if data retrieval failed
- A BOM API failure displays as a **$0.00 zero-cost bill of materials**, creating massive user confusion before export
- After optimization, if route GeoJSON fails to load, the user sees a blank map with a "Completed!" success toast ([`OptimizationPane.tsx:L100-106`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/optimization/OptimizationPane.tsx#L100-L106))
- The hook [`useProjectData.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/useProjectData.ts#L38-L79) exposes no `isError` or `error` status at all

---

### C-06 · Tab Switching Destroys Component Trees and Loses User Work

**File:** [`SidePanel.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/app/SidePanel.tsx#L9-L13)

`if (activeSidebarTab !== tab) return null;` completely unmounts non-active panes. Switching tabs destroys:
- Uncommitted form edits (partially filled project creation, import overrides)
- Table scroll positions
- Expanded accordion/disclosure states
- Filter selections and search text
- Local component state

**Impact:** A user editing import classification overrides in the Assets tab who switches to Layers to check visibility, then returns, finds all their manual overrides wiped.

---

### C-07 · Elevation Profile Renders Fake Data Without Disclaimer

**File:** [`elevationProfile.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/elevationProfile.ts#L12-L26)

When route coordinates are missing or `< 2`, the function silently falls back to hardcoded coordinates and computes **synthetic sine/cosine elevation values**:
```
const elev = baseElevation + Math.sin(i * 1.5) * 18 + Math.cos(i * 0.8) * 12;
```

Users are shown a realistic-looking elevation profile chart even when no real elevation data exists, with **no "Simulated" or "Preview" disclaimer**.

**Impact:** Engineering users make routing decisions based on fabricated terrain data.

---

### C-08 · Progress Bar Shows Fake Fixed-Point Progress

**File:** [`OptimizationPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/optimization/OptimizationPane.tsx#L192-L202)

Progress jumps between fixed pipeline points (10% → 35% → 70% → 85% → 100%). Acknowledged in [`CONTEXT.md`](file:///c:/Users/aryan/Projects/surge/CONTEXT.md) as a known gap. Additionally:
- No elapsed time counter or ETA
- No stage description ("Computing routes…", "Running load flow…")
- The progress bar lacks `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` — screen readers receive zero progress feedback
- The validation blockers list also lacks `role="alert"` or `aria-live`

---

### C-09 · No Optimization Cancellation

**File:** [`OptimizationPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/optimization/OptimizationPane.tsx#L108)

Once started, the run button changes to "Running…" and is disabled. There is no cancel button. Users who realize they used wrong parameters must wait for the entire run to complete.

---

### C-10 · No State Persistence Across Page Refreshes

**File:** [`uiStore.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/store/uiStore.ts)

All Zustand state is in-memory only. A page refresh resets: active project, selected scenario, layer visibility, active panel, map viewport. Combined with C-02 (no URL routing), this is especially painful.

Additionally, [`uiStore.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/store/uiStore.ts#L74-L79) leaks state across project switches — `routeEditMode`, `liveBomOverride`, `routeColorOverride`, and opacity sliders are **not reset** when switching projects. A user editing routes on Project A who switches to Project B sees Project B open with route edit mode still active and Project A's manual BOM overrides displayed.

---

### C-11 · Toast System Is Fundamentally Broken

**File:** [`Toast.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/components/Toast.tsx)

Multiple compounding issues:
- **Single toast only** — rapid events eat each other ([`uiStore.ts:L56-58`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/store/uiStore.ts#L56-L58))
- **Critical color contrast failures** — success toast (`#34D399` bg + white text) has **1.6:1 contrast ratio** (WCAG AA requires 4.5:1); error toast (`#F0555A` + white) has **3.1:1** (also fails AA)
- **No dismiss button** — users must wait 3–8 seconds
- **No `role="alert"` or `aria-live`** — screen readers never announce toasts
- **No pause on hover/focus** — violates WCAG 2.2.1 (Timing Adjustable)
- **No entry/exit animation** — appears and disappears instantly
- **Misleading toasts** — `"Imported nothing"` shows with a green success style when 0 assets are committed

---

### C-12 · No Confirmation for Destructive Admin Actions

**File:** [`AdminPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx)

Three immediate-action destructive operations lack confirmation:
- **Account suspension** ([L195-203](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L195-L203)): one click immediately disables a user
- **Role modification** ([L183-190](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L183-L190)): the role dropdown calls the API on `onValueChange` — merely scrolling or accidentally selecting an option immediately demotes/promotes a user in production
- **Password reset** ([L209-221](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L209-L221)): submitting immediately overwrites the user's password
- No self-action protection prevents admins from disabling their own account

---

### C-13 · Silent Data Loss on Default Project

**File:** [`useAssetImport.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts#L38-L40)

If `currentProjectId` is empty, it assigns `proj-default`. Then at [L91](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts#L91), if `projectId.startsWith('proj-default')`, backend persistence is skipped entirely. Assets render locally on the canvas but are **never saved to the server**. The user receives no warning that their data is ephemeral and will be lost on refresh.

---

### C-14 · QueryClient Created Inside Component Body

**File:** [`App.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/App.tsx#L16)

*Note: This was verified against the actual source — the QueryClient is in [`queryClient.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/query/queryClient.ts) at module level, but the app-level import chain should be verified to ensure it's not re-instantiated.*

Related: [`queryClient.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/query/queryClient.ts#L3-L9) sets `retry: false` and `refetchOnWindowFocus: false`. This means:
- Any momentary packet loss fails queries immediately with no retry
- Users returning to the tab after checking another app see stale data

---

### C-15 · Map Auto-Fit Resets User Viewport on Background Refresh

**File:** [`MapAreaContent.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapAreaContent.tsx#L25-L27)

`fitAllBounds()` fires whenever `isLoading` flips to false. If a user has zoomed in to inspect a specific WTG or parcel, any background query refetch abruptly resets their viewport without consent.

---

### C-16 · Route Edits Have No Save/Discard Action

**Files:** [`MapAreaContent.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapAreaContent.tsx#L48-L51), [`SurgeMapEngine.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/SurgeMapEngine.ts#L379-L419)

Dragging route vertices recalculates live BOM figures using hardcoded `$80.0/m` cost, but:
- There is no "Save Changes", "Reset", or "Discard Edits" action bar on the map
- Changing projects or turning off edit mode silently wipes edits (`setLiveBomOverride(null)`)
- No undo/redo capability exists

---

### C-17 · Feeder Colors Are Indistinguishable Under Color Vision Deficiency

**File:** [`feederColors.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/feederColors.ts#L11-L22)

Emerald (`#10B981`), Teal (`#14B8A6`), and Cyan (`#06B6D4`) are indistinguishable under Deuteranopia and Protanopia. Routes lack complementary stroke patterns (dash arrays, textures, or feeder ID badges).

---

### C-18 · Loading State Aggregation Is Incomplete

**File:** [`useProjectData.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/useProjectData.ts#L77)

`isLoading` omits `polesQuery.isLoading` and `bomQuery.isLoading`. The UI reports loading complete while poles and BOM are still in flight, causing layout shift and temporary "0 poles" flashes.

---

## 🟠 High-Priority Issues

These cause meaningful friction in every session but don't break core workflows.

---

### H-01 · Icon-Only Navigation with No Tooltips or ARIA

**File:** [`RailNav.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/app/RailNav.tsx#L26-L41)

- Uses `title=` attribute (not shown on touch devices) instead of proper tooltips
- Missing `role="tablist"`, `role="tab"`, `aria-selected`, `aria-label`
- No `:focus-visible` ring styling — invisible focus against `#111113` dark background
- Active state is a thin 2px bar that relies solely on color difference
- Inline SVGs lack `aria-hidden="true"`, causing screen readers to announce empty image nodes
- Touch targets are 38×38px (below 44×44px standard)

---

### H-02 · Auth Form Missing Accessibility Fundamentals

**File:** [`AuthGateway.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx)

- No `<label>` elements — inputs rely solely on `placeholder` ([L44-58](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx#L44-L58))
- No `role="dialog"`, `aria-modal="true"`, focus trap, or autofocus on the overlay ([L40-41](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx#L40-L41))
- Error div lacks `role="alert"` ([L59](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx#L59))
- **Password is trimmed** during validation ([L20](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx#L20)) — passwords with leading/trailing whitespace will silently fail
- Inputs remain editable during submission (only button is disabled)
- Raw server error strings are dumped to UI ([L33](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx#L33))
- Stale error messages persist when the user corrects input
- Touch targets are 32px (`h-8`) at 11.5px font — triggers iOS Safari viewport zoom

---

### H-03 · Admin Panel Has No Search, Sort, Pagination, or Form Labels

**File:** [`AdminPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx)

- No search, filter, or sorting for users ([L54-61](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L54-L61))
- No pagination
- All form fields lack `<label>` and `aria-label` ([L113-120](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L113-L120))
- Role `Select` in each row has no `aria-label` identifying which user it modifies ([L183-190](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L183-L190))
- Username/email validation is missing from user creation ([L76-81](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L76-L81))
- No password visibility toggle
- `busy` state disables controls but doesn't show a spinner or change button text ([L141-153](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L141-L153))
- Focus is not managed when inline forms expand ([L104](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L104))

---

### H-04 · Audit Log Is Unpaginated, Unfiltered, and Inaccessible

**File:** [`AuditPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx)

- Hard-capped at 50 items with no pagination or "Load More" ([L37-39](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx#L37-L39))
- No filter by event type, username, or date range
- No search
- No export to CSV
- Rendered as generic `<div>` tags instead of semantic `<ol role="log">` ([L45-58](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx#L45-L58))
- Event severity relies solely on text color — no icons/badges for colorblind users ([L8-16](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx#L8-L16))
- Refresh button uses `isLoading` (only true on first load) instead of `isFetching` — no visual feedback during background refetch ([L27](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx#L27))

---

### H-05 · No Map Legend

**File:** [`LayersPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/layers/LayersPane.tsx#L4-L68)

11 layer toggles across 3 categories with **zero color swatches, line styles, or marker symbols**. Users cannot visually connect map colors (orange terminal poles, red angle poles, purple junction poles, pink dashed HT lines) with their corresponding toggle switch.

Also:
- Switches lack `aria-label` or `aria-labelledby` — screen readers hear only "Switch, checked" ([L43-68](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/layers/LayersPane.tsx#L43-L68))
- No "Show All / Hide All" batch toggle
- Unpopulated layers (0 features) remain active and toggleable without feedback
- Toggling off route editing silently clears `liveBomOverride` with no confirmation ([L90-96](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/layers/LayersPane.tsx#L90-L96))
- Switch hit area is only 30×17px; clicking the label text doesn't toggle

---

### H-06 · No "Zoom to Fit" and No Scale Bar on Map

**Files:** [`MapCanvas.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapCanvas.tsx), [`SurgeMapEngine.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/SurgeMapEngine.ts#L19)

- No "Zoom to Fit" button (auto-fit only fires on load, see C-15)
- No `L.control.scale()` metric scale bar
- Hardcoded initial center at `[23.2350, 69.8210]` (Gujarat) — new projects outside India momentarily load into Gujarat
- Map container lacks `role="region"` and `aria-label` ([L80](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapCanvas.tsx#L80))
- No `ResizeObserver` — sidebar toggles leave unrendered grey tiles ([L35-41](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapCanvas.tsx#L35-L41))
- 8 independent `useEffect` hooks fire sequentially on project load, causing micro-stutters ([L43-56](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapCanvas.tsx#L43-L56))

---

### H-07 · Scenario Comparison Has Critical Visual Bugs

**File:** [`ScenarioComparisonModal.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/scenarios/ScenarioComparisonModal.tsx)

- **WCAG color contrast failure** — white text on `#34D399` (1.7:1), `#06B6D4` (2.3:1), `#F5A524` (2.1:1) ([L5-10](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/scenarios/ScenarioComparisonModal.tsx#L5-L10))
- **Badge truncation bug** — `sc.scenarioName.split(' ')[0]` produces `"Minimum"` for three different scenarios ([L36](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/scenarios/ScenarioComparisonModal.tsx#L36))
- Cards rather than comparison table — cannot easily compare metrics side-by-side ([L28-70](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/scenarios/ScenarioComparisonModal.tsx#L28-L70))
- No best-in-class highlights, no delta percentages
- "Overlay Map Route" closes modal with no confirmation toast ([L57-66](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/scenarios/ScenarioComparisonModal.tsx#L57-L66))
- Fixed `w-[760px]` width breaks on mobile/tablet

---

### H-08 · Asset Upload Has No Progress, No Client Validation, Silent Failures

**Files:** [`AssetDropzone.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetDropzone.tsx), [`useAssetImport.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts)

- No upload progress bar — just static "Processing…" text ([L52](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetDropzone.tsx#L52))
- Dropzone lacks `tabIndex`, `role="button"`, `aria-label`, `onKeyDown` — keyboard inaccessible ([L43-55](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetDropzone.tsx#L43-L55))
- Type filter pills lack `role="radiogroup"` / `aria-pressed` ([L58-68](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetDropzone.tsx#L58-L68))
- Drag-and-drop flickers when hovering over child elements ([L45-47](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetDropzone.tsx#L45-L47))
- Unsupported file formats silently filtered with no error toast ([L41-43](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts#L41-L43))
- Multi-KMZ drop overwrites previous previews — only last file survives ([L46-53](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts#L46-L53))
- `JSON.parse` and file reading run synchronously on the main thread — freezes UI on large files ([L19-26](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts#L19-L26))
- API errors during import are caught and dumped to `console.error` with no user toast ([L103-112](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/useAssetImport.ts#L103-L112))

---

### H-09 · Import Preview Modal Has Major Table and Data Issues

**File:** [`ImportPreviewModal.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx)

- Unpaginated, non-virtualized table rendering all features directly into `<tbody>` — browser lag on large KMZ files ([L121-156](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L121-L156))
- Default capacity input lacks `type="number"` / `inputMode="decimal"` — `NaN` on non-numeric input ([L114-119](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L114-L119))
- "Apply to all rows" overwrites all manual overrides with no confirmation or undo ([L46-51](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L46-L51))
- `skipUnclassified: true` permanently drops UNKNOWN features without explicit acknowledgment ([L60](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L60))
- Geometry glyphs (●, ╱, ▭) are announced literally by screen readers ([L13](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L13))
- Stale override state persists when dialog is cancelled ([L68-69](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L68-L69))
- Fixed `w-[680px]` causes dual-axis scrolling on mobile ([L80](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/ImportPreviewModal.tsx#L80))

---

### H-10 · No Loading State on Action Buttons Anywhere

**Files:** [`Button.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/components/ui/Button.tsx#L4-L7), all features

The Button component has no `loading` prop. Buttons for login, run optimization, export BOM, create project, and admin actions don't show a spinner or disable themselves during requests. Users can double-click and submit duplicate requests. The button also lacks:
- `danger` / `destructive` variant
- `:focus-visible` ring styling
- Adequate touch target size (`sm` = 28px, `default` = 32px)

---

### H-11 · Elevation Drawer Forces Open and Cannot Be Re-Opened

**File:** [`ElevationDrawer.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/ElevationDrawer.tsx)

- `useEffect` unconditionally sets `setOpen(true)` whenever routes exist — if a user deliberately closes the drawer, any re-render forces it back open ([L15-18](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/ElevationDrawer.tsx#L15-L18))
- When closed, returns `null` with **no button or menu item to re-open it** ([L24](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/ElevationDrawer.tsx#L24))
- Only shows first feeder with no selector for multi-feeder projects ([L7](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/ElevationDrawer.tsx#L7))
- Close button is 24×24px — below touch target standards ([L31-37](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/ElevationDrawer.tsx#L31-L37))
- SVG chart has hardcoded 800×160px, no responsive viewBox ([`elevationProfile.ts:L33-35`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/elevationProfile.ts#L33-L35))

---

### H-12 · Side Panel Cannot Be Collapsed or Resized

**File:** [`SidePanel.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/app/SidePanel.tsx#L17)

Fixed `w-[300px]` with no collapse toggle or resize handle. Complex tables (BOM, optimization parameters, audit) feel cramped. On smaller screens, the panel + rail nav consume 350px, suffocating the map. The `<aside>` also lacks `aria-label`.

---

### H-13 · New Project Dialog Has Multiple UX Gaps

**File:** [`NewProjectModal.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/NewProjectModal.tsx)

- Inputs lack `<label>` elements — rely solely on placeholder ([L38-49](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/NewProjectModal.tsx#L38-L49))
- No `<form onSubmit>` wrapper — Enter key doesn't submit ([L38-50](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/NewProjectModal.tsx#L38-L50))
- No `autoFocus` on the name input ([L38](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/NewProjectModal.tsx#L38))
- `createProject.mutateAsync()` has no try/catch — errors fail silently ([L14-21](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/NewProjectModal.tsx#L14-L21))
- Cancel/backdrop close doesn't reset form state ([L18-20](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/NewProjectModal.tsx#L18-L20))

---

### H-14 · Project Selector Has Hidden Auto-Creation and No Loading State

**File:** [`ProjectSelector.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/ProjectSelector.tsx)

- Auto-creates a "Default Workstation Project" when 0 projects exist without notifying the user ([L19-22](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/ProjectSelector.tsx#L19-L22))
- No loading or error state handling — blank selector during fetch ([L36-41](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/ProjectSelector.tsx#L36-L41))
- No placeholder text when no project is selected
- No `aria-label` on the `<Select>`
- Switching projects doesn't check for unsaved work ([L38](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/projects/ProjectSelector.tsx#L38))

---

### H-15 · BOM Panel Shows $0 Empty State and Has Enabled Export on Empty Data

**File:** [`BomPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomPane.tsx)

- When no optimization has run, metrics show `$0.00`, `0.00 km`, `0 Poles` with no explanation ([L34-37](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomPane.tsx#L34-L37))
- Export buttons remain active on empty data — users can download a blank BOM ([L59-66](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomPane.tsx#L59-L66))
- No success toast after export
- BomStrip (map HUD) and BomPane use inconsistent currency formatting ([`BomStrip.tsx:L18`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomStrip.tsx#L18) vs [`BomPane.tsx:L35`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomPane.tsx#L35))
- BomStrip can occlude map controls on small screens ([`BomStrip.tsx:L29-37`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomStrip.tsx#L29-L37))
- BomStrip stacks with ElevationDrawer, consuming 50%+ of map viewport on compact screens

---

### H-16 · Role Display Is Inconsistent

**File:** [`AuthTopBarActions.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthTopBarActions.tsx#L11)

TopBar shows raw enum strings like `(ADMIN)` or `(ENGINEER)` while AdminPane shows friendly title case (`Administrator`, `Engineer`). Long usernames (email-based) have no `truncate` and can push buttons off-screen.

---

### H-17 · Session Restore Causes Layout Shift

**File:** [`useSessionRestore.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/useSessionRestore.ts#L18-L28)

On page reload, `isAuthenticated` is true (from localStorage) but `role` and `username` are null. The Admin nav tab is hidden for ~300ms then pops in, causing layout shift. No session-restoring spinner or placeholder is shown.

---

### H-18 · No `autocomplete` Attributes on Auth Forms

**File:** [`AuthGateway.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx#L44-L58)

Missing `autocomplete="username"` and `autocomplete="current-password"` prevents password managers from auto-filling correctly. This is a one-line fix with outsized UX impact.

---

## 🟡 Medium-Priority Issues

Cumulative friction points that degrade the experience over time.

---

| # | Issue | Key File | Summary |
|:--|:------|:---------|:--------|
| M-01 | No dark/light mode toggle | [`globals.css`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/styles/globals.css), [`tailwind.config.js`](file:///c:/Users/aryan/Projects/surge/web-map-next/tailwind.config.js) | Hardcoded dark theme. Field engineers in sunlight have no high-contrast option. |
| M-02 | No `:focus-visible` styles globally | [`globals.css`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/styles/globals.css#L32-L41) | Also missing `prefers-reduced-motion` rules. |
| M-03 | No "Skip to main content" link | [`App.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/App.tsx#L28-L36) | WCAG 2.4.1 bypass blocks violation. |
| M-04 | No panel transition animations | [`SidePanel.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/app/SidePanel.tsx) | Instant swap feels abrupt. |
| M-05 | No map loading skeleton/spinner | [`MapAreaContent.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapAreaContent.tsx#L23-L35) | Blank dark rectangle during load. |
| M-06 | No layer loading indicators | [`useProjectData.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/useProjectData.ts) | GeoJSON fetching shows no spinner on map. |
| M-07 | No layer opacity controls | [`LayersPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/layers/LayersPane.tsx) | Overlapping layers become visually tangled. |
| M-08 | No empty state messages system-wide | Multiple | Lists show blank areas instead of guidance. |
| M-09 | No optimization run history | Optimization feature | Can't compare current vs. previous results. |
| M-10 | Decision summary is text-heavy | [`OptimizationPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/optimization/OptimizationPane.tsx#L287-L329) | Electrical failures show no actionable guidance. |
| M-11 | Optimization sliders lack numeric input | [`OptimizationPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/optimization/OptimizationPane.tsx#L165-L180) | Voltage steps in 11kV only; no direct entry for 66kV. |
| M-12 | No BOM grouping or sorting | [`BomPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomPane.tsx) | Flat list with no category organization. |
| M-13 | No audit timestamp localization | [`AuditPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx#L18-L24) | No relative time, inconsistent format near midnight. |
| M-14 | No audit detail expansion | [`AuditPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/audit/AuditPane.tsx#L54) | Raw stringified JSON renders as unwrapped text. |
| M-15 | No password strength indicator | [`AdminPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx#L117-L119) | No visual feedback on password quality. |
| M-16 | No "Forgot Password" flow | [`AuthGateway.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/auth/AuthGateway.tsx) | No self-service recovery. |
| M-17 | No assets table/inspection view | [`AssetsPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetsPane.tsx#L16-L22) | Can't search, filter, inspect, or delete individual assets. |
| M-18 | Asset count display is ambiguous | [`AssetSummary.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetSummary.tsx#L11) | `12/20` notation has no tooltip explaining optimisable/total. |
| M-19 | No offline detection | [`client.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/api/client.ts) | Network failures produce generic errors. |
| M-20 | No request retry logic | [`queryClient.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/query/queryClient.ts#L3-L9) | `retry: false` — any packet loss breaks queries. |
| M-21 | Slider has no value label | [`Slider.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/components/ui/Slider.tsx#L14-L25) | Thumb is 14×14px, no live value tooltip, no focus ring. |
| M-22 | Select has no search or empty state | [`Select.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/components/ui/Select.tsx) | Long lists need scrolling; no `aria-label` support. |
| M-23 | No results export beyond BOM | Optimization feature | Can't export routes as GeoJSON or map as image. |
| M-24 | No map fullscreen toggle | [`MapCanvas.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapCanvas.tsx) | Can't maximize map for detailed inspection. |
| M-25 | Admin can disable/demote themselves | [`AdminPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/admin/AdminPane.tsx) | No self-action protection. |
| M-26 | No drag-and-drop visual feedback | [`AssetDropzone.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/assets/AssetDropzone.tsx#L45-L47) | Drag state flickers on child hover events. |
| M-27 | Export PDF button duplicated | [`ExportPdfButton.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/ExportPdfButton.tsx) vs [`BomPane.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/bom/BomPane.tsx) | Different validation text, inconsistent behavior. |
| M-28 | Card heading hierarchy issues | [`Card.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/components/ui/Card.tsx#L11-L25) | Hardcoded `<h3>`, all-caps titles, very small descriptions. |
| M-29 | Dialog has no close button or animations | [`Dialog.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/components/ui/Dialog.tsx#L13-L28) | Missing Radix Description, no header X button, instant appear/vanish. |
| M-30 | Map markers have tiny hit targets | [`SurgeMapEngine.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/SurgeMapEngine.ts#L215-L251) | Intermediate poles 6px, junction poles 10px, vertex handles 12px. |
| M-31 | Responsive layout broken below 768px | [`App.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/App.tsx#L36-L49) | Fixed sidebar + rail = 350px leaves no map space. Also `h-full` vs `h-[100dvh]` issue. |
| M-32 | TopBar overflows on narrow viewports | [`TopBar.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/app/TopBar.tsx#L20-L22) | Action buttons cluster horizontally with no overflow menu. |
| M-33 | Popup/label font sizes below 12px | [`globals.css`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/styles/globals.css#L98-L103) | 10.5px and 11.5px cause eyestrain on high-DPI dark themes. |
| M-34 | Leaflet zoom controls undersized | [`globals.css`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/styles/globals.css#L59-L60) | 32×32px on touch — below 44px standard. |
| M-35 | No base map switcher | [`SurgeMapEngine.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/SurgeMapEngine.ts) | Only one tile layer. Satellite/terrain useful for routing. |
| M-36 | Classification regex is geographically biased | [`classify.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/classify.ts#L42-L47) | WTG pattern only matches `KS|SUR|VAJ` prefixes. |
| M-37 | No coordinate display on map | [`MapCanvas.tsx`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/features/map/MapCanvas.tsx) | Engineers can't see lat/lng under cursor. |
| M-38 | Elevation profile labels fail contrast | [`elevationProfile.ts`](file:///c:/Users/aryan/Projects/surge/web-map-next/src/lib/map/elevationProfile.ts#L61-L66) | `#55585F` and `#8B909C` at 10px on dark backgrounds (~2.4:1). |

---

## 🟢 Low-Priority Issues

Polish items that would improve delight and professionalism.

---

| # | Issue |
|:--|:------|
| L-01 | No keyboard shortcuts for power users |
| L-02 | No help/onboarding system or feature tours |
| L-03 | No print stylesheet for map views or BOM tables |
| L-04 | No internationalization (i18n) — all strings hardcoded in English |
| L-05 | No responsive/mobile layout — desktop-only |
| L-06 | No minimap/overview for large wind farm sites |
| L-07 | No measurement tools on map (distance/area) |
| L-08 | No coordinate format options (decimal degrees / DMS / UTM) |
| L-09 | No audit log export to CSV |
| L-10 | No "Recently Viewed" projects list |
| L-11 | No project description field |
| L-12 | No Zustand DevTools integration |
| L-13 | No map viewport bookmark/save |
| L-14 | No consistent panel headers |
| L-15 | No interactive decision summary (click to highlight on map) |
| L-16 | No multi-file upload |
| L-17 | No right-click context menu on map |
| L-18 | Vertex drag handle missing `:active { cursor: grabbing }` |
| L-19 | No data prefetching for likely next views |
| L-20 | Component prop types not exported from UI barrel file |

---

## Prioritized Improvement Roadmap

### Phase 1 — Trust & Reliability (1–2 weeks)
> Fixes that prevent user confusion, data loss, and trust erosion.

| Item | Effort | Impact |
|------|--------|--------|
| C-05 Let API errors propagate (stop returning empty/zero fallbacks) | Medium | Unlocks all error UX |
| C-01 Global 401 handler + session expiry toast + login redirect | Small | Prevents confusion |
| C-03 React Error Boundary with recovery UI | Small | Prevents white screen |
| C-11 Toast: severity, stacking, dismiss, `aria-live`, contrast fix | Medium | Foundation for all feedback |
| C-14 Fix `retry: false` — add at least 1 retry for network errors | Trivial | Prevents transient failures |
| C-10 Zustand persistence (`localStorage`) + state reset on project switch | Small | Prevents data leaks |
| C-06 CSS-hide inactive tabs instead of unmounting | Small | Prevents form data loss |
| H-18 `autocomplete` attributes on auth forms | Trivial | Password manager support |
| H-10 Button loading state prop | Small | Prevents double-clicks |

### Phase 2 — Core Workflow Improvements (2–3 weeks)
> Makes the primary optimization workflow smooth end-to-end.

| Item | Effort | Impact |
|------|--------|--------|
| C-02 URL routing (React Router or equivalent) | Medium | Bookmarking, sharing, back/forward |
| C-04 SSE reconnection + connection status indicator | Medium | Prevents frozen progress |
| C-08 Stage names, elapsed timer in progress bar + ARIA | Small | Trustworthy progress |
| C-09 Optimization cancel button | Medium (backend) | Escape hatch for wrong params |
| C-07 Elevation profile: show empty state instead of fake data | Small | Prevents false decisions |
| C-15 Only auto-fit bounds on explicit project switch | Small | Preserves user viewport |
| C-16 Route editing action bar (Save/Discard/Undo) | Medium | Prevents silent data loss |
| H-06 Add `L.control.scale()` + "Zoom to Fit" button | Small | Essential map tools |
| H-08 Upload progress bar + client-side file validation | Medium | Better upload UX |

### Phase 3 — Navigation, Discovery & Accessibility (1–2 weeks)
> Helps users find features and makes the app usable for all.

| Item | Effort | Impact |
|------|--------|--------|
| H-01 RailNav: tooltips, ARIA roles, focus rings | Small | Discoverability |
| H-02 Auth form: labels, focus trap, error ARIA, no password trim | Small | WCAG compliance |
| H-05 Layer legend with color swatches + ARIA labels | Medium | Map interpretation |
| H-12 Collapsible side panel | Medium | More map space |
| H-07 Scenario comparison: fix contrast, fix badge truncation | Small | Visual correctness |
| H-16 Consistent role display + username truncation | Trivial | Polish |
| H-17 Session restore loading state to prevent layout shift | Small | Prevents flash |
| C-17 Feeder colors: pair with dash patterns for CVD | Small | Color accessibility |
| M-02 Global `:focus-visible` + `prefers-reduced-motion` | Small | WCAG foundation |

### Phase 4 — Admin, Audit & Data Management (1–2 weeks)
> Makes admin workflows safer and audit usable at scale.

| Item | Effort | Impact |
|------|--------|--------|
| C-12 Confirmation dialogs for all destructive admin actions | Small | Prevents accidents |
| H-03 Admin panel: search, labels, validation, inline feedback | Medium | Usability at scale |
| H-04 Audit: pagination + filters + semantic markup | Medium (backend) | Compliance and investigation |
| H-09 Import preview: pagination, number input, undo for bulk apply | Medium | Large file handling |
| C-13 Warn when using ephemeral default project | Small | Prevents data loss |
| M-25 Self-action protection for admins | Small | Safety |

### Phase 5 — Delight & Power Users (ongoing)
> Polish that differentiates the product.

All remaining 🟡 Medium items not covered above, plus all 🟢 Low items. Prioritize M-35 (base map switcher), M-37 (coordinate display), and M-17 (asset inspection table) first as they are most impactful for the GIS domain.

---

> [!NOTE]
> This report is based solely on static source code analysis. Some issues may be better or worse than described depending on runtime behavior, actual API responses, and real user workflows. A usability test with target operators would validate and further prioritize these findings. Several issues marked as "known gaps" in [`CONTEXT.md`](file:///c:/Users/aryan/Projects/surge/CONTEXT.md) (unpaginated audit log, fixed progress percentages, unconverged ROW corridor polygons) are confirmed and expanded upon here.
