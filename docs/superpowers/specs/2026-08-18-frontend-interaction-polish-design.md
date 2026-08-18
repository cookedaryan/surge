# SURGE Frontend — Interaction & Motion Polish

Date: 2026-08-18
Status: Approved for implementation
Supersedes nothing. Successor to [`2026-08-12-web-map-frontend-redesign-design.md`](./2026-08-12-web-map-frontend-redesign-design.md).

## 1. Problem & Goals

The 2026-08-12 redesign delivered `web-map-next` and its "technical dashboard" identity. That
identity is right and is not being replaced. What it never received is an interaction layer.

Concretely, the entire application contains two transitions: `transition-colors` on `Button`, and a
width transition on the optimisation progress bar. Everything else changes state instantly.
Radix dialogs appear and vanish with no enter or exit. `Pane` unmounts the whole component tree on
tab switch, discarding whatever the operator had typed. `Toast` pops into existence and disappears.
The sign-in screen is a 320px form on a black scrim. Nothing anywhere tells the operator that the
interface heard them.

Goals:

- A motion layer that explains state change rather than decorating it — every animation must be
  attributable to something that happened.
- A token layer with the scales the current flat token set lacks (accent ramp, radii, shadow,
  duration, focus ring), so components stop inventing their own values.
- `prefers-reduced-motion` honoured globally, by construction rather than per-component.
- A sign-in screen, a shell and a results surface that are pleasant to use for a full working day.
- Accessibility gaps that sit in the same files get closed while those files are open.

Non-goals:

- No backend, optimiser or database changes.
- No new product features. No new data is fetched and no new figure is computed or displayed that
  the API does not already return.
- No light theme in this pass. The 2026-08-12 spec requires the token structure to permit one
  later; this pass preserves that property and does not exercise it.
- No URL routing. Report issue C-02 stays open.

## 2. Constraints

These are load-bearing and were established by reading the code, not assumed.

**Contrast ratios in `globals.css` are fixed.** The comment block recording `--text-faint` at
13.7:1 / 6.7:1 / 4.8:1 documents a deliberate WCAG remediation — the value was previously `#55585F`
at 2.4:1. New tokens are added around these; the three text tiers are not re-derived.

**`CardTitle`'s `uppercase` is load-bearing.** Playwright's `getByText` matches rendered text, and
`text-transform` affects it. `workstation.spec.ts` asserts on `'WHY THIS ROUTE'`,
`'PROJECT ASSET SUMMARY'`, `'NETWORK LENGTH'`, `'POLES'` and `'USER ADMINISTRATION'` while the
sources read "Why This Route" etc. Removing `text-transform: uppercase` breaks the suite.

**The sign-in form's test surface is fixed.** `workstation.spec.ts` binds via
`page.locator('form', { hasText: 'Sign in to SURGE' })` and `getByPlaceholder('Username'|'Password')`.
The redesigned screen keeps the `<form>` element, that heading text, and both placeholders.

**`queryClient` sets `refetchOnWindowFocus: false`, `retry: false`, and no refetch interval.** This
is what makes keeping panes mounted affordable — a hidden pane issues no background traffic.

**`showToast(message, variant)` has ~15 call sites.** The signature does not change.

**Progress percent is real.** `useJobProgress` receives `progressPercent` from the server's SSE
stream. The UI may smooth it and time it, but must not invent stages the server did not report.

## 3. Token Layer

`src/styles/globals.css` `:root` gains scales; `tailwind.config.js` exposes them.

| Group | Tokens | Rationale |
|---|---|---|
| Surface | `--surface-3` | completes bg → panel → surface → surface-2 → surface-3 for hover/elevated |
| Accent | `--accent-100/200/400/500/600` | hover and pressed become real values instead of `brightness-110` |
| Radius | `--r-sm 6px`, `--r-md 8px`, `--r-lg 12px`, `--r-xl 16px` | every component currently hardcodes its own |
| Shadow | `--shadow-1/2/3` | rest, floating, dialog |
| Motion | `--dur-fast 120ms`, `--dur 180ms`, `--dur-slow 260ms`, `--ease-out`, `--ease-spring` | within the 120–150ms functional band the 2026-08-12 spec set, extended only for surfaces that travel distance |
| Focus | `--ring`, `--ring-offset` | one global `:focus-visible` rule replaces nothing, because there is none today |

Typography is named, not resized. Tailwind `fontSize` gains `xs`/`sm`/`base` bound to the existing
10.5 / 11.5 / 13.5px. The ~60 `text-[11.5px]` literals become `text-sm` at identical rendered size.
This is a naming change with no visual delta.

**Reduced motion is one rule.** Because every animation reads `--dur-*`, a single
`@media (prefers-reduced-motion: reduce)` block setting those tokens to `0.01ms` disables the whole
motion layer. Components do not each test the preference.

## 4. Motion Primitives

Keyframes in `globals.css`, exposed as Tailwind `animation` entries:
`fade-in`, `fade-out`, `scale-in`, `slide-up`, `slide-in-right`, `shimmer`, `pulse-ring`.

Radix components animate from their `data-state="open" | "closed"` attributes so exit animations
run to completion instead of the content being torn out on close.

## 5. Components

Rebuilt:

- **Button** — `loading` prop rendering a spinner while preserving button width (report H-10);
  `ghost` and `subtle` variants; `active:scale-[0.98]`; focus-visible ring.
- **Card** — optional `interactive` hover-lift. `CardTitle` keeps `uppercase` (§2) and gains an
  icon slot.
- **Dialog** — overlay fade, content scale-in, animated close.
- **Toast** — `uiStore.toast` becomes `toasts: Toast[]`. Stacking, per-variant icon, manual
  dismiss, `aria-live="polite"` with `role="alert"` for errors (report C-11). `showToast`'s
  signature is unchanged (§2).

New:

- **Skeleton** — shimmer placeholder for asset counts, BOM, audit, admin, project selector.
- **Spinner** — inline; renders a static dot under reduced motion.
- **Tooltip** — Radix. Adds `@radix-ui/react-tooltip`, the pass's only new dependency.
- **StatTile** — the bordered metric box currently duplicated inline in `OptimizationPane`,
  `BomStrip` and `AssetSummary`.
- **AnimatedNumber** — count-up; no-ops under reduced motion and renders the final value.
- **Sheet** — Radix Dialog-based right-hand drawer, for §8.

## 6. Sign-in

Replaces the 320px form on `bg-black/85` with a full-viewport composition: an ambient SVG backdrop
(faint grid, turbine nodes, feeder lines that draw once via `stroke-dashoffset`) beside the sign-in
card. The card fades and rises 12px; fields stagger at 40ms. Pure CSS and SVG — no library, no
per-frame JavaScript. Under reduced motion the backdrop renders its finished state.

Accessibility closed in the same file: real `<label>` elements, `autocomplete="username"` /
`"current-password"` (report H-18), a password reveal toggle, `role="alert"` on the error, autofocus
on username (report H-02). The `<form>`, its heading text and both placeholders are preserved (§2).

The distinct session-expired message is retained.

## 7. Shell

- **TopBar** — a run chip (pulsing dot, server stage message, elapsed timer) appears while a job is
  running and opens the results sheet on click. The bottom border becomes an accent progress line
  for the duration of the run.
- **RailNav** — the active indicator becomes a single absolutely-positioned bar that translates
  between tabs rather than appearing and disappearing. Radix tooltips replace the native `title`
  attribute; `aria-current` added (report H-01). **This requires updating two `workstation.spec.ts`
  selectors** from `nav button[title="…"]` to an `aria-label` equivalent.
- **SidePanel** — collapsible, and drag-resizable between 260 and 520px. Collapsed state and width
  persist to `localStorage` (report H-12).
- **Pane** — lazily mounted on first visit, then kept mounted and CSS-hidden, with a cross-fade on
  the active pane. This ends the tab-switch data loss in report C-06. Affordable per §2.
- **MapArea** — floating control cluster: zoom-to-fit, scale bar, legend toggle (reports H-05,
  H-06).

## 8. Results

The side panel keeps a compact `RunSummaryCard` — headline `StatTile`s with count-up, a status
pill, and a control that opens the full breakdown.

The breakdown is a ~640px `Sheet` over the map, so map context is never lost. Sections stagger in:
recommendation reasons on an accent rail; the existing R-3 score breakdown chart, restyled;
Network / Electrical / Poles / Land stat grids with warn states; per-feeder loading bars that grow
from zero; candidate comparison with the recommendation highlighted; violations grouped by
severity.

While a run is in flight the pane shows the server's real percent on a smoothed bar, an elapsed
timer, and the server's own stage message. No stage is inferred (§2).

## 9. Verification

- `npm run typecheck`
- `npm test` — existing suites, notably the four `OptimizationPane` files, query by text and role;
  the component changes are additive to them.
- `npm run test:e2e` — expected to require the two RailNav selector edits in §7 and nothing else.
- Manual: keyboard-only traversal of sign-in → project select → run → results sheet; and a pass
  with `prefers-reduced-motion: reduce` forced, confirming the interface remains fully usable and
  no information is delivered by motion alone.
