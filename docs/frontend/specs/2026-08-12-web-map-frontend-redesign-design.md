# SURGE Web Map Frontend Redesign — Design Spec

Date: 2026-08-12
Status: Approved for planning

## 1. Problem & Goals

`web-map` (the GIS collector/evacuation routing UI) is a vanilla JS/CSS/HTML app built with Vite and Leaflet. It works, but:

- Visually it uses a heavy dark "glassmorphism" theme (navy backgrounds, blur, glow shadows, two competing typefaces, multiple loud accent colors) that reads as decorative rather than precise, for what is fundamentally an engineering tool.
- The sidebar is a fixed 380px width regardless of content, and card/metric spacing is loose relative to how data-dense the tool actually is.
- The codebase concentrates almost all UI logic in one 1000-line `src/app.js`, one 1450-line `src/index.css`, and a 519-line `index.html` with every modal inlined — hard to navigate, hard to change safely, no component boundaries.

Goals:
- A new visual identity — a "technical dashboard" look: neutral near-black/zinc surfaces, hairline borders instead of blur/glow, one restrained accent color, tighter data-dense typography, monospace numerals for engineering readouts.
- A maintainable component architecture that replaces the monolithic files with small, independently understandable units.
- Full feature parity with the current app — nothing regresses.
- No backend changes — same REST/JWT contract against the Spring Boot API.

Non-goals:
- No changes to `backend-java`, `optimisation-python`, or the database.
- No new product features — this is a redesign/migration, not a feature project.
- No automated test suite investment (see §7) — this pass is verified by manual QA.

## 2. Stack & Architecture

- **React 18 + TypeScript + Vite**, scaffolded fresh in `web-map-next/` (sibling to `web-map/`), inside the existing repo.
- **Tailwind CSS + shadcn/ui** (Radix primitives) for the component layer — utility CSS plus accessible, ownable component code, themed to the tokens in §3.
- **TanStack Query** for all server state (projects, jobs, BOM, audit logs) — replaces the hand-rolled `fetchJson` calls and manual polling in `src/api.js`; gives caching, retries, and loading/error state out of the box.
- **Zustand** for small pieces of client-only UI state (active sidebar tab, layer visibility, drawer open/closed) — avoids prop-drilling between the map and sidebar without pulling in Redux.
- **Leaflet stays vanilla, wrapped, not ported to react-leaflet.** `SurgeMapEngine` (`src/map.js`, 534 lines) contains bespoke drawing, routing-line, and edit-mode logic that would be high-risk to re-express declaratively. It's kept as-is and wrapped in one `<MapCanvas>` component that owns a ref + `useEffect` lifecycle and exposes a small callback/event interface to the rest of the React tree.
- `vite.config.ts` adds a `server.proxy` entry for `/api` → the Spring Boot backend (port 8080), mirroring what `nginx.conf` does today in production.
- `classify.js` (asset-classification rules that must mirror the Java backend's `AssetClassificationRules`) is imported unchanged — it's framework-agnostic logic, not UI.

## 3. Design System — "Technical Dashboard" Tokens

Approved via mockup (see project conversation, 2026-08-12). Token values:

**Dark (default):**
| Token | Value | Use |
|---|---|---|
| `--bg` | `#0A0A0C` | app background |
| `--panel` | `#111113` | header/sidebar surface |
| `--surface` | `#17171B` | cards |
| `--surface-2` | `#1C1C20` | nested/inset surfaces (inputs, metric boxes) |
| `--border` | `rgba(255,255,255,0.09)` | hairline dividers |
| `--border-strong` | `rgba(255,255,255,0.17)` | interactive element borders |
| `--text` / `--text-muted` / `--text-faint` | `#F2F3F5` / `#8B909C` / `#55585F` | text hierarchy |
| `--accent` | `#4E8CFF` | primary actions, active/focus states — used sparingly |
| `--success` / `--warning` / `--danger` | `#34D399` / `#F5A524` / `#F0555A` | semantic status only, never decorative |

**Light (optional, togglable later):** inverted scale — `#EEF0F3` bg, `#FFFFFF` panels/cards, `#2F6FED` accent (deepened for contrast), equivalent semantic colors deepened for AA contrast on white. Full values in the approved mockup file.

**Typography:** single UI family for everything (heading and body) at system-font-stack fidelity in the mockup (`-apple-system, "Segoe UI", "Inter", sans-serif`) — production build self-hosts Inter (woff2, not Google Fonts CDN) to avoid FOUT/CDN dependency. A monospace face (`ui-monospace` stack, self-hosted JetBrains Mono in production) is used specifically for numeric engineering readouts (MW, kV, km, $, counts) via `font-variant-numeric: tabular-nums`, reinforcing the instrument-panel feel. Base body size 13.5px, tightened from the current 16px for data density.

**Iconography:** keep Font Awesome (already integrated); standardize sizing (14px inline, 17px nav-rail) and weight usage across the app.

**Layout shape:** top bar (52px) → icon-only vertical rail (50px, tab switcher) + content side-panel (300px, was 380px) → flexible map area. This replaces the current horizontal tab-button row + fixed-width sidebar. Floating map overlays (legend, BOM strip, elevation drawer) become hairline-bordered cards, not blurred glass.

**Elevation & motion:** shadows replace blur/glow (`0 1px 2px rgba(0,0,0,.4), 0 12px 32px rgba(0,0,0,.45)` in dark); transitions kept short (120–150ms) and functional, not decorative.

Both dark and light themes must be implemented via CSS custom properties (`:root`, `@media (prefers-color-scheme: dark)`, `:root[data-theme="dark|light"]` overrides) — dark is the shipped default; a theme toggle is not required in this pass but the token structure must support adding one later without rework.

## 4. Application Structure

```
web-map-next/
  src/
    main.tsx, App.tsx
    app/                    routing shell, layout (TopBar, RailNav, SidePanel, MapArea)
    features/
      auth/                 gateway overlay + login modal
      projects/             project selector, new-project modal
      assets/                ingestion dropzone, import-preview modal, asset summary
      optimization/          scenario form, job progress
      layers/                 layer toggles, opacity sliders, route-edit toggle
      map/                    MapCanvas (wraps SurgeMapEngine), legend, elevation drawer
      bom/                     BOM summary, CSV/PDF export
      audit/                   audit log list
      scenarios/               scenario comparison modal
    components/ui/          shadcn primitives (button, card, dialog, tabs, slider, switch, select…)
    lib/api/                 typed API client modules, one per resource (replaces api.js)
    lib/store/               zustand slices (UI state only — no server data)
    lib/query/                TanStack Query hooks, one set per resource
    styles/                   Tailwind config + design tokens (globals.css)
```

Each `features/*` folder owns its components, its Query hooks, and any feature-local state. The folder boundaries map 1:1 onto the current sidebar tabs (Assets/Optimization/Layers/BOM/Audit) plus the map and modals, so migration work has a direct old-file → new-folder mapping and no feature's logic is spread across unrelated files.

## 5. Migration Plan

Built alongside the current app in a new `web-map-next/` project — `web-map/` keeps running/deploying unchanged until cutover, so there's no partially-broken intermediate state.

1. **Scaffold** — Vite+React+TS+Tailwind+shadcn in `web-map-next/`; apply the approved design tokens; add the `/api` dev proxy; build the static app shell (TopBar/RailNav/SidePanel/MapArea) with no real data wired up yet.
2. **Map integration** — wrap `SurgeMapEngine` in `MapCanvas`; port `map.js` with minimal changes; verify markers, feeder routes, legend, and route-line editing all still work against real data.
3. **Feature-by-feature port** (each lands independently, app stays exercisable throughout):
   - Auth + Projects (gateway overlay, login modal, project selector, new-project modal)
   - Assets (dropzone, import-preview modal + table, asset summary metrics — reuses `classify.js` unchanged)
   - Optimization (scenario form, sliders, job-progress polling via TanStack Query)
   - Layers (visibility toggles, opacity sliders, route-edit toggle)
   - BOM (summary table, CSV export, PDF export)
   - Audit log
   - Scenario comparison modal
4. **API layer rewrite** — `src/api.js` becomes typed `lib/api/*` modules plus `lib/query/*` hooks; same endpoints, same JWT-in-`localStorage` auth handling; no backend contract changes.
5. **Parity QA pass** — every flow above checked by hand against current `web-map`, side by side.
6. **Cutover** — repoint `Dockerfile`/`nginx.conf` at the `web-map-next` build output, retire/archive the old `web-map` app, update root `README.md`'s Quick Start section.

## 6. Data Flow & Error Handling

- All server reads/writes go through TanStack Query hooks in `lib/query/`; loading and error states are handled once per hook and consumed by components via the hook's returned state (no more manual `.hidden` class toggling for spinners/errors).
- JWT stays in `localStorage` under the same key (`surge_jwt_token`) so no re-login is forced at cutover; the typed API client attaches it the same way `fetchJson` does today.
- Long-running optimization jobs keep the current polling model, moved into a `useOptimizationJob` Query hook with `refetchInterval`, replacing the manual `setInterval`-driven progress bar logic in `app.js`.
- Client-only UI state (active tab, layer toggles, drawer open/closed, selected import rows) lives in Zustand — never mixed into Query cache.

## 7. Testing & Verification

Manual QA only for this migration pass (no new automated suite) — this is a UI/architecture migration of existing behavior, not new business logic, and the current app has no test suite to extend. Each feature in §5 step 3 is verified by hand against `web-map` before being considered done: same inputs (sample GeoJSON/KMZ files, same optimization parameters) should produce the same on-screen results and exports (CSV/PDF byte-for-byte where feasible, visually equivalent otherwise).
