# SURGE Web Map Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `web-map` as a new React + TypeScript app (`web-map-next/`) with the approved "technical dashboard" design system, full feature parity, and a maintainable component architecture, then cut production over to it.

**Architecture:** Vite + React 18 + TypeScript app scaffolded alongside the current `web-map/`. Server state (projects, assets, jobs, reports) goes through TanStack Query hooks calling a typed API client; small client-only UI state (active tab, layer toggles, auth) lives in two Zustand stores. Leaflet stays vanilla — `SurgeMapEngine` is ported almost unchanged and wrapped in one `MapCanvas` React component. UI is built from six small Radix-based primitives (Button, Card, Dialog, Select, Slider, Switch) styled with Tailwind utilities bound to the approved CSS-variable token system.

**Tech Stack:** React 18, TypeScript 5, Vite 5, Tailwind CSS 3, Radix UI primitives, TanStack Query 5, Zustand 4, Leaflet 1.9 (unchanged), `@types/geojson`.

## Global Constraints

- No changes to `backend-java`, `optimisation-python`, or `database` — same REST/JWT contract throughout.
- New app lives at `web-map-next/` (sibling to `web-map/`); `web-map/` keeps running unchanged until the cutover task.
- JWT stays in `localStorage` under the key `surge_jwt_token` — do not rename.
- `classify.js` logic (ported to `classify.ts`) must not be altered beyond adding types — it must stay in sync with `com.power.surge.service.classification.AssetClassifier` on the backend.
- Dark theme only for this pass — the token structure must support adding a light toggle later without rework, but no toggle UI is built now.
- No automated test suite for this migration (manual QA only, per the approved spec) — every task is verified by hand against the running app instead of a written test.
- Design tokens, type roles (UI sans + mono for numerals), and layout shape (52px top bar / 50px icon rail / 300px side panel / flexible map) come from the approved mockup and must not drift without a design conversation.
- Every task step that changes code ends with `npm run typecheck` passing before commit.

---

### Task 1: Project scaffold, dependencies, and design tokens

**Files:**
- Create: `web-map-next/package.json`
- Create: `web-map-next/tsconfig.json`
- Create: `web-map-next/tsconfig.node.json`
- Create: `web-map-next/vite.config.ts`
- Create: `web-map-next/tailwind.config.js`
- Create: `web-map-next/postcss.config.js`
- Create: `web-map-next/index.html`
- Create: `web-map-next/src/styles/globals.css`
- Create: `web-map-next/src/main.tsx`
- Create: `web-map-next/src/App.tsx`
- Create: `web-map-next/.gitignore`

**Interfaces:**
- Produces: Tailwind color tokens (`bg`, `panel`, `surface`, `surface2`, `border`, `borderStrong`, `text`, `textMuted`, `textFaint`, `accent`, `accentSoft`, `accentInk`, `success`, `successSoft`, `warning`, `warningSoft`, `danger`, `dangerSoft`) and font families (`font-ui`, `font-mono`) consumed by every later task's className strings.

- [ ] **Step 1: Create the project directory and `package.json`**

```json
{
  "name": "surge-web-map-next",
  "version": "1.0.0",
  "description": "SURGE - Smart Utility Routing & Grid Evacuation Web Map (React)",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@radix-ui/react-dialog": "^1.1.4",
    "@radix-ui/react-select": "^2.1.4",
    "@radix-ui/react-slider": "^1.2.2",
    "@radix-ui/react-switch": "^1.1.2",
    "@tanstack/react-query": "^5.62.7",
    "clsx": "^2.1.1",
    "leaflet": "^1.9.4",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "zustand": "^4.5.5"
  },
  "devDependencies": {
    "@types/geojson": "^7946.0.14",
    "@types/leaflet": "^1.9.14",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.15",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

Run: `cd web-map-next && npm install`
Expected: installs without errors, creates `package-lock.json`.

- [ ] **Step 2: Add TypeScript config**

`web-map-next/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`web-map-next/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Add Vite config with the `/api` dev proxy**

`web-map-next/vite.config.ts`:
```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
});
```

- [ ] **Step 4: Add Tailwind config bound to the token system**

`web-map-next/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        panel: 'var(--panel)',
        surface: 'var(--surface)',
        surface2: 'var(--surface-2)',
        border: 'var(--border)',
        borderStrong: 'var(--border-strong)',
        text: 'var(--text)',
        textMuted: 'var(--text-muted)',
        textFaint: 'var(--text-faint)',
        accent: 'var(--accent)',
        accentSoft: 'var(--accent-soft)',
        accentInk: 'var(--accent-ink)',
        success: 'var(--success)',
        successSoft: 'var(--success-soft)',
        warning: 'var(--warning)',
        warningSoft: 'var(--warning-soft)',
        danger: 'var(--danger)',
        dangerSoft: 'var(--danger-soft)'
      },
      fontFamily: {
        ui: ['-apple-system', '"Segoe UI"', 'Inter', 'sans-serif'],
        mono: ['ui-monospace', '"SF Mono"', '"Cascadia Code"', '"Roboto Mono"', 'Consolas', 'monospace']
      }
    }
  },
  plugins: []
};
```

`web-map-next/postcss.config.js`:
```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
};
```

- [ ] **Step 5: Add `index.html`, global tokens CSS, and entry files**

`web-map-next/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SURGE — Collector &amp; Evacuation Engine</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`web-map-next/src/styles/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg: #0A0A0C;
  --panel: #111113;
  --surface: #17171B;
  --surface-2: #1C1C20;
  --border: rgba(255,255,255,0.09);
  --border-strong: rgba(255,255,255,0.17);
  --text: #F2F3F5;
  --text-muted: #8B909C;
  --text-faint: #55585F;
  --accent: #4E8CFF;
  --accent-soft: rgba(78,140,255,0.14);
  --accent-ink: #071022;
  --success: #34D399;
  --success-soft: rgba(52,211,153,0.14);
  --warning: #F5A524;
  --warning-soft: rgba(245,165,36,0.14);
  --danger: #F0555A;
  --danger-soft: rgba(240,85,90,0.14);
}

* { box-sizing: border-box; }
html, body, #root { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, "Segoe UI", Inter, sans-serif;
  font-size: 13.5px;
  -webkit-font-smoothing: antialiased;
}
.tabular { font-variant-numeric: tabular-nums; }
.leaflet-container { background: var(--surface-2) !important; }
```

`web-map-next/src/main.tsx`:
```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import 'leaflet/dist/leaflet.css';
import './styles/globals.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

`web-map-next/src/App.tsx` (placeholder, replaced task-by-task):
```tsx
export default function App() {
  return (
    <div className="h-full flex items-center justify-center text-textMuted font-ui">
      SURGE shell scaffold — components land in later tasks.
    </div>
  );
}
```

`web-map-next/.gitignore`:
```
node_modules
dist
.DS_Store
*.local
```

- [ ] **Step 6: Verify the scaffold boots**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `cd web-map-next && npm run dev`
Expected: Vite starts on `http://localhost:5173`; open it in the browser preview and confirm the placeholder text renders on a near-black background.

- [ ] **Step 7: Commit**

```bash
git add web-map-next/package.json web-map-next/package-lock.json web-map-next/tsconfig.json web-map-next/tsconfig.node.json web-map-next/vite.config.ts web-map-next/tailwind.config.js web-map-next/postcss.config.js web-map-next/index.html web-map-next/src web-map-next/.gitignore
git commit -m "feat(web-map-next): scaffold Vite/React/TS app with design tokens"
```

---

### Task 2: UI primitives (Button, Card, Dialog, Select, Slider, Switch)

**Files:**
- Create: `web-map-next/src/components/ui/Button.tsx`
- Create: `web-map-next/src/components/ui/Card.tsx`
- Create: `web-map-next/src/components/ui/Dialog.tsx`
- Create: `web-map-next/src/components/ui/Select.tsx`
- Create: `web-map-next/src/components/ui/Slider.tsx`
- Create: `web-map-next/src/components/ui/Switch.tsx`
- Create: `web-map-next/src/components/ui/index.ts`

**Interfaces:**
- Consumes: Tailwind tokens from Task 1 (`bg-accent`, `text-textMuted`, etc.).
- Produces: `Button`, `Card`, `CardTitle`, `Dialog`, `Select` (+ `SelectOption`), `Slider`, `Switch` — the only styled primitives every feature component imports from `components/ui`.

- [ ] **Step 1: `Button.tsx`**

```tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary';
  size?: 'default' | 'sm';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-md border font-semibold cursor-pointer transition-colors',
        size === 'default' ? 'h-7 px-2.5 text-xs' : 'h-[26px] px-2 text-[11.5px]',
        variant === 'primary'
          ? 'bg-accent border-accent text-white hover:brightness-110'
          : 'bg-surface2 border-borderStrong text-text hover:border-textFaint',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      {...props}
    />
  )
);
Button.displayName = 'Button';
```

- [ ] **Step 2: `Card.tsx`**

```tsx
import { HTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={clsx('bg-surface border border-border rounded-lg p-3', className)} {...props} />
  )
);
Card.displayName = 'Card';

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={clsx(
        'm-0 mb-2 text-[11.5px] font-bold uppercase tracking-wide text-textMuted flex items-center gap-1.5',
        className
      )}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={clsx('m-0 mb-2.5 text-[11.5px] text-textFaint leading-relaxed', className)} {...props} />;
}
```

- [ ] **Step 3: `Dialog.tsx`**

```tsx
import * as RadixDialog from '@radix-ui/react-dialog';
import { ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  widthClassName?: string;
}

export function Dialog({ open, onOpenChange, title, children, footer, widthClassName = 'w-[480px]' }: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/60 z-40" />
        <RadixDialog.Content
          className={`fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 ${widthClassName} max-w-[92vw] max-h-[85vh] overflow-y-auto bg-panel border border-borderStrong rounded-lg p-4 z-50 font-ui text-text`}
        >
          <RadixDialog.Title className="m-0 mb-3 text-sm font-bold text-text">{title}</RadixDialog.Title>
          {children}
          {footer && <div className="mt-4 flex justify-end gap-2">{footer}</div>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
```

- [ ] **Step 4: `Select.tsx`**

```tsx
import * as RadixSelect from '@radix-ui/react-select';

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
}

export function Select({ value, onValueChange, options, className }: SelectProps) {
  return (
    <RadixSelect.Root value={value} onValueChange={onValueChange}>
      <RadixSelect.Trigger
        className={`h-[30px] rounded-md border border-borderStrong bg-surface2 px-2 text-xs text-text flex items-center justify-between gap-2 ${className || ''}`}
      >
        <RadixSelect.Value />
        <RadixSelect.Icon>▾</RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content className="bg-panel border border-borderStrong rounded-md overflow-hidden z-50">
          <RadixSelect.Viewport>
            {options.map((opt) => (
              <RadixSelect.Item
                key={opt.value}
                value={opt.value}
                className="px-2.5 py-1.5 text-xs text-text cursor-pointer outline-none data-[highlighted]:bg-accentSoft"
              >
                <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
```

- [ ] **Step 5: `Slider.tsx` and `Switch.tsx`**

`web-map-next/src/components/ui/Slider.tsx`:
```tsx
import * as RadixSlider from '@radix-ui/react-slider';

interface SliderProps {
  value: number;
  onValueChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
}

export function Slider({ value, onValueChange, min, max, step }: SliderProps) {
  return (
    <RadixSlider.Root
      className="relative flex items-center w-full h-4"
      value={[value]}
      onValueChange={([v]) => onValueChange(v)}
      min={min}
      max={max}
      step={step}
    >
      <RadixSlider.Track className="relative h-1 flex-1 rounded-full bg-borderStrong">
        <RadixSlider.Range className="absolute h-full rounded-full bg-accent" />
      </RadixSlider.Track>
      <RadixSlider.Thumb className="block w-3.5 h-3.5 rounded-full bg-accent border-2 border-panel shadow-[0_0_0_1px_var(--accent)] cursor-pointer" />
    </RadixSlider.Root>
  );
}
```

`web-map-next/src/components/ui/Switch.tsx`:
```tsx
import * as RadixSwitch from '@radix-ui/react-switch';

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

export function Switch({ checked, onCheckedChange }: SwitchProps) {
  return (
    <RadixSwitch.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      className="w-[30px] h-[17px] rounded-full bg-borderStrong data-[state=checked]:bg-accent relative flex-none cursor-pointer"
    >
      <RadixSwitch.Thumb className="block w-[13px] h-[13px] rounded-full bg-text translate-x-0.5 data-[state=checked]:translate-x-[15px] data-[state=checked]:bg-accentInk transition-transform" />
    </RadixSwitch.Root>
  );
}
```

- [ ] **Step 6: Barrel export**

`web-map-next/src/components/ui/index.ts`:
```ts
export { Button } from './Button';
export { Card, CardTitle, CardDescription } from './Card';
export { Dialog } from './Dialog';
export { Select, type SelectOption } from './Select';
export { Slider } from './Slider';
export { Switch } from './Switch';
```

- [ ] **Step 7: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

```bash
git add web-map-next/src/components
git commit -m "feat(web-map-next): add Radix-based UI primitives"
```

---

### Task 3: Client state stores (Zustand)

**Files:**
- Create: `web-map-next/src/lib/store/uiStore.ts`
- Create: `web-map-next/src/lib/store/authStore.ts`
- Create: `web-map-next/src/lib/store/index.ts`

**Interfaces:**
- Produces:
  - `LayerName` type: `'wtgs' | 'substations' | 'towers' | 'referenceLines' | 'routes' | 'parcels' | 'restricted' | 'imported'`
  - `useUiStore()` — hook returning `UiState` (see below), used by App shell, Layers, Assets, Optimization, Projects, Scenarios features.
  - `useAuthStore()` — hook returning `AuthState`, used by Auth feature and TopBar.

- [ ] **Step 1: `uiStore.ts`**

```ts
import { create } from 'zustand';

export type LayerName =
  | 'wtgs' | 'substations' | 'towers' | 'referenceLines'
  | 'routes' | 'parcels' | 'restricted' | 'imported';

export type SidebarTab = 'assets' | 'optimize' | 'layers' | 'bom' | 'audit';

interface UiState {
  activeSidebarTab: SidebarTab;
  setActiveSidebarTab: (tab: SidebarTab) => void;

  currentProjectId: string | null;
  setCurrentProjectId: (id: string | null) => void;

  currentJobId: string | null;
  setCurrentJobId: (id: string | null) => void;

  layerVisibility: Record<LayerName, boolean>;
  toggleLayer: (layer: LayerName) => void;

  parcelOpacity: number;
  setParcelOpacity: (v: number) => void;

  restrictedOpacity: number;
  setRestrictedOpacity: (v: number) => void;

  routeEditMode: boolean;
  setRouteEditMode: (v: boolean) => void;

  elevationDrawerOpen: boolean;
  setElevationDrawerOpen: (v: boolean) => void;

  scenarioComparisonOpen: boolean;
  setScenarioComparisonOpen: (v: boolean) => void;

  newProjectModalOpen: boolean;
  setNewProjectModalOpen: (v: boolean) => void;

  importPreviewOpen: boolean;
  setImportPreviewOpen: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeSidebarTab: 'assets',
  setActiveSidebarTab: (tab) => set({ activeSidebarTab: tab }),

  currentProjectId: null,
  setCurrentProjectId: (id) => set({ currentProjectId: id }),

  currentJobId: null,
  setCurrentJobId: (id) => set({ currentJobId: id }),

  layerVisibility: {
    wtgs: true, substations: true, towers: true, referenceLines: true,
    routes: true, parcels: true, restricted: false, imported: true
  },
  toggleLayer: (layer) =>
    set((s) => ({ layerVisibility: { ...s.layerVisibility, [layer]: !s.layerVisibility[layer] } })),

  parcelOpacity: 0.25,
  setParcelOpacity: (v) => set({ parcelOpacity: v }),

  restrictedOpacity: 0.35,
  setRestrictedOpacity: (v) => set({ restrictedOpacity: v }),

  routeEditMode: false,
  setRouteEditMode: (v) => set({ routeEditMode: v }),

  elevationDrawerOpen: false,
  setElevationDrawerOpen: (v) => set({ elevationDrawerOpen: v }),

  scenarioComparisonOpen: false,
  setScenarioComparisonOpen: (v) => set({ scenarioComparisonOpen: v }),

  newProjectModalOpen: false,
  setNewProjectModalOpen: (v) => set({ newProjectModalOpen: v }),

  importPreviewOpen: false,
  setImportPreviewOpen: (v) => set({ importPreviewOpen: v })
}));
```

- [ ] **Step 2: `authStore.ts`**

```ts
import { create } from 'zustand';

const TOKEN_KEY = 'surge_jwt_token';

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  role: string | null;
  login: (username: string, role: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  username: null,
  role: null,
  login: (username, role) => set({ isAuthenticated: true, username, role }),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ isAuthenticated: false, username: null, role: null });
  }
}));
```

- [ ] **Step 3: Barrel export**

`web-map-next/src/lib/store/index.ts`:
```ts
export { useUiStore, type LayerName, type SidebarTab } from './uiStore';
export { useAuthStore } from './authStore';
```

- [ ] **Step 4: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

```bash
git add web-map-next/src/lib/store
git commit -m "feat(web-map-next): add ui and auth zustand stores"
```

---

### Task 4: Typed API client

**Files:**
- Create: `web-map-next/src/lib/api/types.ts`
- Create: `web-map-next/src/lib/api/client.ts`
- Create: `web-map-next/src/lib/api/auth.ts`
- Create: `web-map-next/src/lib/api/projects.ts`
- Create: `web-map-next/src/lib/api/assets.ts`
- Create: `web-map-next/src/lib/api/jobs.ts`
- Create: `web-map-next/src/lib/api/reports.ts`
- Create: `web-map-next/src/lib/api/audit.ts`
- Create: `web-map-next/src/lib/api/index.ts`

This is a direct, behavior-preserving port of `web-map/src/api.js` (see file for the exact endpoints/fallbacks being reproduced) split into typed modules by resource, matching `features/*` folder boundaries.

**Interfaces:**
- Produces: all types below, plus a single `api` object re-exported from `lib/api/index.ts` with every method from the original `api.js` (`login`, `register`, `getAuditLogs`, `listProjects`, `createProject`, `importGeoJsonAssets`, `importKmzAssets`, `previewKmzAssets`, `commitAssetImport`, `getTowers`, `importParcelsGeoJson`, `importRestrictedAreasGeoJson`, `getProjectAssetsGeoJson`, `getParcelsGeoJson`, `getRestrictedAreasGeoJson`, `getRoutesGeoJson`, `runOptimization`, `getJobStatus`, `listenJobProgress`, `getBomReport`, `getPdfReportUrl`, `getBomCsvUrl`, `getScenarioComparison`) — unchanged signatures, so Task 6's Query hooks can call `api.method(...)` exactly as the old `app.js` did.

- [ ] **Step 1: `types.ts`**

```ts
import type { FeatureCollection } from 'geojson';
export type { FeatureCollection };

export interface Project {
  id: string;
  name: string;
  description?: string;
  crs?: string;
  createdAt?: string;
}

export interface AuthResponse {
  token: string;
  username: string;
  role: string;
}

export interface Job {
  id: string;
  status?: string;
}

export interface JobProgress {
  status: string;
  progressPercent?: number;
  message?: string;
}

export interface OptimizationParams {
  scenario: string;
  feederCapacityMw: number;
  maxSpanMeters: number;
  voltageKv: number;
}

export interface BomReport {
  totalNetworkLengthMeters: number;
  totalPoles: number;
  totalEstimatedCost: number;
  totalElectricalLossesKw: number;
  feederSummaries: unknown[];
}

export interface ImportPreviewFeature {
  externalId: string;
  geometryType: string;
  kmlFolder?: string;
  classifiedAs?: string;
  lineType?: string;
  status?: string;
  matchedRule: string;
  evidence?: string;
  vertexCount?: number;
}

export interface ImportPreview {
  importId: string;
  fileName?: string;
  countsByType?: Record<string, number>;
  duplicatesRemoved?: number;
  skippedByGeometry?: Record<string, number>;
  features: ImportPreviewFeature[];
}

export interface CommitImportBody {
  importId: string;
  overrides: Record<string, string>;
  defaultCapacityMw: number | null;
  skipUnclassified: boolean;
}

export interface CommitImportResult {
  wtgsImported?: number;
  substationsImported?: number;
  towersImported?: number;
  unclassified?: number;
}

export interface AuditLog {
  username?: string;
  action: string;
  details?: string;
  resourceType?: string;
  timestamp?: string;
}

export interface ScenarioComparisonEntry {
  scenarioName: string;
  totalEstimatedCost?: number;
  totalElectricalLossesKw?: number;
  landRowCompensationCost?: number;
  totalNetworkLengthMeters?: number;
  totalPoles?: number;
  capexDeltaPct?: number;
  lossesDeltaPct?: number;
}

export interface ScenarioComparison {
  scenarios: ScenarioComparisonEntry[];
}
```

- [ ] **Step 2: `client.ts`**

```ts
const API_BASE_URL = '/api/v1';
const TOKEN_KEY = 'surge_jwt_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined)
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP Error ${response.status}`);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

export async function uploadFile<T>(url: string, fileBlob: File | Blob): Promise<T> {
  const formData = new FormData();
  formData.append('file', fileBlob);
  const token = getToken();
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(url, { method: 'POST', headers, body: formData });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP Error ${response.status}`);
  }
  return (await response.json()) as T;
}

export function emptyGeoJson(): import('./types').FeatureCollection {
  return { type: 'FeatureCollection', features: [] };
}

export { API_BASE_URL };
```

- [ ] **Step 3: `auth.ts` and `audit.ts`**

`web-map-next/src/lib/api/auth.ts`:
```ts
import { API_BASE_URL, fetchJson, setToken } from './client';
import type { AuthResponse } from './types';

export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await fetchJson<AuthResponse>(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  if (res.token) setToken(res.token);
  return res;
}

export async function register(username: string, email: string, password: string): Promise<AuthResponse> {
  const res = await fetchJson<AuthResponse>(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    body: JSON.stringify({ username, email, password, role: 'ROLE_ENGINEER' })
  });
  if (res.token) setToken(res.token);
  return res;
}
```

`web-map-next/src/lib/api/audit.ts`:
```ts
import { API_BASE_URL, fetchJson } from './client';
import type { AuditLog } from './types';

export async function getAuditLogs(): Promise<AuditLog[]> {
  try {
    return await fetchJson<AuditLog[]>(`${API_BASE_URL}/audit-logs`);
  } catch {
    return [];
  }
}
```

- [ ] **Step 4: `projects.ts` and `assets.ts`**

`web-map-next/src/lib/api/projects.ts`:
```ts
import { API_BASE_URL, fetchJson } from './client';
import type { Project } from './types';

export async function listProjects(): Promise<Project[]> {
  try {
    const list = await fetchJson<Project[]>(`${API_BASE_URL}/projects`);
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export async function createProject(name: string, description: string): Promise<Project> {
  try {
    return await fetchJson<Project>(`${API_BASE_URL}/projects`, {
      method: 'POST',
      body: JSON.stringify({ name, description, crs: 'EPSG:4326' })
    });
  } catch (err) {
    console.warn('[Create Project API Fallback]', err);
    return {
      id: 'proj-' + Date.now(),
      name: name || 'Default Workstation Project',
      description: description || 'Grid Evacuation Workspace',
      crs: 'EPSG:4326',
      createdAt: new Date().toISOString()
    };
  }
}
```

`web-map-next/src/lib/api/assets.ts`:
```ts
import { API_BASE_URL, emptyGeoJson, fetchJson, uploadFile } from './client';
import type { CommitImportBody, CommitImportResult, FeatureCollection, ImportPreview } from './types';

export async function importGeoJsonAssets(projectId: string, geoJsonContent: unknown): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/assets/geojson`, {
    method: 'POST',
    body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
  });
}

export async function importKmzAssets(projectId: string, fileBlob: File): Promise<unknown> {
  return await uploadFile(`${API_BASE_URL}/projects/${projectId}/assets/kmz`, fileBlob);
}

export async function previewKmzAssets(projectId: string, fileBlob: File): Promise<ImportPreview> {
  return await uploadFile<ImportPreview>(`${API_BASE_URL}/projects/${projectId}/assets/kmz/preview`, fileBlob);
}

export async function commitAssetImport(projectId: string, body: CommitImportBody): Promise<CommitImportResult> {
  return await fetchJson<CommitImportResult>(`${API_BASE_URL}/projects/${projectId}/assets/import/commit`, {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

export async function getTowers(projectId: string): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/towers`);
}

export async function importParcelsGeoJson(projectId: string, geoJsonContent: unknown): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`, {
    method: 'POST',
    body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
  });
}

export async function importRestrictedAreasGeoJson(projectId: string, geoJsonContent: unknown): Promise<unknown> {
  return await fetchJson(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`, {
    method: 'POST',
    body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
  });
}

export async function getProjectAssetsGeoJson(projectId: string): Promise<FeatureCollection> {
  try {
    const res = await fetchJson<FeatureCollection>(`${API_BASE_URL}/projects/${projectId}/assets/geojson`);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Assets API Error]', e);
  }
  return emptyGeoJson();
}

export async function getParcelsGeoJson(projectId: string): Promise<FeatureCollection> {
  try {
    const res = await fetchJson<FeatureCollection>(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Parcels API Error]', e);
  }
  return emptyGeoJson();
}

export async function getRestrictedAreasGeoJson(projectId: string): Promise<FeatureCollection> {
  try {
    const res = await fetchJson<FeatureCollection>(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`);
    if (res && Array.isArray(res.features)) return res;
  } catch (e) {
    console.warn('[Restricted API Error]', e);
  }
  return emptyGeoJson();
}
```

- [ ] **Step 5: `jobs.ts` and `reports.ts`**

`web-map-next/src/lib/api/jobs.ts`:
```ts
import { API_BASE_URL, emptyGeoJson, fetchJson } from './client';
import type { FeatureCollection, Job, JobProgress, OptimizationParams } from './types';

export async function getRoutesGeoJson(projectId: string, jobId?: string | null): Promise<FeatureCollection> {
  try {
    if (jobId) {
      const res = await fetchJson<FeatureCollection>(
        `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/routes/geojson`
      );
      if (res && Array.isArray(res.features)) return res;
    }
  } catch (e) {
    console.warn('[Routes API Error]', e);
  }
  return emptyGeoJson();
}

export async function runOptimization(projectId: string, params: Partial<OptimizationParams> = {}): Promise<Job> {
  return await fetchJson<Job>(`${API_BASE_URL}/projects/${projectId}/jobs`, {
    method: 'POST',
    body: JSON.stringify({
      algorithmType: 'MULTI_OBJECTIVE_A_STAR',
      scenario: params.scenario || 'Balanced',
      feederCapacityMw: params.feederCapacityMw || 20.0,
      maxSpanMeters: params.maxSpanMeters || 150.0,
      voltageKv: params.voltageKv || 33.0
    })
  });
}

export async function getJobStatus(projectId: string, jobId: string): Promise<Job> {
  return await fetchJson<Job>(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}`);
}

export function listenJobProgress(
  projectId: string,
  jobId: string,
  onProgress?: (data: JobProgress) => void,
  onError?: (err: Error) => void,
  onComplete?: (data: JobProgress) => void
): () => void {
  const url = `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/progress`;
  let eventSource: EventSource;
  try {
    eventSource = new EventSource(url);

    eventSource.addEventListener('progress', (e: MessageEvent) => {
      try {
        const data: JobProgress = JSON.parse(e.data);
        if (onProgress) onProgress(data);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          eventSource.close();
          if (data.status === 'COMPLETED' && onComplete) onComplete(data);
          if (data.status === 'FAILED' && onError) onError(new Error(data.message || 'Job failed'));
        }
      } catch (err) {
        console.warn('[SSE Parse Error]', err);
      }
    });

    eventSource.onerror = (err) => {
      eventSource.close();
      if (onError) onError(err as unknown as Error);
    };

    return () => eventSource.close();
  } catch (err) {
    if (onError) onError(err as Error);
    return () => {};
  }
}
```

`web-map-next/src/lib/api/reports.ts`:
```ts
import { API_BASE_URL, fetchJson } from './client';
import type { BomReport, ScenarioComparison } from './types';

export async function getBomReport(projectId: string): Promise<BomReport> {
  try {
    return await fetchJson<BomReport>(`${API_BASE_URL}/projects/${projectId}/reports/bom`);
  } catch {
    return {
      totalNetworkLengthMeters: 0,
      totalPoles: 0,
      totalEstimatedCost: 0,
      totalElectricalLossesKw: 0,
      feederSummaries: []
    };
  }
}

export function getPdfReportUrl(projectId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/reports/pdf`;
}

export function getBomCsvUrl(projectId: string, jobId?: string | null): string {
  if (jobId) return `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/reports/bom/csv`;
  return `${API_BASE_URL}/projects/${projectId}/reports/bom/csv`;
}

export async function getScenarioComparison(projectId: string): Promise<ScenarioComparison> {
  return await fetchJson<ScenarioComparison>(`${API_BASE_URL}/projects/${projectId}/reports/scenarios/compare`);
}
```

- [ ] **Step 6: Barrel export**

`web-map-next/src/lib/api/index.ts`:
```ts
import * as auth from './auth';
import * as projects from './projects';
import * as assets from './assets';
import * as jobs from './jobs';
import * as reports from './reports';
import * as audit from './audit';

export const api = { ...auth, ...projects, ...assets, ...jobs, ...reports, ...audit };
export * from './types';
```

- [ ] **Step 7: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

```bash
git add web-map-next/src/lib/api
git commit -m "feat(web-map-next): port typed API client from web-map/src/api.js"
```

---

### Task 5: Port `classify.ts`

**Files:**
- Create: `web-map-next/src/lib/classify.ts`

**Interfaces:**
- Produces: `ASSET_TYPES`, `ASSET_TYPE_LABELS`, `OPTIMISABLE_STATUSES`, `LINE_TYPES`, `LINE_TYPE_LABELS`, `classifyFeature`, `normaliseType`, `isOptimisable`, `classifyLine`, `classifyPolygon`, `classifyGeoJsonFeature` — identical names/behavior to `web-map/src/classify.js`, consumed by the Assets feature (Task 13/14).

- [ ] **Step 1: Port the file verbatim with type annotations**

Copy `web-map/src/classify.js` to `web-map-next/src/lib/classify.ts` unchanged in logic. Add these type annotations only (do not alter any rule, regex, or ordering — the header comment's sync requirement with `AssetClassifier.java` still applies):

```ts
export function classifyFeature(properties: Record<string, unknown> = {}) { /* ...unchanged body... */ }
export function normaliseType(value: unknown): string { /* ...unchanged body... */ }
export function isOptimisable(status: string): boolean { /* ...unchanged body... */ }
export function classifyLine(properties: Record<string, unknown> = {}) { /* ...unchanged body... */ }
export function classifyPolygon(properties: Record<string, unknown> = {}) { /* ...unchanged body... */ }
export function classifyGeoJsonFeature(feature: import('geojson').Feature) { /* ...unchanged body... */ }
```

Concretely: take every line of `web-map/src/classify.js` (263 lines — `ASSET_TYPES` through `classifyGeoJsonFeature`) and paste it into `classify.ts`, then change only the six function signatures above to add parameter/return types as shown. Everything else (constants, regexes, `folderSegmentsLeafFirst`, `statusFor`) is copied byte-for-byte.

- [ ] **Step 2: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run a manual parity check — in a scratch Node REPL or a temporary script, call `classifyFeature({ externalId: 'KS-101' })` from both `web-map/src/classify.js` and `web-map-next/src/lib/classify.ts` and confirm identical output (`{ assetType: 'WTG', ... }`).

```bash
git add web-map-next/src/lib/classify.ts
git commit -m "feat(web-map-next): port asset classification rules"
```

---

### Task 6: TanStack Query setup and hooks

**Files:**
- Create: `web-map-next/src/lib/query/queryClient.ts`
- Create: `web-map-next/src/lib/query/queries.ts`
- Create: `web-map-next/src/lib/query/mutations.ts`
- Create: `web-map-next/src/lib/query/index.ts`
- Modify: `web-map-next/src/main.tsx` — wrap `<App />` in `QueryClientProvider`

**Interfaces:**
- Consumes: `api` from `lib/api` (Task 4).
- Produces: `useProjects`, `useProjectAssets(projectId)`, `useParcels(projectId)`, `useRestrictedAreas(projectId)`, `useRoutes(projectId, jobId)`, `useBomReport(projectId)`, `useAuditLogs()`, `useScenarioComparison(projectId)` (queries); `useCreateProject`, `usePreviewKmzImport(projectId)`, `useCommitImport(projectId)`, `useRunOptimization(projectId)` (mutations) — used by every feature task from Task 10 onward.

- [ ] **Step 1: `queryClient.ts`**

```ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false
    }
  }
});
```

- [ ] **Step 2: `queries.ts`**

```ts
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: api.listProjects });
}

export function useProjectAssets(projectId: string | null) {
  return useQuery({
    queryKey: ['assets', projectId],
    queryFn: () => api.getProjectAssetsGeoJson(projectId as string),
    enabled: !!projectId
  });
}

export function useParcels(projectId: string | null) {
  return useQuery({
    queryKey: ['parcels', projectId],
    queryFn: () => api.getParcelsGeoJson(projectId as string),
    enabled: !!projectId
  });
}

export function useRestrictedAreas(projectId: string | null) {
  return useQuery({
    queryKey: ['restrictedAreas', projectId],
    queryFn: () => api.getRestrictedAreasGeoJson(projectId as string),
    enabled: !!projectId
  });
}

export function useRoutes(projectId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ['routes', projectId, jobId],
    queryFn: () => api.getRoutesGeoJson(projectId as string, jobId),
    enabled: !!projectId
  });
}

export function useBomReport(projectId: string | null) {
  return useQuery({
    queryKey: ['bom', projectId],
    queryFn: () => api.getBomReport(projectId as string),
    enabled: !!projectId
  });
}

export function useAuditLogs() {
  return useQuery({ queryKey: ['auditLogs'], queryFn: api.getAuditLogs });
}

export function useScenarioComparison(projectId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['scenarioComparison', projectId],
    queryFn: () => api.getScenarioComparison(projectId as string),
    enabled: !!projectId && enabled
  });
}
```

- [ ] **Step 3: `mutations.ts`**

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { CommitImportBody, OptimizationParams, Project } from '../api';

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description: string }) =>
      api.createProject(name, description),
    onSuccess: (project) => {
      qc.setQueryData<Project[]>(['projects'], (old) => (old ? [...old, project] : [project]));
    }
  });
}

export function usePreviewKmzImport(projectId: string | null) {
  return useMutation({
    mutationFn: (file: File) => api.previewKmzAssets(projectId as string, file)
  });
}

export function useCommitImport(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CommitImportBody) => api.commitAssetImport(projectId as string, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', projectId] });
      qc.invalidateQueries({ queryKey: ['parcels', projectId] });
      qc.invalidateQueries({ queryKey: ['restrictedAreas', projectId] });
    }
  });
}

export function useRunOptimization(projectId: string | null) {
  return useMutation({
    mutationFn: (params: OptimizationParams) => api.runOptimization(projectId as string, params)
  });
}
```

- [ ] **Step 4: Barrel export and provider wiring**

`web-map-next/src/lib/query/index.ts`:
```ts
export { queryClient } from './queryClient';
export * from './queries';
export * from './mutations';
```

Modify `web-map-next/src/main.tsx`:
```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import 'leaflet/dist/leaflet.css';
import './styles/globals.css';
import { queryClient } from './lib/query';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
);
```

- [ ] **Step 5: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, confirm the app still boots (React Query Devtools not required) with no console errors.

```bash
git add web-map-next/src/lib/query web-map-next/src/main.tsx
git commit -m "feat(web-map-next): add TanStack Query client and resource hooks"
```

---

### Task 7: App shell (TopBar, RailNav, SidePanel, MapArea)

**Files:**
- Create: `web-map-next/src/app/TopBar.tsx`
- Create: `web-map-next/src/app/RailNav.tsx`
- Create: `web-map-next/src/app/SidePanel.tsx`
- Create: `web-map-next/src/app/MapArea.tsx`
- Modify: `web-map-next/src/App.tsx`

**Interfaces:**
- Consumes: `useUiStore` (Task 3), UI primitives (Task 2).
- Produces: `<TopBar />`, `<RailNav />`, `<SidePanel>{children}</SidePanel>`, `<MapArea>{children}</MapArea>` — the layout every later feature slots into. `RailNav` reads/writes `activeSidebarTab` from `useUiStore`; `SidePanel` renders whichever child matches `activeSidebarTab` via a `tab` prop on each child.

- [ ] **Step 1: `TopBar.tsx`** (placeholder project selector / export buttons — replaced with real data in Tasks 11–12)

```tsx
export function TopBar() {
  return (
    <header className="h-[52px] flex-none flex items-center gap-5 px-4 bg-panel border-b border-border font-ui">
      <div className="flex items-center gap-2">
        <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-accent" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
        </svg>
        <span className="font-bold tracking-wide text-sm text-text">SURGE</span>
        <span className="text-[10.5px] text-textFaint ml-2 pl-2 border-l border-borderStrong">
          Collector &amp; Evacuation Engine
        </span>
      </div>
      <div id="topbar-project-slot" className="flex items-center gap-2" />
      <div className="flex-1" />
      <div id="topbar-actions-slot" className="flex items-center gap-2" />
    </header>
  );
}
```

- [ ] **Step 2: `RailNav.tsx`**

```tsx
import { useUiStore, type SidebarTab } from '../lib/store';

const TABS: { id: SidebarTab; title: string; path: string }[] = [
  { id: 'assets', title: 'Assets', path: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' },
  { id: 'optimize', title: 'Optimization', path: 'M13 2 4 14h6l-1 8 9-12h-6l1-8z' },
  { id: 'layers', title: 'Layers', path: 'M12 2l9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5' },
  { id: 'bom', title: 'BOM', path: 'M9 2h6l1 4H8l1-4zM6 6h12l1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L6 6z' },
  { id: 'audit', title: 'Audit', path: 'M9 11H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h4m0-10V7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-9m0-10v12' }
];

export function RailNav() {
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  const setActiveSidebarTab = useUiStore((s) => s.setActiveSidebarTab);

  return (
    <nav className="w-[50px] flex-none bg-panel border-r border-border flex flex-col items-center pt-2.5 gap-0.5">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          title={tab.title}
          onClick={() => setActiveSidebarTab(tab.id)}
          className={`relative w-[38px] h-[38px] flex items-center justify-center rounded-lg border border-transparent ${
            activeSidebarTab === tab.id ? 'text-accent bg-accentSoft' : 'text-textFaint hover:text-textMuted hover:bg-surface2'
          }`}
        >
          {activeSidebarTab === tab.id && (
            <span className="absolute -left-2.5 top-2 bottom-2 w-0.5 rounded bg-accent" />
          )}
          <svg viewBox="0 0 24 24" className="w-[17px] h-[17px]" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d={tab.path} />
          </svg>
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 3: `SidePanel.tsx` and `MapArea.tsx`**

`web-map-next/src/app/SidePanel.tsx`:
```tsx
import { ReactNode } from 'react';
import { useUiStore, type SidebarTab } from '../lib/store';

interface PaneProps {
  tab: SidebarTab;
  children: ReactNode;
}

export function Pane({ tab, children }: PaneProps) {
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  if (activeSidebarTab !== tab) return null;
  return <div className="flex flex-col gap-3">{children}</div>;
}

export function SidePanel({ children }: { children: ReactNode }) {
  return (
    <aside className="w-[300px] flex-none bg-panel border-r border-border overflow-y-auto p-3.5">
      {children}
    </aside>
  );
}
```

`web-map-next/src/app/MapArea.tsx`:
```tsx
import { ReactNode } from 'react';

export function MapArea({ children }: { children: ReactNode }) {
  return <main className="flex-1 relative bg-surface2 overflow-hidden">{children}</main>;
}
```

- [ ] **Step 4: Compose `App.tsx`**

```tsx
import { TopBar } from './app/TopBar';
import { RailNav } from './app/RailNav';
import { SidePanel, Pane } from './app/SidePanel';
import { MapArea } from './app/MapArea';

export default function App() {
  return (
    <div className="h-full flex flex-col font-ui text-text">
      <TopBar />
      <div className="flex-1 flex min-h-0">
        <RailNav />
        <SidePanel>
          <Pane tab="assets"><div className="text-textFaint text-xs">Assets pane — Task 13/14</div></Pane>
          <Pane tab="optimize"><div className="text-textFaint text-xs">Optimization pane — Task 15</div></Pane>
          <Pane tab="layers"><div className="text-textFaint text-xs">Layers pane — Task 16</div></Pane>
          <Pane tab="bom"><div className="text-textFaint text-xs">BOM pane — Task 17</div></Pane>
          <Pane tab="audit"><div className="text-textFaint text-xs">Audit pane — Task 18</div></Pane>
        </SidePanel>
        <MapArea>
          <div className="flex items-center justify-center h-full text-textFaint text-xs">
            Map canvas — Task 10
          </div>
        </MapArea>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, open the preview, and confirm: 52px dark header with the SURGE wordmark, a 50px icon rail on the left with 5 icons, clicking each icon switches which placeholder pane text shows in the 300px side panel, and the remaining space is the map placeholder.

```bash
git add web-map-next/src/app web-map-next/src/App.tsx
git commit -m "feat(web-map-next): build app shell layout (TopBar, RailNav, SidePanel, MapArea)"
```

---

### Task 8: Port the Leaflet map engine

**Files:**
- Create: `web-map-next/src/lib/map/icons.ts`
- Create: `web-map-next/src/lib/map/SurgeMapEngine.ts`
- Create: `web-map-next/src/lib/map/elevationProfile.ts`

This ports `web-map/src/icons.js` and `web-map/src/map.js` (534 lines) almost unchanged — Leaflet stays vanilla per the design spec. The one structural change: `renderElevationProfile` is extracted out of the engine class into a standalone function that takes an `SVGSVGElement` directly instead of looking one up by a global DOM id, so the future `ElevationDrawer` React component (Task 20) can own its own `<svg>` ref instead of relying on a string id living somewhere else in the tree.

**Interfaces:**
- Consumes: `LayerName` type from `lib/store` (Task 3).
- Produces: `SVG_ICONS` (unchanged), `SurgeMapEngine` class with the same public methods as before minus `renderElevationProfile`, and `renderElevationProfile(svg: SVGSVGElement, routeGeoJson: FeatureCollection): void` as a standalone export — consumed by `MapCanvas` (Task 9) and `ElevationDrawer` (Task 20) respectively.

- [ ] **Step 1: `icons.ts`**

Port `web-map/src/icons.js` unchanged, only adding a type:

```ts
export const SVG_ICONS: Record<string, string> = {
  wtg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-wtg"><path d="M12 13v9"/><path d="M12 11a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/><path d="M12 7V2l4 4z"/><path d="M10.3 8.8L5.7 6.2l1.6 5.4z"/><path d="M13.7 8.8l4.6-2.6-1.6 5.4z"/></svg>`,
  substation: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-substation"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M13 7l-3 5h4l-3 5"/><line x1="8" y1="2" x2="8" y2="4"/><line x1="16" y1="2" x2="16" y2="4"/></svg>`,
  tower: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-tower"><path d="M7 22L10 3h4l3 19"/><path d="M4.5 8h15"/><path d="M6 13h12"/><path d="M10 3L5 6.5"/><path d="M14 3l5 3.5"/><path d="M8.6 13L15.4 8"/><path d="M15.4 13L8.6 8"/></svg>`,
  route: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-route"><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="5" r="2.5"/><path d="M7.2 17.5l9.6-10"/><path d="M12 6h4.5v4.5"/></svg>`,
  parcel: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-parcel"><path d="M4 8l8-4 8 4-3 12H7L4 8z"/><path d="M12 4v16"/><path d="M6 14h12"/></svg>`,
  restricted: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-restricted"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>`,
  genericPoint: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="surge-icon surge-icon-point"><circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"/></svg>`
};
```

- [ ] **Step 2: `SurgeMapEngine.ts`**

Port `web-map/src/map.js` lines 1–448 (constructor through `enableRouteEditing`) unchanged in behavior, converted to TypeScript:

```ts
import L from 'leaflet';
import type { FeatureCollection } from 'geojson';
import { SVG_ICONS } from './icons';
import type { LayerName } from '../store';

export class SurgeMapEngine {
  map: L.Map;
  layers: Record<LayerName, L.FeatureGroup>;
  parcelGeoJson?: FeatureCollection;
  restrictedGeoJson?: FeatureCollection;
  editHandleLayer?: L.LayerGroup;

  constructor(containerId: string) {
    this.map = L.map(containerId, { center: [23.2350, 69.8210], zoom: 13, zoomControl: false });
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    const darkCarto = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; CartoDB &copy; OpenStreetMap'
    });
    const esriSatellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 19, attribution: 'Esri World Imagery' }
    );
    darkCarto.addTo(this.map);
    L.control.layers({ 'Dark Grid': darkCarto, Satellite: esriSatellite }, undefined, { position: 'topright' }).addTo(this.map);

    this.layers = {
      wtgs: L.featureGroup().addTo(this.map),
      substations: L.featureGroup().addTo(this.map),
      towers: L.featureGroup().addTo(this.map),
      referenceLines: L.featureGroup().addTo(this.map),
      routes: L.featureGroup().addTo(this.map),
      parcels: L.featureGroup().addTo(this.map),
      restricted: L.featureGroup().addTo(this.map),
      imported: L.featureGroup().addTo(this.map)
    };
  }

  clearAll(): void {
    Object.values(this.layers).forEach((layerGroup) => layerGroup.clearLayers());
  }

  renderWtgs(geoJson: FeatureCollection): void {
    this.layers.wtgs.clearLayers();
    if (!geoJson || !geoJson.features) return;
    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const props = (feature.properties || {}) as Record<string, any>;
        const excluded = props.optimisable === false;
        const icon = L.divIcon({
          className: `custom-leaflet-marker wtg-marker${excluded ? ' wtg-excluded' : ''}`,
          html: `<div class="marker-pin wtg-pin${excluded ? ' wtg-pin-excluded' : ''}">${SVG_ICONS.wtg}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });
        const marker = L.marker(latlng, { icon });
        const status = props.status || 'UNKNOWN';
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.wtg} Wind Turbine Generator</h4>
            <div class="popup-row"><span>Turbine ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Capacity:</span> <strong>${props.capacityMw || 3.0} MW</strong></div>
            <div class="popup-row"><span>Status:</span> <strong>${status.replace(/_/g, ' ')}</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
            ${excluded ? '<div class="popup-note">Excluded from optimisation by status.</div>' : ''}
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.wtgs);
  }

  renderSubstations(geoJson: FeatureCollection): void {
    this.layers.substations.clearLayers();
    if (!geoJson || !geoJson.features) return;
    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const icon = L.divIcon({
          className: 'custom-leaflet-marker sub-marker',
          html: `<div class="marker-pin sub-pin">${SVG_ICONS.substation}</div>`,
          iconSize: [34, 34],
          iconAnchor: [17, 17]
        });
        const marker = L.marker(latlng, { icon });
        const props = (feature.properties || {}) as Record<string, any>;
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.substation} Substation</h4>
            <div class="popup-row"><span>Substation ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Grid Capacity:</span> <strong>${props.capacityMw || 100} MW</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.substations);
  }

  renderTowers(geoJson: FeatureCollection): void {
    this.layers.towers.clearLayers();
    if (!geoJson || !geoJson.features) return;
    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const icon = L.divIcon({
          className: 'custom-leaflet-marker tower-marker',
          html: `<div class="marker-pin tower-pin">${SVG_ICONS.tower}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });
        const marker = L.marker(latlng, { icon });
        const props = (feature.properties || {}) as Record<string, any>;
        const towerType = props.towerType ? props.towerType.replace('_', ' ') : 'Tower';
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.tower} Evacuation Tower</h4>
            <div class="popup-row"><span>Tower ID:</span> <strong>${props.externalId || feature.id}</strong></div>
            <div class="popup-row"><span>Structure:</span> <strong>${towerType}</strong></div>
            ${props.lineSection ? `<div class="popup-row"><span>Line section:</span> <strong>${props.lineSection}</strong></div>` : ''}
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
            <div class="popup-note">Existing asset — not part of collector optimisation.</div>
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.towers);
  }

  renderReferenceLines(geoJson: FeatureCollection): void {
    this.layers.referenceLines.clearLayers();
    if (!geoJson || !geoJson.features) return;

    const STYLES: Record<string, { color: string; weight: number; dashArray: string | null; label: string }> = {
      ROAD: { color: '#A8A29E', weight: 2, dashArray: null, label: 'Road' },
      HT_LINE: { color: '#F472B6', weight: 2.5, dashArray: '10 4', label: 'HT / EHV line' },
      WATERCOURSE: { color: '#38BDF8', weight: 2.5, dashArray: null, label: 'Watercourse' },
      EVACUATION_ROUTE: { color: '#A78BFA', weight: 2, dashArray: '4 4', label: 'Existing route' },
      UNKNOWN: { color: '#64748B', weight: 1.5, dashArray: '2 4', label: 'Unclassified line' }
    };

    L.geoJSON(geoJson, {
      style: (feature) => {
        const style = STYLES[feature?.properties?.lineType] || STYLES.UNKNOWN;
        return { color: style.color, weight: style.weight, dashArray: style.dashArray ?? undefined, opacity: 0.75 };
      },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        const style = STYLES[props.lineType] || STYLES.UNKNOWN;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${style.label}</h4>
            <div class="popup-row"><span>Name:</span> <strong>${props.externalId || 'unnamed'}</strong></div>
            ${props.voltageKv ? `<div class="popup-row"><span>Voltage:</span> <strong>${props.voltageKv} kV</strong></div>` : ''}
            <div class="popup-note">${
              props.crossingConstraint ? 'Crossing this feature adds cost to a route.' : 'Reference only — no routing constraint.'
            }</div>
          </div>
        `);
        layer.on('mouseover', () => (layer as L.Path).setStyle({ weight: style.weight + 2, opacity: 1 }));
        layer.on('mouseout', () => (layer as L.Path).setStyle({ weight: style.weight, opacity: 0.75 }));
      }
    }).addTo(this.layers.referenceLines);
  }

  renderRoutes(geoJson: FeatureCollection, customColor: string | null = null): void {
    this.layers.routes.clearLayers();
    if (!geoJson || !geoJson.features) return;
    const colors = customColor ? [customColor] : ['#10B981', '#06B6D4', '#3B82F6', '#8B5CF6', '#F59E0B'];
    let idx = 0;
    L.geoJSON(geoJson, {
      style: () => ({
        color: customColor || colors[idx++ % colors.length],
        weight: 5,
        opacity: 0.85,
        dashArray: '10, 6',
        lineCap: 'round'
      }),
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.route} Feeder Route</h4>
            <div class="popup-row"><span>Feeder:</span> <strong>${props.feederName || 'Feeder'}</strong></div>
            <div class="popup-row"><span>Length:</span> <strong>${
              props.totalLengthMeters ? (props.totalLengthMeters / 1000).toFixed(2) + ' km' : 'N/A'
            }</strong></div>
            <div class="popup-row"><span>Poles Placed:</span> <strong>${props.poleCount || 0}</strong></div>
            <div class="popup-row"><span>Estimated Cost:</span> <strong>$${(props.totalCost || 0).toLocaleString()}</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.routes);
  }

  renderParcels(geoJson: FeatureCollection, fillOpacity = 0.25): void {
    this.layers.parcels.clearLayers();
    if (!geoJson || !geoJson.features) return;
    this.parcelGeoJson = geoJson;
    L.geoJSON(geoJson, {
      style: { color: '#8B5CF6', weight: 2, fillColor: '#8B5CF6', fillOpacity },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.parcel} Cadastral Land Parcel</h4>
            <div class="popup-row"><span>Parcel ID:</span> <strong>${props.parcelId || feature.id}</strong></div>
            <div class="popup-row"><span>Owner:</span> <strong>${props.ownerName || 'Private Owner'}</strong></div>
            <div class="popup-row"><span>Acquisition Rate:</span> <strong>$${props.acquisitionCostPerM2 || 100}/m²</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.parcels);
  }

  renderRestrictedAreas(geoJson: FeatureCollection, fillOpacity = 0.35): void {
    this.layers.restricted.clearLayers();
    if (!geoJson || !geoJson.features) return;
    this.restrictedGeoJson = geoJson;
    L.geoJSON(geoJson, {
      style: { color: '#EF4444', weight: 2, fillColor: '#EF4444', fillOpacity, dashArray: '4, 4' },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.restricted} Restricted Area</h4>
            <div class="popup-row"><span>Zone Name:</span> <strong>${props.name || 'Exclusion Zone'}</strong></div>
            <div class="popup-row"><span>Restriction Type:</span> <strong>${props.restrictionType || 'ENVIRONMENTAL'}</strong></div>
            <div class="popup-row"><span>Buffer Distance:</span> <strong>${props.bufferMeters || 0} m</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.restricted);
  }

  setLayerOpacity(layerName: 'parcels' | 'restricted', opacity: number): void {
    if (layerName === 'parcels' && this.parcelGeoJson) {
      this.renderParcels(this.parcelGeoJson, opacity);
    } else if (layerName === 'restricted' && this.restrictedGeoJson) {
      this.renderRestrictedAreas(this.restrictedGeoJson, opacity);
    }
  }

  clearImported(): void {
    this.layers.imported.clearLayers();
  }

  invalidateSize(): void {
    this.map.invalidateSize({ animate: false });
  }

  renderImportedGeoJson(geoJson: FeatureCollection): void {
    if (!geoJson) return;
    const importedLayer = L.geoJSON(geoJson, {
      style: (feature) => {
        const geomType = feature?.geometry ? feature.geometry.type : '';
        if (geomType.includes('Polygon')) return { color: '#06B6D4', weight: 2, fillColor: '#06B6D4', fillOpacity: 0.35 };
        if (geomType.includes('LineString')) return { color: '#10B981', weight: 4, opacity: 0.9, dashArray: '8, 4' };
        return { color: '#3B82F6', weight: 2 };
      },
      pointToLayer: (feature, latlng) => {
        const icon = L.divIcon({
          className: 'custom-leaflet-marker wtg-marker',
          html: `<div class="marker-pin wtg-pin">${SVG_ICONS.genericPoint}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });
        const marker = L.marker(latlng, { icon });
        const props = (feature.properties || {}) as Record<string, any>;
        const title = props.externalId || props.name || props.id || 'Imported Feature';
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.genericPoint} ${title}</h4>
            <div class="popup-row"><span>Type:</span> <strong>${feature.geometry ? feature.geometry.type : 'Point'}</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
          </div>
        `);
        return marker;
      },
      onEachFeature: (feature, layer) => {
        if (feature.geometry && feature.geometry.type.includes('Point')) return;
        const props = (feature.properties || {}) as Record<string, any>;
        const keys = Object.keys(props).slice(0, 4);
        const rowsHtml = keys.map((k) => `<div class="popup-row"><span>${k}:</span> <strong>${props[k]}</strong></div>`).join('');
        layer.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-layer-group text-cyan"></i> Imported GeoJSON Feature</h4>
            ${rowsHtml || '<div class="popup-row"><span>Geometry:</span> <strong>' + feature.geometry.type + '</strong></div>'}
          </div>
        `);
      }
    }).addTo(this.layers.imported);

    try {
      const bounds = importedLayer.getBounds();
      if (bounds && bounds.isValid()) this.map.fitBounds(bounds, { padding: [50, 50] });
    } catch (err) {
      console.warn('Could not fit bounds to imported GeoJSON:', err);
    }
  }

  fitAllBounds(): void {
    const allLayers: L.Layer[] = [];
    Object.values(this.layers).forEach((layerGroup) => layerGroup.eachLayer((layer) => allLayers.push(layer)));
    if (allLayers.length === 0) return;
    try {
      const group = L.featureGroup(allLayers);
      const bounds = group.getBounds();
      if (bounds && bounds.isValid()) this.map.fitBounds(bounds, { padding: [40, 40] });
    } catch (e) {
      console.warn('Could not fit bounds:', e);
    }
  }

  setLayerVisibility(layerName: LayerName, visible: boolean): void {
    if (!this.layers[layerName]) return;
    if (visible) this.map.addLayer(this.layers[layerName]);
    else this.map.removeLayer(this.layers[layerName]);
  }

  enableRouteEditing(enabled: boolean, onVertexMoved?: (lengthMeters: number, poles: number, cost: number) => void): void {
    if (this.editHandleLayer) {
      this.map.removeLayer(this.editHandleLayer);
      this.editHandleLayer = undefined;
    }
    if (!enabled) return;

    this.editHandleLayer = L.layerGroup().addTo(this.map);

    this.layers.routes.eachLayer((layerGroup) => {
      if (layerGroup instanceof L.GeoJSON) {
        layerGroup.eachLayer((polylineLayer) => {
          if (polylineLayer instanceof L.Polyline) {
            const latlngs = polylineLayer.getLatLngs() as L.LatLng[];
            latlngs.forEach((latlng, index) => {
              const handle = L.marker(latlng, {
                draggable: true,
                icon: L.divIcon({
                  className: 'vertex-drag-handle',
                  html: `<div style="width:12px;height:12px;background:#F59E0B;border:2px solid #ffffff;border-radius:50%;cursor:grab;"></div>`,
                  iconSize: [12, 12],
                  iconAnchor: [6, 6]
                })
              });
              handle.on('drag', (e) => {
                const newLatLng = (e.target as L.Marker).getLatLng();
                latlngs[index] = newLatLng;
                polylineLayer.setLatLngs(latlngs);
                let totalDist = 0;
                for (let i = 0; i < latlngs.length - 1; i++) totalDist += latlngs[i].distanceTo(latlngs[i + 1]);
                const newPoles = Math.ceil(totalDist / 150.0);
                const newCost = Math.round(totalDist * 80.0);
                if (onVertexMoved) onVertexMoved(totalDist, newPoles, newCost);
              });
              handle.addTo(this.editHandleLayer!);
            });
          }
        });
      }
    });
  }
}
```

- [ ] **Step 3: `elevationProfile.ts`** — extracted from the old `renderElevationProfile(svgId, routeGeoJson)`

```ts
import L from 'leaflet';
import type { FeatureCollection } from 'geojson';

export function renderElevationProfile(svg: SVGSVGElement, routeGeoJson: FeatureCollection): void {
  let coords: number[][] = [];
  if (routeGeoJson && routeGeoJson.features && routeGeoJson.features.length > 0) {
    const feat = routeGeoJson.features[0];
    if (feat.geometry && 'coordinates' in feat.geometry) {
      coords = feat.geometry.coordinates as number[][];
    }
  }
  if (coords.length < 2) {
    coords = [[69.8210, 23.2350], [69.8150, 23.2280], [69.8050, 23.2200]];
  }

  const points: { dist: number; elev: number }[] = [];
  let cumDist = 0;
  const baseElevation = 45;

  for (let i = 0; i < coords.length; i++) {
    if (i > 0) {
      const p1 = L.latLng(coords[i - 1][1], coords[i - 1][0]);
      const p2 = L.latLng(coords[i][1], coords[i][0]);
      cumDist += p1.distanceTo(p2);
    }
    const elev = baseElevation + Math.sin(i * 1.5) * 18 + Math.cos(i * 0.8) * 12;
    points.push({ dist: cumDist, elev });
  }

  const totalDist = points[points.length - 1].dist || 5000;
  const minElev = 10;
  const maxElev = 90;
  const width = 800;
  const height = 160;
  const padding = 24;

  const scaleX = (d: number) => padding + (d / totalDist) * (width - 2 * padding);
  const scaleY = (e: number) => height - padding - ((e - minElev) / (maxElev - minElev)) * (height - 2 * padding);

  let pathD = `M ${scaleX(points[0].dist)},${scaleY(points[0].elev)}`;
  for (let i = 1; i < points.length; i++) pathD += ` L ${scaleX(points[i].dist)},${scaleY(points[i].elev)}`;
  const areaD = `${pathD} L ${scaleX(points[points.length - 1].dist)},${height - padding} L ${scaleX(points[0].dist)},${height - padding} Z`;

  svg.innerHTML = `
    <defs>
      <linearGradient id="elevGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#4E8CFF" stop-opacity="0.4"/>
        <stop offset="100%" stop-color="#4E8CFF" stop-opacity="0.0"/>
      </linearGradient>
    </defs>
    <line x1="${padding}" y1="${scaleY(30)}" x2="${width - padding}" y2="${scaleY(30)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>
    <line x1="${padding}" y1="${scaleY(60)}" x2="${width - padding}" y2="${scaleY(60)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>
    <path d="${areaD}" fill="url(#elevGrad)"/>
    <path d="${pathD}" fill="none" stroke="#4E8CFF" stroke-width="3" stroke-linecap="round"/>
    ${points
      .map(
        (p, idx) => `
      <circle cx="${scaleX(p.dist)}" cy="${scaleY(p.elev)}" r="4" fill="#F5A524" stroke="#ffffff" stroke-width="1.5">
        <title>Pole #${idx + 1}: ${p.dist.toFixed(0)}m, Elev: ${p.elev.toFixed(1)}m</title>
      </circle>
      <text x="${scaleX(p.dist)}" y="${scaleY(p.elev) - 10}" fill="#8B909C" font-size="10" text-anchor="middle">${p.elev.toFixed(0)}m</text>
    `
      )
      .join('')}
    <text x="${padding}" y="${height - 6}" fill="#55585F" font-size="10">0 m</text>
    <text x="${width - padding}" y="${height - 6}" fill="#55585F" font-size="10" text-anchor="end">${(totalDist / 1000).toFixed(2)} km</text>
  `;
}
```

- [ ] **Step 4: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors. `@types/leaflet` (installed in Task 1) resolves all `L.*` types.

```bash
git add web-map-next/src/lib/map
git commit -m "feat(web-map-next): port Leaflet map engine and elevation profile renderer"
```

---

### Task 9: `useProjectData` aggregate hook

**Files:**
- Create: `web-map-next/src/features/map/useProjectData.ts`

This ports the data-shaping half of `web-map/src/app.js`'s `refreshProjectData` (grouping assets by `assetType`, counting optimisable WTGs) into one hook that both `MapCanvas` and the Assets/BOM panes consume, so the grouping logic exists in exactly one place.

**Interfaces:**
- Consumes: `useProjectAssets`, `useParcels`, `useRestrictedAreas`, `useRoutes`, `useBomReport` (Task 6).
- Produces:
  ```ts
  export interface ProjectMapData {
    wtgs: FeatureCollection;
    substations: FeatureCollection;
    towers: FeatureCollection;
    referenceLines: FeatureCollection;
    parcels: FeatureCollection;
    restrictedAreas: FeatureCollection;
    routes: FeatureCollection;
    counts: {
      wtgsTotal: number;
      wtgsOptimisable: number;
      substations: number;
      towers: number;
      referenceLines: number;
      parcels: number;
      restrictedAreas: number;
    };
    bom: BomReport | undefined;
    isLoading: boolean;
  }
  export function useProjectData(projectId: string | null, jobId: string | null): ProjectMapData
  ```
  Consumed by `MapCanvas` integration (Task 10), Assets summary card (Task 13), and the BOM pane (Task 17).

- [ ] **Step 1: Implement the hook**

```ts
import { useMemo } from 'react';
import type { Feature, FeatureCollection } from 'geojson';
import { useBomReport, useParcels, useProjectAssets, useRestrictedAreas, useRoutes } from '../../lib/query';
import type { BomReport } from '../../lib/api';

export interface ProjectMapData {
  wtgs: FeatureCollection;
  substations: FeatureCollection;
  towers: FeatureCollection;
  referenceLines: FeatureCollection;
  parcels: FeatureCollection;
  restrictedAreas: FeatureCollection;
  routes: FeatureCollection;
  counts: {
    wtgsTotal: number;
    wtgsOptimisable: number;
    substations: number;
    towers: number;
    referenceLines: number;
    parcels: number;
    restrictedAreas: number;
  };
  bom: BomReport | undefined;
  isLoading: boolean;
}

function byType(fc: FeatureCollection | undefined, type: string): Feature[] {
  return (fc?.features || []).filter((f) => ((f.properties as any)?.assetType || '').toUpperCase() === type);
}

function toCollection(features: Feature[]): FeatureCollection {
  return { type: 'FeatureCollection', features };
}

export function useProjectData(projectId: string | null, jobId: string | null): ProjectMapData {
  const assetsQuery = useProjectAssets(projectId);
  const parcelsQuery = useParcels(projectId);
  const restrictedQuery = useRestrictedAreas(projectId);
  const routesQuery = useRoutes(projectId, jobId);
  const bomQuery = useBomReport(projectId);

  return useMemo(() => {
    const wtgsList = byType(assetsQuery.data, 'WTG');
    const subList = byType(assetsQuery.data, 'SUBSTATION');
    const towerList = byType(assetsQuery.data, 'EVACUATION_TOWER');
    const lineList = byType(assetsQuery.data, 'REFERENCE_LINE');
    const wtgsOptimisable = wtgsList.filter((f) => (f.properties as any)?.optimisable !== false).length;

    return {
      wtgs: toCollection(wtgsList),
      substations: toCollection(subList),
      towers: toCollection(towerList),
      referenceLines: toCollection(lineList),
      parcels: parcelsQuery.data ?? { type: 'FeatureCollection', features: [] },
      restrictedAreas: restrictedQuery.data ?? { type: 'FeatureCollection', features: [] },
      routes: routesQuery.data ?? { type: 'FeatureCollection', features: [] },
      counts: {
        wtgsTotal: wtgsList.length,
        wtgsOptimisable,
        substations: subList.length,
        towers: towerList.length,
        referenceLines: lineList.length,
        parcels: (parcelsQuery.data?.features || []).length,
        restrictedAreas: (restrictedQuery.data?.features || []).length
      },
      bom: bomQuery.data,
      isLoading: assetsQuery.isLoading || parcelsQuery.isLoading || restrictedQuery.isLoading || routesQuery.isLoading
    };
  }, [assetsQuery.data, parcelsQuery.data, restrictedQuery.data, routesQuery.data, bomQuery.data, assetsQuery.isLoading, parcelsQuery.isLoading, restrictedQuery.isLoading, routesQuery.isLoading]);
}
```

- [ ] **Step 2: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

```bash
git add web-map-next/src/features/map/useProjectData.ts
git commit -m "feat(web-map-next): add useProjectData aggregate hook"
```

---

### Task 10: `MapCanvas`, `Legend`, and map integration into `App.tsx`

**Files:**
- Create: `web-map-next/src/features/map/MapCanvas.tsx`
- Create: `web-map-next/src/features/map/Legend.tsx`
- Create: `web-map-next/src/features/map/MapAreaContent.tsx`
- Modify: `web-map-next/src/App.tsx` — replace the map placeholder with `<MapAreaContent />`

**Interfaces:**
- Consumes: `SurgeMapEngine` (Task 8), `useProjectData` (Task 9), `useUiStore` (Task 3).
- Produces:
  ```ts
  export interface MapCanvasProps {
    wtgs: FeatureCollection; substations: FeatureCollection; towers: FeatureCollection;
    referenceLines: FeatureCollection; routes: FeatureCollection; parcels: FeatureCollection;
    restrictedAreas: FeatureCollection; layerVisibility: Record<LayerName, boolean>;
    parcelOpacity: number; restrictedOpacity: number; routeEditMode: boolean;
    onRouteVertexMoved: (lengthMeters: number, poles: number, cost: number) => void;
  }
  export interface MapCanvasHandle {
    renderImportedGeoJson: (geoJson: FeatureCollection) => void;
    clearImported: () => void;
    invalidateSize: () => void;
    fitAllBounds: () => void;
  }
  ```
  `MapCanvas` (forwardRef component) and `<MapAreaContent />` — consumed by the Assets file-upload flow (Task 13, via the imperative handle) and by Task 21's final integration pass. `onRouteVertexMoved` is wired to a no-op here; Task 17 (BOM) replaces it with the live-override display.

- [ ] **Step 1: `MapCanvas.tsx`**

```tsx
import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import type { FeatureCollection } from 'geojson';
import { SurgeMapEngine } from '../../lib/map/SurgeMapEngine';
import type { LayerName } from '../../lib/store';

export interface MapCanvasProps {
  wtgs: FeatureCollection;
  substations: FeatureCollection;
  towers: FeatureCollection;
  referenceLines: FeatureCollection;
  routes: FeatureCollection;
  parcels: FeatureCollection;
  restrictedAreas: FeatureCollection;
  layerVisibility: Record<LayerName, boolean>;
  parcelOpacity: number;
  restrictedOpacity: number;
  routeEditMode: boolean;
  onRouteVertexMoved: (lengthMeters: number, poles: number, cost: number) => void;
}

export interface MapCanvasHandle {
  renderImportedGeoJson: (geoJson: FeatureCollection) => void;
  clearImported: () => void;
  invalidateSize: () => void;
  fitAllBounds: () => void;
}

const MAP_CONTAINER_ID = 'surge-leaflet-container';

export const MapCanvas = forwardRef<MapCanvasHandle, MapCanvasProps>(function MapCanvas(props, ref) {
  const engineRef = useRef<SurgeMapEngine | null>(null);

  useEffect(() => {
    engineRef.current = new SurgeMapEngine(MAP_CONTAINER_ID);
    return () => {
      engineRef.current?.map.remove();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => { engineRef.current?.renderWtgs(props.wtgs); }, [props.wtgs]);
  useEffect(() => { engineRef.current?.renderSubstations(props.substations); }, [props.substations]);
  useEffect(() => { engineRef.current?.renderTowers(props.towers); }, [props.towers]);
  useEffect(() => { engineRef.current?.renderReferenceLines(props.referenceLines); }, [props.referenceLines]);
  useEffect(() => { engineRef.current?.renderRoutes(props.routes); }, [props.routes]);
  useEffect(() => {
    engineRef.current?.renderParcels(props.parcels, props.parcelOpacity);
  }, [props.parcels, props.parcelOpacity]);
  useEffect(() => {
    engineRef.current?.renderRestrictedAreas(props.restrictedAreas, props.restrictedOpacity);
  }, [props.restrictedAreas, props.restrictedOpacity]);

  useEffect(() => {
    if (!engineRef.current) return;
    (Object.keys(props.layerVisibility) as LayerName[]).forEach((layer) => {
      engineRef.current!.setLayerVisibility(layer, props.layerVisibility[layer]);
    });
  }, [props.layerVisibility]);

  useEffect(() => {
    engineRef.current?.enableRouteEditing(props.routeEditMode, props.onRouteVertexMoved);
  }, [props.routeEditMode]);

  useImperativeHandle(
    ref,
    () => ({
      renderImportedGeoJson: (geoJson) => engineRef.current?.renderImportedGeoJson(geoJson),
      clearImported: () => engineRef.current?.clearImported(),
      invalidateSize: () => engineRef.current?.invalidateSize(),
      fitAllBounds: () => engineRef.current?.fitAllBounds()
    }),
    []
  );

  return <div id={MAP_CONTAINER_ID} className="absolute inset-0" />;
});
```

- [ ] **Step 2: `Legend.tsx`**

```tsx
export function Legend() {
  const items: { color: string; label: string; shape?: 'dash' }[] = [
    { color: 'var(--accent)', label: 'Wind turbine' },
    { color: 'var(--warning)', label: 'Substation' },
    { color: 'var(--danger)', label: 'Restricted zone' },
    { color: 'var(--accent)', label: 'Feeder route', shape: 'dash' }
  ];
  return (
    <div className="absolute right-3.5 top-3.5 w-[172px] bg-surface border border-border rounded-lg p-2.5 font-ui pointer-events-none">
      <h4 className="m-0 mb-2 text-[10.5px] uppercase tracking-wide text-textFaint font-bold">Legend</h4>
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5 py-0.5 text-[11px] text-textMuted">
          {item.shape === 'dash' ? (
            <span className="w-2.5 h-2.5 rounded-full border-2 border-dashed flex-none" style={{ borderColor: item.color }} />
          ) : (
            <span className="w-2.5 h-2.5 rounded-sm flex-none" style={{ background: item.color }} />
          )}
          {item.label}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: `MapAreaContent.tsx`** — composes `MapCanvas` + `Legend` with live project data; Tasks 17 and 20 extend this same file to add `BomStrip` and `ElevationDrawer`

```tsx
import { useEffect, useRef } from 'react';
import { useUiStore } from '../../lib/store';
import { useProjectData } from './useProjectData';
import { MapCanvas, type MapCanvasHandle } from './MapCanvas';
import { Legend } from './Legend';

export function MapAreaContent() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const layerVisibility = useUiStore((s) => s.layerVisibility);
  const parcelOpacity = useUiStore((s) => s.parcelOpacity);
  const restrictedOpacity = useUiStore((s) => s.restrictedOpacity);
  const routeEditMode = useUiStore((s) => s.routeEditMode);

  const data = useProjectData(currentProjectId, currentJobId);
  const mapRef = useRef<MapCanvasHandle>(null);

  useEffect(() => {
    if (!data.isLoading) mapRef.current?.fitAllBounds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.wtgs, data.substations, data.towers, data.referenceLines, data.parcels, data.restrictedAreas, data.routes]);

  return (
    <>
      <MapCanvas
        ref={mapRef}
        wtgs={data.wtgs}
        substations={data.substations}
        towers={data.towers}
        referenceLines={data.referenceLines}
        routes={data.routes}
        parcels={data.parcels}
        restrictedAreas={data.restrictedAreas}
        layerVisibility={layerVisibility}
        parcelOpacity={parcelOpacity}
        restrictedOpacity={restrictedOpacity}
        routeEditMode={routeEditMode}
        onRouteVertexMoved={() => {}}
      />
      <Legend />
    </>
  );
}
```

- [ ] **Step 4: Wire into `App.tsx`**

Replace the map placeholder `<div>` inside `<MapArea>` with:
```tsx
<MapArea>
  <MapAreaContent />
</MapArea>
```
and add `import { MapAreaContent } from './features/map/MapAreaContent';` to the top of `App.tsx`.

- [ ] **Step 5: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, open the preview, and confirm the map area now shows a real Leaflet dark-tile basemap centered on the Kutch site coordinates, with a zoom control top-right and the Legend card top-right below it. No project is selected yet, so no markers are expected.

```bash
git add web-map-next/src/features/map/MapCanvas.tsx web-map-next/src/features/map/Legend.tsx web-map-next/src/features/map/MapAreaContent.tsx web-map-next/src/App.tsx
git commit -m "feat(web-map-next): wire MapCanvas and Legend into the app shell"
```

---

### Task 11: Auth gateway and login

**Files:**
- Create: `web-map-next/src/features/auth/AuthGateway.tsx`
- Create: `web-map-next/src/features/auth/AuthTopBarActions.tsx`
- Modify: `web-map-next/src/app/TopBar.tsx` — accept `projectSlot` / `actionsSlot` props instead of DOM-id placeholder divs
- Modify: `web-map-next/src/App.tsx` — render `<AuthGateway />` and pass `<AuthTopBarActions />` into `TopBar`

**Interfaces:**
- Consumes: `api.login` (Task 4), `useAuthStore` (Task 3), `Button` (Task 2).
- Produces: `<AuthGateway />` (full-screen overlay, renders `null` when authenticated) and `<AuthTopBarActions />` (user badge + logout, renders `null` when not authenticated) — the `TopBar` slot props are consumed by Task 12's project selector as well.

- [ ] **Step 1: Replace `TopBar`'s placeholder divs with slot props**

Modify `web-map-next/src/app/TopBar.tsx`:
```tsx
import { ReactNode } from 'react';

interface TopBarProps {
  projectSlot?: ReactNode;
  actionsSlot?: ReactNode;
}

export function TopBar({ projectSlot, actionsSlot }: TopBarProps) {
  return (
    <header className="h-[52px] flex-none flex items-center gap-5 px-4 bg-panel border-b border-border font-ui">
      <div className="flex items-center gap-2">
        <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-accent" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
        </svg>
        <span className="font-bold tracking-wide text-sm text-text">SURGE</span>
        <span className="text-[10.5px] text-textFaint ml-2 pl-2 border-l border-borderStrong">
          Collector &amp; Evacuation Engine
        </span>
      </div>
      <div className="flex items-center gap-2">{projectSlot}</div>
      <div className="flex-1" />
      <div className="flex items-center gap-2">{actionsSlot}</div>
    </header>
  );
}
```

- [ ] **Step 2: `AuthGateway.tsx`**

```tsx
import { FormEvent, useState } from 'react';
import { api } from '../../lib/api';
import { useAuthStore } from '../../lib/store';
import { Button } from '../../components/ui';

export function AuthGateway() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const login = useAuthStore((s) => s.login);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.login(username.trim(), password.trim());
      login(res.username, res.role);
    } catch (err) {
      setError('Authentication failed: ' + (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 font-ui">
      <form onSubmit={handleSubmit} className="w-[320px] bg-panel border border-borderStrong rounded-lg p-5 flex flex-col gap-3">
        <h2 className="m-0 text-sm font-bold text-text">Sign in to SURGE</h2>
        <p className="m-0 text-[11.5px] text-textFaint">Engineering access is required to load or edit project data.</p>
        <input
          className="h-8 rounded-md border border-borderStrong bg-surface2 px-2.5 text-xs text-text outline-none focus:border-accent"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />
        <input
          className="h-8 rounded-md border border-borderStrong bg-surface2 px-2.5 text-xs text-text outline-none focus:border-accent"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {error && <div className="text-[11px] text-danger">{error}</div>}
        <Button type="submit" variant="primary" disabled={submitting} className="justify-center">
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: `AuthTopBarActions.tsx`**

```tsx
import { useAuthStore } from '../../lib/store';
import { Button } from '../../components/ui';

export function AuthTopBarActions() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const username = useAuthStore((s) => s.username);
  const role = useAuthStore((s) => s.role);
  const logout = useAuthStore((s) => s.logout);

  if (!isAuthenticated) return null;
  const cleanRole = (role || 'ENGINEER').replace('ROLE_', '');

  return (
    <>
      <span className="text-[11px] text-textMuted">
        {username || 'Engineer'} ({cleanRole})
      </span>
      <Button size="sm" onClick={logout}>Logout</Button>
    </>
  );
}
```

- [ ] **Step 4: Wire into `App.tsx`**

Add `<AuthGateway />` as a sibling of the top-level flex column, and pass `actionsSlot={<AuthTopBarActions />}` to `<TopBar />`:

```tsx
import { AuthGateway } from './features/auth/AuthGateway';
import { AuthTopBarActions } from './features/auth/AuthTopBarActions';
// ...existing imports

export default function App() {
  return (
    <div className="h-full flex flex-col font-ui text-text">
      <AuthGateway />
      <TopBar actionsSlot={<AuthTopBarActions />} />
      {/* ...rest unchanged... */}
    </div>
  );
}
```

- [ ] **Step 5: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`. With no token in `localStorage`, confirm the sign-in overlay appears over a dimmed app. Submitting bad credentials against the real backend (start it via `docker-compose up backend` or the existing dev workflow) shows the auth error text; a successful login closes the overlay and shows the username/role badge + Logout button in the top bar.

```bash
git add web-map-next/src/features/auth web-map-next/src/app/TopBar.tsx web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add auth gateway, login, and top bar user badge"
```

---

### Task 12: Project selector and new-project modal

**Files:**
- Create: `web-map-next/src/features/projects/ProjectSelector.tsx`
- Create: `web-map-next/src/features/projects/NewProjectModal.tsx`
- Modify: `web-map-next/src/App.tsx` — pass `<ProjectSelector />` into `TopBar`'s `projectSlot`

This ports `loadProjects`/`selectProject`/the new-project modal handlers from `web-map/src/app.js` (lines 103–147, 325–358), including the "auto-create a default project when none exist" fallback.

**Interfaces:**
- Consumes: `useProjects`, `useCreateProject` (Task 6), `useUiStore` (Task 3), `Select`/`Button`/`Dialog` (Task 2).
- Produces: `<ProjectSelector />` — sets `currentProjectId` in `useUiStore`, which `MapAreaContent` (Task 10) and every later feature already reads.

- [ ] **Step 1: `NewProjectModal.tsx`**

```tsx
import { useState } from 'react';
import { useUiStore } from '../../lib/store';
import { useCreateProject } from '../../lib/query';
import { Dialog, Button } from '../../components/ui';

export function NewProjectModal() {
  const open = useUiStore((s) => s.newProjectModalOpen);
  const setOpen = useUiStore((s) => s.setNewProjectModalOpen);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const createProject = useCreateProject();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  async function handleSave() {
    if (!name.trim()) return;
    const project = await createProject.mutateAsync({ name: name.trim(), description: description.trim() });
    setCurrentProjectId(project.id);
    setName('');
    setDescription('');
    setOpen(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="New Project"
      footer={
        <>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="primary" disabled={createProject.isPending || !name.trim()} onClick={handleSave}>
            {createProject.isPending ? 'Creating…' : 'Create Project'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <input
          className="h-8 rounded-md border border-borderStrong bg-surface2 px-2.5 text-xs text-text outline-none focus:border-accent"
          placeholder="Project name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <textarea
          className="rounded-md border border-borderStrong bg-surface2 px-2.5 py-2 text-xs text-text outline-none focus:border-accent resize-none h-20"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
    </Dialog>
  );
}
```

- [ ] **Step 2: `ProjectSelector.tsx`** — including the "no projects yet" auto-create fallback from the original `loadProjects`

```tsx
import { useEffect } from 'react';
import { useCreateProject, useProjects } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { Select, Button } from '../../components/ui';
import { NewProjectModal } from './NewProjectModal';

export function ProjectSelector() {
  const { data: projects = [], isSuccess } = useProjects();
  const createProject = useCreateProject();
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const setNewProjectModalOpen = useUiStore((s) => s.setNewProjectModalOpen);

  useEffect(() => {
    if (!isSuccess) return;
    if (projects.length === 0 && !createProject.isPending && !createProject.data) {
      createProject.mutate({ name: 'Default Workstation Project', description: 'Default Grid Evacuation Workspace' });
      return;
    }
    if (!currentProjectId && projects.length > 0) {
      setCurrentProjectId(projects[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuccess, projects, currentProjectId]);

  useEffect(() => {
    if (createProject.data && !currentProjectId) setCurrentProjectId(createProject.data.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createProject.data]);

  return (
    <>
      <Select
        value={currentProjectId || ''}
        onValueChange={setCurrentProjectId}
        options={projects.map((p) => ({ value: p.id, label: p.name }))}
        className="min-w-[160px]"
      />
      <Button size="sm" onClick={() => setNewProjectModalOpen(true)}>+ New</Button>
      <NewProjectModal />
    </>
  );
}
```

- [ ] **Step 3: Wire into `App.tsx`**

```tsx
import { ProjectSelector } from './features/projects/ProjectSelector';
// ...
<TopBar projectSlot={<ProjectSelector />} actionsSlot={<AuthTopBarActions />} />
```

- [ ] **Step 4: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, log in, and confirm: the project dropdown populates (or a default project is silently created if the backend has none), selecting a different project updates the map (still empty until Task 13 wires real asset data), and "+ New" opens the modal, creates a project, and switches to it.

```bash
git add web-map-next/src/features/projects web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add project selector and new-project modal"
```

---

### Task 13: Asset dropzone, import orchestration, and asset summary

**Files:**
- Create: `web-map-next/src/lib/store/uiStore.ts` — modify: add toast state
- Create: `web-map-next/src/components/Toast.tsx`
- Create: `web-map-next/src/features/assets/useAssetImport.ts`
- Create: `web-map-next/src/features/assets/AssetDropzone.tsx`
- Create: `web-map-next/src/features/assets/AssetSummary.tsx`
- Create: `web-map-next/src/features/assets/AssetsPane.tsx`
- Modify: `web-map-next/src/features/map/MapAreaContent.tsx` — accept `mapRef` as a prop instead of owning it, so `AssetsPane` can drive the same map instance
- Modify: `web-map-next/src/App.tsx` — own `mapRef`, pass it to both `MapAreaContent` and `AssetsPane`, render `<Toast />`

This ports `handleFileUpload` (`web-map/src/app.js` lines 611–784) and `showToast` (786–802). One deliberate behavior change from the original, noted for the Task 21 parity pass: instead of calling `mapEngine.renderWtgs/renderSubstations/...` directly with locally-parsed features, this port shows the raw import immediately via the additive "imported" layer (`renderImportedGeoJson`, same as before) and then invalidates the `assets`/`parcels`/`restrictedAreas` queries so `MapAreaContent`'s already-wired `useProjectData` re-renders the canonical typed layers once the backend confirms the import — avoiding a second, parallel path that writes into the map bypassing the query cache that now owns that data.

**Interfaces:**
- Consumes: `classifyGeoJsonFeature`, `ASSET_TYPES` (Task 5), `api` (Task 4), `MapCanvasHandle` (Task 10), `useUiStore` (Task 3, extended here), `Card`/`CardTitle`/`CardDescription` (Task 2), `ImportPreview` type (Task 4).
- Produces:
  - `useUiStore` gains `toast: string | null`, `showToast(message: string): void`, `clearToast(): void`.
  - `useAssetImport({ mapRef, onKmzPreview, onToast }): { handleFiles(files: FileList | File[], selectedType: AssetImportType): Promise<void>; isProcessing: boolean }` with `export type AssetImportType = 'auto' | 'wtg' | 'substation' | 'parcel' | 'restricted'`.
  - `<AssetDropzone mapRef onKmzPreview />`, `<AssetSummary />`, `<AssetsPane mapRef />` (composes both; Task 14 extends `AssetsPane` to wire the KMZ preview modal).

- [ ] **Step 1: Add toast state to `uiStore.ts`**

Add to the `UiState` interface (after `importPreviewOpen`):
```ts
  toast: string | null;
  showToast: (message: string) => void;
  clearToast: () => void;
```
Add to the `create<UiState>((set) => ({ ... }))` body (after `importPreviewOpen: false,`):
```ts
  toast: null,
  showToast: (message) => set({ toast: message }),
  clearToast: () => set({ toast: null }),
```

- [ ] **Step 2: `components/Toast.tsx`**

```tsx
import { useEffect } from 'react';
import { useUiStore } from '../lib/store';

export function Toast() {
  const toast = useUiStore((s) => s.toast);
  const clearToast = useUiStore((s) => s.clearToast);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(clearToast, 3000);
    return () => clearTimeout(timer);
  }, [toast, clearToast]);

  if (!toast) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999] bg-success text-white text-[13px] font-semibold px-5 py-2.5 rounded-lg shadow-lg">
      {toast}
    </div>
  );
}
```

- [ ] **Step 3: `useAssetImport.ts`**

```ts
import { useState } from 'react';
import type { RefObject } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Feature } from 'geojson';
import { api } from '../../lib/api';
import type { ImportPreview } from '../../lib/api';
import { ASSET_TYPES, classifyGeoJsonFeature } from '../../lib/classify';
import { useUiStore } from '../../lib/store';
import type { MapCanvasHandle } from '../map/MapCanvas';

export type AssetImportType = 'auto' | 'wtg' | 'substation' | 'parcel' | 'restricted';

interface UseAssetImportOptions {
  mapRef: RefObject<MapCanvasHandle>;
  onKmzPreview: (preview: ImportPreview) => void;
  onToast: (message: string) => void;
}

function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target!.result as string);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

export function useAssetImport({ mapRef, onKmzPreview, onToast }: UseAssetImportOptions) {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const queryClient = useQueryClient();
  const [isProcessing, setIsProcessing] = useState(false);

  async function handleFiles(files: FileList | File[], selectedType: AssetImportType) {
    const fileList = Array.from(files);
    if (fileList.length === 0) return;

    const projectId = currentProjectId || 'proj-default';
    if (!currentProjectId) setCurrentProjectId(projectId);

    const kmzFiles = fileList.filter((f) => /\.(kmz|kml)$/i.test(f.name));
    const geoJsonFiles = fileList.filter((f) => !/\.(kmz|kml)$/i.test(f.name));

    setIsProcessing(true);
    try {
      for (const file of kmzFiles) {
        try {
          const preview = await api.previewKmzAssets(projectId, file);
          onKmzPreview(preview);
        } catch (err) {
          onToast(`Import error: ${(err as Error).message || err}`);
        }
      }

      if (geoJsonFiles.length === 0) return;

      mapRef.current?.clearImported();
      const unclassified: Feature[] = [];
      let totalFeatures = 0;

      for (const file of geoJsonFiles) {
        try {
          const text = await readFileText(file);
          const geoJson = JSON.parse(text);
          const features: Feature[] = geoJson.features || (geoJson.type === 'Feature' ? [geoJson] : []);
          totalFeatures += features.length;

          mapRef.current?.renderImportedGeoJson(geoJson);

          for (const feat of features) {
            if (!feat.properties) feat.properties = {};
            const props = feat.properties as Record<string, any>;

            if (selectedType === 'wtg') props.assetType = 'WTG';
            else if (selectedType === 'substation') props.assetType = 'SUBSTATION';
            else if (selectedType === 'parcel') props.assetType = 'PARCEL';
            else if (selectedType === 'restricted') props.assetType = 'RESTRICTED';

            const geomType = feat.geometry?.type || '';
            if (geomType === 'Point' || geomType === 'MultiPoint') {
              if (selectedType === 'auto') {
                const detected = classifyGeoJsonFeature(feat).assetType;
                props.assetType = detected;
                if (detected === ASSET_TYPES.UNKNOWN) unclassified.push(feat);
              }
            } else if (geomType !== 'LineString' && geomType !== 'MultiLineString' && geomType !== 'Polygon' && geomType !== 'MultiPolygon') {
              unclassified.push(feat);
            }
          }

          if (projectId && !projectId.startsWith('proj-default')) {
            const payload = JSON.stringify(geoJson);
            const isParcel =
              selectedType === 'parcel' ||
              (selectedType === 'auto' &&
                features.some((f) => f.geometry?.type?.includes('Polygon') && !(f.properties as any)?.restrictionType));
            const isRestrictedPayload =
              selectedType === 'restricted' ||
              (selectedType === 'auto' &&
                features.some((f) => f.geometry?.type?.includes('Polygon') && (f.properties as any)?.restrictionType));

            if (isParcel) {
              api.importParcelsGeoJson(projectId, payload).catch((err) => console.warn('[Backend Import Fallback]', err));
            } else if (isRestrictedPayload) {
              api.importRestrictedAreasGeoJson(projectId, payload).catch((err) => console.warn('[Backend Import Fallback]', err));
            } else {
              api.importGeoJsonAssets(projectId, payload).catch((err) => console.warn('[Backend Import Fallback]', err));
            }
          }
        } catch (err) {
          console.error(`Failed to parse file ${file.name}:`, err);
        }
      }

      if (unclassified.length > 0) {
        const sample = unclassified
          .slice(0, 3)
          .map((f) => (f.properties as any)?.externalId || (f.properties as any)?.name || '?')
          .join(', ');
        onToast(
          `${unclassified.length} feature(s) could not be classified (${sample}${unclassified.length > 3 ? ', …' : ''}). ` +
            `Pick an asset type above and re-import, or upload as KMZ to use the preview.`
        );
      }

      mapRef.current?.invalidateSize();
      mapRef.current?.fitAllBounds();
      onToast(`Loaded ${totalFeatures} feature${totalFeatures !== 1 ? 's' : ''} from ${fileList.length} file${fileList.length !== 1 ? 's' : ''}`);

      await queryClient.invalidateQueries({ queryKey: ['assets', projectId] });
      await queryClient.invalidateQueries({ queryKey: ['parcels', projectId] });
      await queryClient.invalidateQueries({ queryKey: ['restrictedAreas', projectId] });
    } finally {
      setIsProcessing(false);
    }
  }

  return { handleFiles, isProcessing };
}
```

- [ ] **Step 4: `AssetDropzone.tsx`**

```tsx
import { ChangeEvent, DragEvent, RefObject, useRef, useState } from 'react';
import { useUiStore } from '../../lib/store';
import { Card, CardTitle, CardDescription } from '../../components/ui';
import type { ImportPreview } from '../../lib/api';
import type { MapCanvasHandle } from '../map/MapCanvas';
import { useAssetImport, type AssetImportType } from './useAssetImport';

const TYPE_OPTIONS: { value: AssetImportType; label: string }[] = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'wtg', label: 'WTGs' },
  { value: 'substation', label: 'Substation' },
  { value: 'parcel', label: 'Parcels' },
  { value: 'restricted', label: 'Restricted' }
];

interface AssetDropzoneProps {
  mapRef: RefObject<MapCanvasHandle>;
  onKmzPreview: (preview: ImportPreview) => void;
}

export function AssetDropzone({ mapRef, onKmzPreview }: AssetDropzoneProps) {
  const showToast = useUiStore((s) => s.showToast);
  const [selectedType, setSelectedType] = useState<AssetImportType>('auto');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { handleFiles, isProcessing } = useAssetImport({ mapRef, onKmzPreview, onToast: showToast });

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files, selectedType);
  }

  function onFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) handleFiles(e.target.files, selectedType);
    e.target.value = '';
  }

  return (
    <Card>
      <CardTitle>GeoJSON Ingestion</CardTitle>
      <CardDescription>Drag &amp; drop feature collections for WTGs, substations, restricted areas, or parcels.</CardDescription>
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border border-dashed rounded-md px-2.5 py-4 text-center cursor-pointer ${
          dragOver ? 'border-accent bg-accentSoft' : 'border-borderStrong bg-surface2'
        }`}
      >
        <p className="m-0 text-xs font-semibold text-text">{isProcessing ? 'Processing…' : 'Drop .geojson / .kmz / .kml'}</p>
        <span className="text-[11px] text-textFaint">or click to browse</span>
        <input ref={fileInputRef} type="file" multiple accept=".geojson,.json,.kmz,.kml" className="hidden" onChange={onFileInputChange} />
      </div>
      <div className="flex flex-wrap gap-1.5 mt-2.5">
        {TYPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setSelectedType(opt.value)}
            className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
              selectedType === opt.value ? 'bg-accent border-accent text-white' : 'bg-surface2 border-borderStrong text-textMuted'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 5: `AssetSummary.tsx` and `AssetsPane.tsx`**

`web-map-next/src/features/assets/AssetSummary.tsx`:
```tsx
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { Card, CardTitle } from '../../components/ui';

export function AssetSummary() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const { counts } = useProjectData(currentProjectId, currentJobId);

  const metrics = [
    { label: 'WTGs', value: counts.wtgsOptimisable === counts.wtgsTotal ? counts.wtgsTotal : `${counts.wtgsOptimisable}/${counts.wtgsTotal}` },
    { label: 'Substations', value: counts.substations },
    { label: 'Towers', value: counts.towers },
    { label: 'Ref. lines', value: counts.referenceLines },
    { label: 'Parcels', value: counts.parcels },
    { label: 'Restricted', value: counts.restrictedAreas }
  ];

  return (
    <Card>
      <CardTitle>Project Asset Summary</CardTitle>
      <div className="grid grid-cols-3 gap-2">
        {metrics.map((m) => (
          <div key={m.label} className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
            <div className="font-mono text-[17px] font-semibold tabular leading-none">{m.value}</div>
            <div className="text-[10px] text-textFaint mt-1">{m.label}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
```

`web-map-next/src/features/assets/AssetsPane.tsx` (Task 14 replaces the `onKmzPreview` no-op with real modal wiring):
```tsx
import type { RefObject } from 'react';
import type { MapCanvasHandle } from '../map/MapCanvas';
import { AssetDropzone } from './AssetDropzone';
import { AssetSummary } from './AssetSummary';

interface AssetsPaneProps {
  mapRef: RefObject<MapCanvasHandle>;
}

export function AssetsPane({ mapRef }: AssetsPaneProps) {
  return (
    <>
      <AssetDropzone mapRef={mapRef} onKmzPreview={() => {}} />
      <AssetSummary />
    </>
  );
}
```

- [ ] **Step 6: Lift `mapRef` up into `App.tsx`**

Modify `web-map-next/src/features/map/MapAreaContent.tsx` to accept `mapRef` as a prop instead of creating its own:
```tsx
import { useEffect } from 'react';
import type { RefObject } from 'react';
import { useUiStore } from '../../lib/store';
import { useProjectData } from './useProjectData';
import { MapCanvas, type MapCanvasHandle } from './MapCanvas';
import { Legend } from './Legend';

interface MapAreaContentProps {
  mapRef: RefObject<MapCanvasHandle>;
}

export function MapAreaContent({ mapRef }: MapAreaContentProps) {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const layerVisibility = useUiStore((s) => s.layerVisibility);
  const parcelOpacity = useUiStore((s) => s.parcelOpacity);
  const restrictedOpacity = useUiStore((s) => s.restrictedOpacity);
  const routeEditMode = useUiStore((s) => s.routeEditMode);

  const data = useProjectData(currentProjectId, currentJobId);

  useEffect(() => {
    if (!data.isLoading) mapRef.current?.fitAllBounds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.wtgs, data.substations, data.towers, data.referenceLines, data.parcels, data.restrictedAreas, data.routes]);

  return (
    <>
      <MapCanvas
        ref={mapRef}
        wtgs={data.wtgs}
        substations={data.substations}
        towers={data.towers}
        referenceLines={data.referenceLines}
        routes={data.routes}
        parcels={data.parcels}
        restrictedAreas={data.restrictedAreas}
        layerVisibility={layerVisibility}
        parcelOpacity={parcelOpacity}
        restrictedOpacity={restrictedOpacity}
        routeEditMode={routeEditMode}
        onRouteVertexMoved={() => {}}
      />
      <Legend />
    </>
  );
}
```

Replace `web-map-next/src/App.tsx` with:
```tsx
import { useRef } from 'react';
import { TopBar } from './app/TopBar';
import { RailNav } from './app/RailNav';
import { SidePanel, Pane } from './app/SidePanel';
import { MapArea } from './app/MapArea';
import { AuthGateway } from './features/auth/AuthGateway';
import { AuthTopBarActions } from './features/auth/AuthTopBarActions';
import { ProjectSelector } from './features/projects/ProjectSelector';
import { AssetsPane } from './features/assets/AssetsPane';
import { MapAreaContent } from './features/map/MapAreaContent';
import type { MapCanvasHandle } from './features/map/MapCanvas';
import { Toast } from './components/Toast';

export default function App() {
  const mapRef = useRef<MapCanvasHandle>(null);

  return (
    <div className="h-full flex flex-col font-ui text-text">
      <AuthGateway />
      <Toast />
      <TopBar projectSlot={<ProjectSelector />} actionsSlot={<AuthTopBarActions />} />
      <div className="flex-1 flex min-h-0">
        <RailNav />
        <SidePanel>
          <Pane tab="assets"><AssetsPane mapRef={mapRef} /></Pane>
          <Pane tab="optimize"><div className="text-textFaint text-xs">Optimization pane — Task 15</div></Pane>
          <Pane tab="layers"><div className="text-textFaint text-xs">Layers pane — Task 16</div></Pane>
          <Pane tab="bom"><div className="text-textFaint text-xs">BOM pane — Task 17</div></Pane>
          <Pane tab="audit"><div className="text-textFaint text-xs">Audit pane — Task 18</div></Pane>
        </SidePanel>
        <MapArea>
          <MapAreaContent mapRef={mapRef} />
        </MapArea>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, log in, select a project, and drag a sample `.geojson` file (points/lines/polygons) onto the dropzone. Confirm: the imported layer renders immediately on the map, a toast appears with the feature count, the asset summary metrics update after the query invalidation resolves, and dropping a file with unclassifiable points shows the "could not be classified" toast.

```bash
git add web-map-next/src/lib/store/uiStore.ts web-map-next/src/components/Toast.tsx web-map-next/src/features/assets web-map-next/src/features/map/MapAreaContent.tsx web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add asset dropzone, import orchestration, and asset summary"
```

---

### Task 14: KMZ/KML import preview modal

**Files:**
- Create: `web-map-next/src/features/assets/ImportPreviewModal.tsx`
- Modify: `web-map-next/src/features/assets/AssetsPane.tsx` — hold `preview` state, wire it to `AssetDropzone.onKmzPreview` and render the modal

This ports `openImportPreview` / `applyTypeToVisibleRows` / `commitImportPreview` (`web-map/src/app.js` lines 447–600).

**Interfaces:**
- Consumes: `ImportPreview`/`ImportPreviewFeature` types (Task 4), `useCommitImport` (Task 6), `ASSET_TYPES`/`ASSET_TYPE_LABELS`/`LINE_TYPES`/`LINE_TYPE_LABELS` (Task 5), `Dialog`/`Button`/`Select` (Task 2), `useUiStore.showToast` (Task 13).
- Produces: `<ImportPreviewModal preview={preview} onClose={...} />`.

- [ ] **Step 1: `ImportPreviewModal.tsx`**

```tsx
import { useState } from 'react';
import { Dialog, Button, Select } from '../../components/ui';
import { ASSET_TYPES, ASSET_TYPE_LABELS, LINE_TYPES, LINE_TYPE_LABELS } from '../../lib/classify';
import { useCommitImport } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import type { ImportPreview } from '../../lib/api';

interface ImportPreviewModalProps {
  preview: ImportPreview | null;
  onClose: () => void;
}

const GEOMETRY_GLYPH: Record<string, string> = { Point: '●', LineString: '╱', Polygon: '▭' };

export function ImportPreviewModal({ preview, onClose }: ImportPreviewModalProps) {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);
  const commitImport = useCommitImport(currentProjectId);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [bulkType, setBulkType] = useState('');
  const [defaultCapacity, setDefaultCapacity] = useState('');

  if (!preview) return null;

  const counts = preview.countsByType || {};
  const unknownCount = counts.UNKNOWN || 0;
  const skipped = preview.skippedByGeometry || {};
  const skippedTotal = Object.values(skipped).reduce((sum, n) => sum + n, 0);

  const notes: string[] = [];
  if ((preview.duplicatesRemoved || 0) > 0) {
    notes.push(`${preview.duplicatesRemoved} duplicate placemark(s) removed — this file repeats its own folder tree.`);
  }
  if (skippedTotal > 0) {
    const detail = Object.entries(skipped).map(([type, n]) => `${n} ${type}`).join(', ');
    notes.push(`${skippedTotal} non-point feature(s) not imported as assets (${detail}).`);
  }
  if (unknownCount > 0) {
    notes.push(`${unknownCount} feature(s) could not be classified and will be skipped unless you assign a type.`);
  }

  function setOverride(externalId: string, type: string) {
    setOverrides((prev) => ({ ...prev, [externalId]: type }));
  }

  function applyBulk() {
    if (!bulkType || !preview) return;
    const next: Record<string, string> = {};
    for (const feature of preview.features) next[feature.externalId] = bulkType;
    setOverrides(next);
  }

  async function handleCommit() {
    if (!preview) return;
    try {
      const result = await commitImport.mutateAsync({
        importId: preview.importId,
        overrides,
        defaultCapacityMw: defaultCapacity ? parseFloat(defaultCapacity) : null,
        skipUnclassified: true
      });
      const parts: string[] = [];
      if (result.wtgsImported) parts.push(`${result.wtgsImported} turbines`);
      if (result.substationsImported) parts.push(`${result.substationsImported} substations`);
      if (result.towersImported) parts.push(`${result.towersImported} towers`);
      if (result.unclassified) parts.push(`${result.unclassified} skipped`);
      showToast(`Imported ${parts.join(', ') || 'nothing'}`);
      setOverrides({});
      onClose();
    } catch (err) {
      showToast(`Import failed: ${(err as Error).message || err}`);
    }
  }

  return (
    <Dialog
      open={!!preview}
      onOpenChange={(open) => { if (!open) onClose(); }}
      title={`Import Preview — ${preview.fileName || 'Uploaded file'}`}
      widthClassName="w-[680px]"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={commitImport.isPending} onClick={handleCommit}>
            {commitImport.isPending ? 'Importing…' : 'Confirm Import'}
          </Button>
        </>
      }
    >
      <div className="flex flex-wrap gap-1.5 mb-2.5">
        {Object.entries(counts)
          .filter(([, count]) => count > 0)
          .map(([type, count]) => (
            <div key={type} className="text-[11px] font-semibold px-2 py-1 rounded-full bg-surface2 border border-border text-textMuted">
              <strong className="text-text">{count}</strong> {ASSET_TYPE_LABELS[type as keyof typeof ASSET_TYPE_LABELS] || type}
            </div>
          ))}
      </div>
      {notes.length > 0 && (
        <div className="flex flex-col gap-1 mb-2.5">
          {notes.map((note, i) => (
            <div key={i} className="text-[11px] text-warning">{note}</div>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mb-2.5">
        <Select
          value={bulkType}
          onValueChange={setBulkType}
          options={Object.keys(ASSET_TYPES).map((t) => ({ value: t, label: ASSET_TYPE_LABELS[t as keyof typeof ASSET_TYPE_LABELS] }))}
          className="min-w-[160px]"
        />
        <Button size="sm" onClick={applyBulk}>Apply to all rows</Button>
        <input
          className="h-[26px] w-[120px] rounded-md border border-borderStrong bg-surface2 px-2 text-[11px] text-text outline-none focus:border-accent"
          placeholder="Default MW"
          value={defaultCapacity}
          onChange={(e) => setDefaultCapacity(e.target.value)}
        />
      </div>
      <div className="overflow-x-auto border border-border rounded-md">
        <table className="w-full text-[11px] border-collapse">
          <thead>
            <tr className="bg-surface2 text-textFaint uppercase tracking-wide text-[10px]">
              <th className="text-left px-2 py-1.5">Geom</th>
              <th className="text-left px-2 py-1.5">Name</th>
              <th className="text-left px-2 py-1.5">Folder</th>
              <th className="text-left px-2 py-1.5">Type</th>
              <th className="text-left px-2 py-1.5">Status</th>
              <th className="text-left px-2 py-1.5">Rule</th>
            </tr>
          </thead>
          <tbody>
            {preview.features.map((feature) => {
              const isLine = feature.geometryType === 'LineString';
              const currentValue = overrides[feature.externalId] ?? (isLine ? feature.lineType : feature.classifiedAs) ?? 'UNKNOWN';
              const options = isLine
                ? Object.keys(LINE_TYPES).map((t) => ({ value: t, label: LINE_TYPE_LABELS[t as keyof typeof LINE_TYPE_LABELS] }))
                : Object.keys(ASSET_TYPES).map((t) => ({ value: t, label: ASSET_TYPE_LABELS[t as keyof typeof ASSET_TYPE_LABELS] }));
              const unresolved = feature.classifiedAs === 'UNKNOWN' || (isLine && feature.lineType === 'UNKNOWN');
              return (
                <tr key={feature.externalId} className={unresolved ? 'bg-dangerSoft' : ''}>
                  <td className="px-2 py-1 text-textFaint" title={feature.geometryType}>{GEOMETRY_GLYPH[feature.geometryType] || '?'}</td>
                  <td className="px-2 py-1 text-text">{feature.externalId || <em>unnamed</em>}</td>
                  <td className="px-2 py-1 text-textFaint">{feature.kmlFolder || '—'}</td>
                  <td className="px-2 py-1">
                    <Select value={currentValue} onValueChange={(v) => setOverride(feature.externalId, v)} options={options} className="h-6 text-[11px]" />
                  </td>
                  <td className="px-2 py-1 text-textFaint">{feature.status && feature.status !== 'UNKNOWN' ? feature.status.replace(/_/g, ' ') : '—'}</td>
                  <td className="px-2 py-1 text-textFaint" title={feature.evidence || ''}>{feature.matchedRule.replace(/_/g, ' ').toLowerCase()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Dialog>
  );
}
```

- [ ] **Step 2: Wire preview state into `AssetsPane.tsx`**

Replace `web-map-next/src/features/assets/AssetsPane.tsx` with:
```tsx
import { useState } from 'react';
import type { RefObject } from 'react';
import type { MapCanvasHandle } from '../map/MapCanvas';
import type { ImportPreview } from '../../lib/api';
import { AssetDropzone } from './AssetDropzone';
import { AssetSummary } from './AssetSummary';
import { ImportPreviewModal } from './ImportPreviewModal';

interface AssetsPaneProps {
  mapRef: RefObject<MapCanvasHandle>;
}

export function AssetsPane({ mapRef }: AssetsPaneProps) {
  const [preview, setPreview] = useState<ImportPreview | null>(null);

  return (
    <>
      <AssetDropzone mapRef={mapRef} onKmzPreview={setPreview} />
      <AssetSummary />
      <ImportPreviewModal preview={preview} onClose={() => setPreview(null)} />
    </>
  );
}
```

- [ ] **Step 3: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, log in, select a project, and drag a sample `.kmz`/`.kml` file with mixed turbines/towers/substations onto the dropzone. Confirm: the preview modal opens with per-type count chips, a table row per feature with a working type `Select`, "Apply to all rows" bulk-overrides every row, and "Confirm Import" commits, shows a toast with the import counts, closes the modal, and the map/asset summary refresh via the invalidated queries.

```bash
git add web-map-next/src/features/assets/ImportPreviewModal.tsx web-map-next/src/features/assets/AssetsPane.tsx
git commit -m "feat(web-map-next): add KMZ/KML import preview modal"
```

---

### Task 15: Optimization form and job progress

**Files:**
- Create: `web-map-next/src/features/optimization/useJobProgress.ts`
- Create: `web-map-next/src/features/optimization/OptimizationPane.tsx`
- Modify: `web-map-next/src/App.tsx` — replace the `optimize` `Pane` placeholder with `<OptimizationPane />`

Ports the optimization-parameter sliders, `runOptimization`, and SSE progress handling (`web-map/src/app.js` lines 230–247, 804–870). Slider min/max ranges below are reasonable defaults centered on the API's own defaults (20 MW / 150 m / 33 kV, from `web-map/src/api.js` `runOptimization`); confirm them against `web-map/index.html`'s actual `<input type="range">` attributes during the Task 21 parity pass and adjust if they differ.

**Interfaces:**
- Consumes: `useRunOptimization` (Task 6), `api.listenJobProgress` (Task 4), `Card`/`CardTitle`/`Select`/`Slider`/`Button` (Task 2), `useUiStore` (Task 3).
- Produces: `useJobProgress(projectId, jobId, onComplete): JobProgress | null`, `<OptimizationPane />`.

- [ ] **Step 1: `useJobProgress.ts`**

```ts
import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import type { JobProgress } from '../../lib/api';

export function useJobProgress(projectId: string | null, jobId: string | null, onComplete: () => void) {
  const [progress, setProgress] = useState<JobProgress | null>(null);

  useEffect(() => {
    if (!projectId || !jobId) {
      setProgress(null);
      return;
    }
    setProgress({ status: 'RUNNING', progressPercent: 10, message: 'Initializing optimization job request...' });
    const stop = api.listenJobProgress(
      projectId,
      jobId,
      (data) => setProgress(data),
      (err) => setProgress({ status: 'FAILED', message: err.message }),
      () => {
        setProgress({ status: 'COMPLETED', progressPercent: 100, message: 'Optimization completed cleanly!' });
        onComplete();
      }
    );
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, jobId]);

  return progress;
}
```

- [ ] **Step 2: `OptimizationPane.tsx`**

```tsx
import { useState } from 'react';
import { Card, CardTitle, Select, Slider, Button } from '../../components/ui';
import { useRunOptimization } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { useJobProgress } from './useJobProgress';

const SCENARIOS = [
  { value: 'Balanced', label: 'Balanced (cost + environment)' },
  { value: 'Minimum Cost', label: 'Minimum Cost' },
  { value: 'Minimum Land Impact', label: 'Minimum Land Impact' },
  { value: 'Minimum Environmental Impact', label: 'Minimum Environmental Impact' }
];

export function OptimizationPane() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const setCurrentJobId = useUiStore((s) => s.setCurrentJobId);
  const showToast = useUiStore((s) => s.showToast);

  const [scenario, setScenario] = useState('Balanced');
  const [feederCapacityMw, setFeederCapacityMw] = useState(20.0);
  const [maxSpanMeters, setMaxSpanMeters] = useState(150);
  const [voltageKv, setVoltageKv] = useState(33.0);

  const runOptimization = useRunOptimization(currentProjectId);
  const progress = useJobProgress(currentProjectId, currentJobId, () => {
    showToast('Optimization completed cleanly!');
  });

  async function handleRun() {
    if (!currentProjectId) {
      showToast('Please select a project first.');
      return;
    }
    try {
      const job = await runOptimization.mutateAsync({ scenario, feederCapacityMw, maxSpanMeters, voltageKv });
      setCurrentJobId(job.id);
    } catch (err) {
      showToast('Optimization failed: ' + (err as Error).message);
    }
  }

  const isRunning = progress != null && progress.status !== 'COMPLETED' && progress.status !== 'FAILED';

  return (
    <Card>
      <CardTitle>Scenario &amp; Algorithm</CardTitle>
      <div className="flex flex-col gap-3">
        <div>
          <label className="block text-[11.5px] text-textMuted mb-1.5">Optimization scenario</label>
          <Select value={scenario} onValueChange={setScenario} options={SCENARIOS} className="w-full" />
        </div>
        <div>
          <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
            Feeder capacity <span className="font-mono text-text tabular">{feederCapacityMw.toFixed(1)} MW</span>
          </label>
          <Slider value={feederCapacityMw} onValueChange={setFeederCapacityMw} min={5} max={50} step={0.5} />
        </div>
        <div>
          <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
            Max pole span <span className="font-mono text-text tabular">{maxSpanMeters.toFixed(0)} m</span>
          </label>
          <Slider value={maxSpanMeters} onValueChange={setMaxSpanMeters} min={50} max={300} step={10} />
        </div>
        <div>
          <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
            System voltage <span className="font-mono text-text tabular">{voltageKv.toFixed(1)} kV</span>
          </label>
          <Slider value={voltageKv} onValueChange={setVoltageKv} min={11} max={66} step={0.5} />
        </div>
        <Button variant="primary" className="justify-center" disabled={isRunning || runOptimization.isPending} onClick={handleRun}>
          {isRunning ? 'Running…' : 'Run optimization pipeline'}
        </Button>
        {progress && (
          <div className="mt-1">
            <div className="h-1.5 rounded-full bg-surface2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${progress.status === 'FAILED' ? 'bg-danger' : 'bg-accent'}`}
                style={{ width: `${progress.progressPercent ?? 10}%` }}
              />
            </div>
            <p className="text-[11px] text-textFaint mt-1.5">{progress.message}</p>
          </div>
        )}
      </div>
    </Card>
  );
}
```

- [ ] **Step 3: Wire into `App.tsx`**

Replace the `optimize` `Pane` placeholder:
```tsx
<Pane tab="optimize"><OptimizationPane /></Pane>
```
and add `import { OptimizationPane } from './features/optimization/OptimizationPane';`.

- [ ] **Step 4: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, log in, select a project with imported WTGs, adjust the sliders (confirm the mono numeral badges update live), and click "Run optimization pipeline." Confirm the progress bar advances and the status message updates as SSE events arrive, ending in "Optimization completed cleanly!" and a toast.

```bash
git add web-map-next/src/features/optimization web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add optimization form and job progress"
```

---

### Task 16: Layer controls pane

**Files:**
- Create: `web-map-next/src/features/layers/LayersPane.tsx`
- Modify: `web-map-next/src/App.tsx` — replace the `layers` `Pane` placeholder with `<LayersPane />`

Ports the layer checkboxes, opacity sliders, and route-edit toggle (`web-map/src/app.js` lines 249–303).

**Interfaces:**
- Consumes: `useUiStore` (Task 3, `layerVisibility`/`toggleLayer`/`parcelOpacity`/`restrictedOpacity`/`routeEditMode`), `Card`/`CardTitle`/`Switch`/`Slider` (Task 2).
- Produces: `<LayersPane />` — purely reads/writes `useUiStore`; `MapCanvas` (Task 10) already reacts to these fields.

- [ ] **Step 1: `LayersPane.tsx`**

```tsx
import { Card, CardTitle, Switch, Slider } from '../../components/ui';
import { useUiStore, type LayerName } from '../../lib/store';

const LAYER_TOGGLES: { key: LayerName; label: string }[] = [
  { key: 'wtgs', label: 'Wind turbines' },
  { key: 'substations', label: 'Substations' },
  { key: 'towers', label: 'Evacuation towers' },
  { key: 'referenceLines', label: 'Reference lines' },
  { key: 'routes', label: 'Feeder routes' },
  { key: 'restricted', label: 'Restricted zones' }
];

export function LayersPane() {
  const layerVisibility = useUiStore((s) => s.layerVisibility);
  const toggleLayer = useUiStore((s) => s.toggleLayer);
  const parcelOpacity = useUiStore((s) => s.parcelOpacity);
  const setParcelOpacity = useUiStore((s) => s.setParcelOpacity);
  const restrictedOpacity = useUiStore((s) => s.restrictedOpacity);
  const setRestrictedOpacity = useUiStore((s) => s.setRestrictedOpacity);
  const routeEditMode = useUiStore((s) => s.routeEditMode);
  const setRouteEditMode = useUiStore((s) => s.setRouteEditMode);

  return (
    <>
      <Card>
        <CardTitle>Map Layer Controls</CardTitle>
        {LAYER_TOGGLES.map((item) => (
          <div key={item.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-b-0">
            <span className="text-xs text-text">{item.label}</span>
            <Switch checked={layerVisibility[item.key]} onCheckedChange={() => toggleLayer(item.key)} />
          </div>
        ))}
      </Card>
      <Card>
        <CardTitle>Polygon Opacity</CardTitle>
        <div className="flex flex-col gap-3">
          <div>
            <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
              Parcels <span className="font-mono text-text tabular">{parcelOpacity.toFixed(2)}</span>
            </label>
            <Slider value={parcelOpacity} onValueChange={setParcelOpacity} min={0} max={1} step={0.05} />
          </div>
          <div>
            <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
              Restricted areas <span className="font-mono text-text tabular">{restrictedOpacity.toFixed(2)}</span>
            </label>
            <Slider value={restrictedOpacity} onValueChange={setRestrictedOpacity} min={0} max={1} step={0.05} />
          </div>
        </div>
      </Card>
      <Card>
        <div className="flex items-center justify-between">
          <span className="text-xs text-text">Interactive route editing</span>
          <Switch checked={routeEditMode} onCheckedChange={setRouteEditMode} />
        </div>
        <p className="text-[11px] text-textFaint mt-1.5 mb-0">Drag route vertices on the map; BOM totals update live while enabled.</p>
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Wire into `App.tsx`**

```tsx
<Pane tab="layers"><LayersPane /></Pane>
```
and add `import { LayersPane } from './features/layers/LayersPane';`.

- [ ] **Step 3: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, open the Layers pane, and confirm: toggling each switch shows/hides the corresponding map layer, dragging the opacity sliders visibly changes parcel/restricted-area fill on the map, and toggling "Interactive route editing" adds/removes the draggable orange vertex handles on any rendered route.

```bash
git add web-map-next/src/features/layers web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add layer visibility, opacity, and route-edit controls"
```

---

### Task 17: BOM strip, BOM pane, and report exports

**Files:**
- Create: `web-map-next/src/lib/store/uiStore.ts` — modify: add `liveBomOverride` state
- Create: `web-map-next/src/features/bom/BomStrip.tsx`
- Create: `web-map-next/src/features/bom/BomPane.tsx`
- Create: `web-map-next/src/features/bom/ExportPdfButton.tsx`
- Modify: `web-map-next/src/features/map/MapAreaContent.tsx` — render `<BomStrip />` and wire `onRouteVertexMoved` to `setLiveBomOverride`
- Modify: `web-map-next/src/App.tsx` — replace the `bom` `Pane` placeholder with `<BomPane />`, add `<ExportPdfButton />` to the top bar `actionsSlot`

Ports `updateBomReport` (`web-map/src/app.js` lines 872–888), the CSV/PDF export button handlers (310–322), and the live BOM values that update while dragging a route vertex (297–302).

**Interfaces:**
- Consumes: `useProjectData` (Task 9, `bom` field), `api.getBomCsvUrl`/`getPdfReportUrl` (Task 4), `useUiStore` (Task 3, extended here).
- Produces:
  - `useUiStore` gains `liveBomOverride: { lengthKm: string; poles: number; cost: number } | null` and `setLiveBomOverride(v): void`.
  - `<BomStrip />` (floating map overlay), `<BomPane />` (side panel tab), `<ExportPdfButton />` (top bar action).

- [ ] **Step 1: Add `liveBomOverride` to `uiStore.ts`**

Add to the `UiState` interface (after the `toast` fields from Task 13):
```ts
  liveBomOverride: { lengthKm: string; poles: number; cost: number } | null;
  setLiveBomOverride: (v: { lengthKm: string; poles: number; cost: number } | null) => void;
```
Add to the store body:
```ts
  liveBomOverride: null,
  setLiveBomOverride: (v) => set({ liveBomOverride: v }),
```

- [ ] **Step 2: `BomStrip.tsx`**

```tsx
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';

export function BomStrip() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const liveOverride = useUiStore((s) => s.liveBomOverride);
  const { bom } = useProjectData(currentProjectId, currentJobId);

  const lengthKm = liveOverride ? liveOverride.lengthKm : bom ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
  const poles = liveOverride ? liveOverride.poles : bom?.totalPoles ?? 0;
  const cost = liveOverride ? liveOverride.cost : bom?.totalEstimatedCost ?? 0;
  const losses = bom?.totalElectricalLossesKw ?? 0;

  const segments = [
    { label: 'Network length', value: `${lengthKm} km` },
    { label: 'Poles', value: String(poles) },
    { label: 'Est. CapEx', value: `$${cost.toLocaleString()}` },
    { label: 'Losses', value: `${losses.toFixed(2)} kW` }
  ];

  return (
    <div className="absolute left-3.5 bottom-3.5 flex rounded-lg overflow-hidden font-ui">
      {segments.map((seg, i) => (
        <div
          key={seg.label}
          className={`bg-panel border border-borderStrong px-4 py-2.5 flex flex-col gap-0.5 min-w-[88px] ${i > 0 ? 'border-l-0' : ''}`}
        >
          <span className="font-mono font-bold text-[13.5px] tabular">{seg.value}</span>
          <span className="text-[9.5px] uppercase tracking-wide text-textFaint">{seg.label}</span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: `BomPane.tsx` and `ExportPdfButton.tsx`**

`web-map-next/src/features/bom/BomPane.tsx`:
```tsx
import { Card, CardTitle, Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';

export function BomPane() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const showToast = useUiStore((s) => s.showToast);
  const { bom } = useProjectData(currentProjectId, currentJobId);

  function downloadCsv() {
    if (!currentProjectId) return showToast('Select a project first.');
    window.open(api.getBomCsvUrl(currentProjectId, currentJobId), '_blank');
  }
  function downloadPdf() {
    if (!currentProjectId) return showToast('Select a project first.');
    window.open(api.getPdfReportUrl(currentProjectId), '_blank');
  }

  const lengthKm = bom ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
  const cost = bom?.totalEstimatedCost?.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) ?? '$0.00';
  const losses = bom?.totalElectricalLossesKw?.toFixed(2) ?? '0.00';

  return (
    <Card>
      <CardTitle>Bill of Materials</CardTitle>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{lengthKm} km</div>
          <div className="text-[10px] text-textFaint mt-1">Network length</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{bom?.totalPoles ?? 0}</div>
          <div className="text-[10px] text-textFaint mt-1">Poles</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{cost}</div>
          <div className="text-[10px] text-textFaint mt-1">Est. CapEx</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{losses} kW</div>
          <div className="text-[10px] text-textFaint mt-1">Losses</div>
        </div>
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={downloadCsv} className="flex-1 justify-center">Export CSV</Button>
        <Button size="sm" onClick={downloadPdf} className="flex-1 justify-center">Export PDF</Button>
      </div>
    </Card>
  );
}
```

`web-map-next/src/features/bom/ExportPdfButton.tsx`:
```tsx
import { Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { api } from '../../lib/api';

export function ExportPdfButton() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);

  return (
    <Button
      size="sm"
      onClick={() => {
        if (!currentProjectId) return showToast('Please select a project first.');
        window.open(api.getPdfReportUrl(currentProjectId), '_blank');
      }}
    >
      Export PDF
    </Button>
  );
}
```

- [ ] **Step 4: Wire `BomStrip` and the live-override callback into `MapAreaContent.tsx`**

Add `import { BomStrip } from '../bom/BomStrip';`, read `setLiveBomOverride` from `useUiStore`, replace `onRouteVertexMoved={() => {}}` with:
```tsx
onRouteVertexMoved={(lengthMeters, poles, cost) =>
  setLiveBomOverride({ lengthKm: (lengthMeters / 1000).toFixed(2), poles, cost })
}
```
and render `<BomStrip />` as a sibling of `<Legend />` in the returned JSX.

- [ ] **Step 5: Wire `BomPane` and `ExportPdfButton` into `App.tsx`**

```tsx
<Pane tab="bom"><BomPane /></Pane>
```
and in the `TopBar` `actionsSlot`:
```tsx
<TopBar
  projectSlot={<ProjectSelector />}
  actionsSlot={<><ExportPdfButton /><AuthTopBarActions /></>}
/>
```
Add the corresponding imports (`BomPane`, `ExportPdfButton`).

- [ ] **Step 6: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, run an optimization job to completion, and confirm: the floating BOM strip on the map and the BOM pane both show matching totals, enabling route-edit mode and dragging a vertex updates both live, and the CSV/PDF export buttons (in both the BOM pane and the top bar) open the correct backend URLs in a new tab.

```bash
git add web-map-next/src/lib/store/uiStore.ts web-map-next/src/features/bom web-map-next/src/features/map/MapAreaContent.tsx web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add BOM strip, BOM pane, and report exports"
```

---

### Task 18: Audit log pane

**Files:**
- Create: `web-map-next/src/features/audit/AuditPane.tsx`
- Modify: `web-map-next/src/App.tsx` — replace the `audit` `Pane` placeholder with `<AuditPane />`

Ports `loadAuditLogs` (`web-map/src/app.js` lines 967–996).

**Interfaces:**
- Consumes: `useAuditLogs` (Task 6), `Card`/`Button` (Task 2).
- Produces: `<AuditPane />`.

- [ ] **Step 1: `AuditPane.tsx`**

```tsx
import { Card, Button } from '../../components/ui';
import { useAuditLogs } from '../../lib/query';

export function AuditPane() {
  const { data: logs = [], isLoading, isError, refetch } = useAuditLogs();

  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <h3 className="m-0 text-[11.5px] font-bold uppercase tracking-wide text-textMuted">Audit Log</h3>
        <Button size="sm" onClick={() => refetch()}>Refresh</Button>
      </div>
      {isLoading && <div className="text-[11px] text-textFaint">Loading…</div>}
      {isError && <div className="text-[11px] text-danger">Failed to load audit logs.</div>}
      {!isLoading && !isError && logs.length === 0 && (
        <div className="text-[11px] text-textFaint">No audit logs recorded yet.</div>
      )}
      <div className="flex flex-col gap-2">
        {logs.map((log, i) => (
          <div key={i} className="border-b border-border pb-2 last:border-b-0">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-text font-semibold">{log.username || 'anonymous'}</span>
              <span className="text-textMuted">{log.action}</span>
            </div>
            <div className="text-[11px] text-textFaint">{log.details || log.resourceType}</div>
            <div className="text-[10px] text-textFaint mt-0.5">
              {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Wire into `App.tsx`**

```tsx
<Pane tab="audit"><AuditPane /></Pane>
```
and add `import { AuditPane } from './features/audit/AuditPane';`.

- [ ] **Step 3: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, open the Audit tab, and confirm the log list loads (or shows the empty state) and "Refresh" re-fetches.

```bash
git add web-map-next/src/features/audit web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add audit log pane"
```

---

### Task 19: Scenario comparison modal

**Files:**
- Create: `web-map-next/src/lib/store/uiStore.ts` — modify: add `routeColorOverride` state
- Create: `web-map-next/src/features/scenarios/CompareScenariosButton.tsx`
- Create: `web-map-next/src/features/scenarios/ScenarioComparisonModal.tsx`
- Modify: `web-map-next/src/features/map/MapCanvas.tsx` — accept and apply `routeColorOverride`
- Modify: `web-map-next/src/features/map/MapAreaContent.tsx` — read `routeColorOverride` from the store and pass it through
- Modify: `web-map-next/src/App.tsx` — add `<CompareScenariosButton />` to the top bar actions and render `<ScenarioComparisonModal />`

Ports `loadScenarioComparison` and its "Overlay Map Route" action (`web-map/src/app.js` lines 149–163, 890–965). The overlay recolors the routes already loaded for the current job in place (via a `routeColorOverride` store field consumed by `MapCanvas`) rather than re-fetching `getRoutesGeoJson(projectId)` with no `jobId` the way the original click handler did — that original call always resolved to an empty collection (`getRoutesGeoJson` only returns data when a `jobId` is passed; see `web-map/src/api.js` lines 186–196), so it never actually changed what was on the map. Recoloring the current job's already-rendered routes is what the feature visibly did in practice. Flag this to the user during the Task 21 parity pass in case the empty-fetch was masking a real bug worth fixing on the backend instead.

**Interfaces:**
- Consumes: `useScenarioComparison` (Task 6), `useUiStore` (Task 3), `Dialog`/`Button` (Task 2).
- Produces: `useUiStore` gains `routeColorOverride: string | null` and `setRouteColorOverride(v): void`; `<CompareScenariosButton />`, `<ScenarioComparisonModal />`.

- [ ] **Step 1: Add `routeColorOverride` to `uiStore.ts`**

Add to `UiState` (after `liveBomOverride` from Task 17):
```ts
  routeColorOverride: string | null;
  setRouteColorOverride: (v: string | null) => void;
```
Add to the store body:
```ts
  routeColorOverride: null,
  setRouteColorOverride: (v) => set({ routeColorOverride: v }),
```

- [ ] **Step 2: Apply `routeColorOverride` in `MapCanvas.tsx`**

Add `routeColorOverride: string | null;` to `MapCanvasProps`, and replace the existing routes effect:
```tsx
useEffect(() => { engineRef.current?.renderRoutes(props.routes); }, [props.routes]);
```
with:
```tsx
useEffect(() => {
  engineRef.current?.renderRoutes(props.routes, props.routeColorOverride);
}, [props.routes, props.routeColorOverride]);
```

- [ ] **Step 3: `CompareScenariosButton.tsx`**

```tsx
import { Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';

export function CompareScenariosButton() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);
  const setOpen = useUiStore((s) => s.setScenarioComparisonOpen);

  return (
    <Button
      size="sm"
      onClick={() => {
        if (!currentProjectId) return showToast('Please select a project first.');
        setOpen(true);
      }}
    >
      Compare Scenarios
    </Button>
  );
}
```

- [ ] **Step 4: `ScenarioComparisonModal.tsx`**

```tsx
import { Dialog, Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useScenarioComparison } from '../../lib/query';

const BADGE_COLORS: Record<string, string> = {
  'Minimum Cost': '#34D399',
  'Minimum Land Impact': '#8B5CF6',
  'Minimum Environmental Impact': '#06B6D4',
  Balanced: '#F5A524'
};

export function ScenarioComparisonModal() {
  const open = useUiStore((s) => s.scenarioComparisonOpen);
  const setOpen = useUiStore((s) => s.setScenarioComparisonOpen);
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setRouteColorOverride = useUiStore((s) => s.setRouteColorOverride);
  const { data, isLoading, isError } = useScenarioComparison(currentProjectId, open);

  const scenarios = data?.scenarios ?? [];

  return (
    <Dialog open={open} onOpenChange={setOpen} title="Scenario Comparison" widthClassName="w-[760px]">
      {isLoading && <div className="text-[11px] text-textFaint">Loading scenario analytics…</div>}
      {isError && <div className="text-[11px] text-danger">Failed to load scenario comparison.</div>}
      {!isLoading && !isError && scenarios.length === 0 && (
        <div className="text-[11px] text-textFaint">No scenario comparison data available.</div>
      )}
      <div className="grid grid-cols-2 gap-3">
        {scenarios.map((sc) => {
          const color = BADGE_COLORS[sc.scenarioName] || '#4E8CFF';
          return (
            <div key={sc.scenarioName} className="border border-border rounded-md bg-surface2 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-text">{sc.scenarioName}</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: color, color: '#fff' }}>
                  {sc.scenarioName.split(' ')[0]}
                </span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5">
                <span>CAPEX</span>
                <span className="font-mono text-text tabular">${(sc.totalEstimatedCost || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5">
                <span>Losses</span>
                <span className="font-mono text-text tabular">{(sc.totalElectricalLossesKw || 0).toFixed(1)} kW</span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5">
                <span>ROW cost</span>
                <span className="font-mono text-text tabular">${(sc.landRowCompensationCost || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5 mb-2">
                <span>Length / Poles</span>
                <span className="font-mono text-text tabular">
                  {((sc.totalNetworkLengthMeters || 0) / 1000).toFixed(2)} km / {sc.totalPoles || 0}
                </span>
              </div>
              <Button
                size="sm"
                className="w-full justify-center"
                onClick={() => {
                  setRouteColorOverride(color);
                  setOpen(false);
                }}
              >
                Overlay Map Route
              </Button>
            </div>
          );
        })}
      </div>
    </Dialog>
  );
}
```

- [ ] **Step 5: Wire into `MapAreaContent.tsx` and `App.tsx`**

In `MapAreaContent.tsx`, read `const routeColorOverride = useUiStore((s) => s.routeColorOverride);` and pass `routeColorOverride={routeColorOverride}` to `<MapCanvas />`.

In `App.tsx`, add `<CompareScenariosButton />` to the `actionsSlot` (before `<ExportPdfButton />`) and render `<ScenarioComparisonModal />` as a sibling of `<Toast />`:
```tsx
<TopBar
  projectSlot={<ProjectSelector />}
  actionsSlot={<><CompareScenariosButton /><ExportPdfButton /><AuthTopBarActions /></>}
/>
```

- [ ] **Step 6: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, run an optimization job, then click "Compare Scenarios." Confirm the modal shows a card per scenario with CAPEX/losses/ROW/length-poles figures, and clicking "Overlay Map Route" on a card closes the modal and recolors the currently rendered feeder route to that scenario's badge color.

```bash
git add web-map-next/src/lib/store/uiStore.ts web-map-next/src/features/scenarios web-map-next/src/features/map/MapCanvas.tsx web-map-next/src/features/map/MapAreaContent.tsx web-map-next/src/App.tsx
git commit -m "feat(web-map-next): add scenario comparison modal and route color overlay"
```

---

### Task 20: Elevation profile drawer

**Files:**
- Create: `web-map-next/src/features/map/ElevationDrawer.tsx`
- Modify: `web-map-next/src/features/map/MapAreaContent.tsx` — render `<ElevationDrawer routes={data.routes} />`

Ports the elevation drawer's open/close behavior (`web-map/src/app.js` lines 305–308, 413–415) using the standalone `renderElevationProfile(svg, routeGeoJson)` extracted in Task 8.

**Interfaces:**
- Consumes: `renderElevationProfile` (Task 8), `useUiStore` (`elevationDrawerOpen`/`setElevationDrawerOpen`, Task 3).
- Produces: `<ElevationDrawer routes={FeatureCollection} />`.

- [ ] **Step 1: `ElevationDrawer.tsx`**

```tsx
import { useEffect, useRef } from 'react';
import type { FeatureCollection } from 'geojson';
import { renderElevationProfile } from '../../lib/map/elevationProfile';
import { useUiStore } from '../../lib/store';

interface ElevationDrawerProps {
  routes: FeatureCollection;
}

export function ElevationDrawer({ routes }: ElevationDrawerProps) {
  const open = useUiStore((s) => s.elevationDrawerOpen);
  const setOpen = useUiStore((s) => s.setElevationDrawerOpen);
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (routes.features.length > 0) setOpen(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routes]);

  useEffect(() => {
    if (open && svgRef.current) renderElevationProfile(svgRef.current, routes);
  }, [open, routes]);

  if (!open) return null;

  return (
    <div className="absolute left-3.5 right-3.5 bottom-3.5 h-[190px] bg-panel border border-borderStrong rounded-lg p-2.5 font-ui">
      <div className="flex items-center justify-between mb-1">
        <h4 className="m-0 text-[10.5px] uppercase tracking-wide text-textFaint font-bold">Elevation Profile</h4>
        <button onClick={() => setOpen(false)} className="text-textFaint hover:text-text text-xs leading-none">✕</button>
      </div>
      <svg ref={svgRef} viewBox="0 0 800 160" className="w-full h-[160px]" />
    </div>
  );
}
```

- [ ] **Step 2: Wire into `MapAreaContent.tsx`**

Add `import { ElevationDrawer } from './ElevationDrawer';` and render `<ElevationDrawer routes={data.routes} />` as a sibling of `<BomStrip />`. Note the `BomStrip` and `ElevationDrawer` overlays both anchor to `bottom-3.5` — since `BomStrip` is `left-3.5` (auto width) and `ElevationDrawer` spans `left-3.5 right-3.5`, the drawer renders behind/below the BOM strip in stacking order; this is acceptable for now and revisited in Task 21's parity pass (the original app placed the elevation drawer as a full-width bottom panel and the BOM values in a separate tab, not both floating over the map simultaneously — Task 21 should confirm whether the redesign's mockup intends the BOM strip to sit above the drawer, or whether the drawer should only render `bottom-3.5` when the BOM strip isn't relevant, e.g. move `BomStrip` to `bottom-[210px]` when the drawer is open).

- [ ] **Step 3: Verify and commit**

Run: `cd web-map-next && npm run typecheck`
Expected: no errors.

Run: `npm run dev`, run an optimization job so a route exists, and confirm the elevation drawer opens automatically along the bottom of the map with a filled area chart, pole markers, and a working close button.

```bash
git add web-map-next/src/features/map/ElevationDrawer.tsx web-map-next/src/features/map/MapAreaContent.tsx
git commit -m "feat(web-map-next): add elevation profile drawer"
```

---

### Task 21: Final integration and parity pass

**Files:**
- Modify: `web-map-next/src/features/bom/BomStrip.tsx` — shift up when the elevation drawer is open, fixing the overlap flagged in Task 20

**Interfaces:**
- Consumes: everything built in Tasks 1–20.
- Produces: no new interfaces — this task only fixes the one known layout defect and performs manual QA per the spec's "no automated test suite, manual QA only" testing section.

- [ ] **Step 1: Fix the `BomStrip` / `ElevationDrawer` overlap**

Modify `web-map-next/src/features/bom/BomStrip.tsx`: add `const elevationDrawerOpen = useUiStore((s) => s.elevationDrawerOpen);` and change the returned wrapper's className from a fixed `bottom-3.5` to:
```tsx
<div
  className={`absolute left-3.5 flex rounded-lg overflow-hidden font-ui transition-all ${
    elevationDrawerOpen ? 'bottom-[220px]' : 'bottom-3.5'
  }`}
>
```

- [ ] **Step 2: Full production build check**

Run: `cd web-map-next && npm run build`
Expected: builds cleanly with no TypeScript or bundler errors, producing `web-map-next/dist/`.

- [ ] **Step 3: Manual parity checklist against `web-map`**

Run both apps side by side — `web-map` via `cd web-map && npm run dev` (or the existing container) and `web-map-next` via `cd web-map-next && npm run dev` — against the same backend and the same sample project data, and confirm each item matches in *behavior* (visual styling is expected to differ per the approved redesign):

- [ ] Logging in with valid/invalid credentials behaves the same; logout returns to the sign-in gate.
- [ ] Project dropdown lists the same projects; "+ New" creates a project and switches to it the same way.
- [ ] Dropping a `.geojson` file with points/lines/polygons classifies and renders the same as the old app (auto-detect picks the same asset types via the shared `classify.ts` rules).
- [ ] Dropping a `.kmz`/`.kml` file opens the same import preview information (counts, notes, per-row rule/evidence), and committing produces the same import result toast.
- [ ] Running an optimization with the same scenario/sliders produces the same job, the same SSE progress messages, and the same final map/BOM state.
- [ ] Every layer toggle, opacity slider, and route-edit toggle produces the same map effect.
- [ ] BOM totals (length/poles/cost/losses) match between the strip, the BOM pane, and the old app for the same job.
- [ ] CSV and PDF export buttons (header and BOM pane) download the same files.
- [ ] Audit log entries match.
- [ ] Scenario comparison shows the same scenarios/figures; confirm with the user whether "Overlay Map Route" recoloring the current route (this port's behavior, see Task 19) is acceptable versus the original's no-op fetch, or whether the backend route-fetch-without-a-job-id behavior should be fixed instead.
- [ ] Optimization slider min/max ranges (Task 15) match the values in `web-map/index.html`'s `<input type="range">` elements — adjust `OptimizationPane.tsx` if they don't.

Fix any discrepancy found by editing the relevant file from Tasks 1–20 directly; there is no separate "fix" task — this checklist is the acceptance gate for the whole migration.

- [ ] **Step 4: Commit**

```bash
git add web-map-next/src/features/bom/BomStrip.tsx
git commit -m "fix(web-map-next): resolve BOM strip / elevation drawer overlap, complete parity pass"
```

---

### Task 22: Cutover — Docker, CI, and README

**Files:**
- Create: `web-map-next/Dockerfile`
- Create: `web-map-next/nginx.conf`
- Create: `web-map-next/.dockerignore`
- Modify: `docker-compose.yml` — build `web-map-next` instead of `web-map`
- Modify: `.github/workflows/ci.yml` — point the frontend CI job at `web-map-next` and drop the `npm test` step (no automated test suite per the spec)
- Modify: `README.md` — describe `web-map-next` as the frontend, update the Quick Start commands

This task repoints production and CI at the new app. **`web-map/` is not deleted** — per the "prefer reversible actions" guidance, it's left in the repo, unreferenced by the build, so the team can delete it explicitly once they're confident in the cutover; this task only stops building/deploying it.

**Interfaces:**
- Consumes: `web-map-next/package.json`'s `build` script (Task 1).
- Produces: nothing consumed by later tasks — this is the last task in the plan.

- [ ] **Step 1: `web-map-next/Dockerfile`**

```dockerfile
# Build stage for Vite Web GIS Frontend
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY tsconfig*.json vite.config.ts tailwind.config.js postcss.config.js index.html ./
COPY src ./src
RUN npm run build

# Nginx production web server
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: `web-map-next/nginx.conf`** (identical to `web-map/nginx.conf`)

```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

`web-map-next/.dockerignore`:
```
node_modules
dist
.git
```

- [ ] **Step 3: Repoint `docker-compose.yml`**

Modify the `web-map` service's `build.context` (currently `./web-map`, docker-compose.yml lines 65–66) to `./web-map-next`:
```yaml
    build:
      context: ./web-map-next
      dockerfile: Dockerfile
```
Leave `container_name: surge-web-map`, `ports: ["3000:80"]`, and the healthcheck unchanged — only the build source moves.

- [ ] **Step 4: Repoint the frontend CI job**

Modify `.github/workflows/ci.yml`'s frontend job (currently lines 48–61):
```yaml
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web-map-next
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: npm
          cache-dependency-path: web-map-next/package-lock.json
      - run: npm ci
      - run: npm run build
```
(the `npm test` step is removed — this migration ships with manual QA only, per the spec).

- [ ] **Step 5: Update `README.md`**

Replace item 3 under "Core Components" (currently lines 19–22):
```markdown
3. **Web GIS Map Frontend (`/web-map-next`)**
   - An interactive map interface built with React, TypeScript, Vite, Tailwind CSS, and Leaflet.
   - Allows users to drag-and-drop GeoJSON features, configure optimization scenarios, visualize routes, and download Bill of Materials (BOM) CSV reports.
   - Uses a "technical dashboard" design system — near-black surfaces, hairline borders, a single accent color, and monospace numerals for engineering readouts. `web-map/` (the previous vanilla-JS implementation) is retained for reference but no longer built or deployed.
```

Replace the "Web Map Frontend" Quick Start block (currently lines 52–59):
```markdown
### Web Map Frontend
```powershell
cd web-map-next
npm ci
npm run build
npm run dev
```
```

- [ ] **Step 6: Verify and commit**

Run: `docker compose build web-map`
Expected: the image builds successfully from `web-map-next/`.

Run: `docker compose up -d` (full stack, with `.env` configured per the README) and open `http://localhost:3000`.
Expected: the redesigned SURGE app loads, and every item from Task 21's parity checklist still holds through the production nginx build (not just the Vite dev server).

```bash
git add web-map-next/Dockerfile web-map-next/nginx.conf web-map-next/.dockerignore docker-compose.yml .github/workflows/ci.yml README.md
git commit -m "chore: cut over Docker, CI, and docs from web-map to web-map-next"
```

---

## Self-Review

**Spec coverage:** §2 (stack) → Tasks 1–2, 6, 8; §3 (design tokens) → Task 1; §4 (folder structure) → Tasks throughout, one `features/*` folder per task group; §5 (migration phases 1–6) → Tasks 1–2 (scaffold), 8–10 (map integration), 11–20 (feature-by-feature port), 4/6/13 (API rewrite), 21 (parity pass), 22 (cutover); §6 (data flow/error handling) → Task 6 (Query hooks own loading/error state), Task 3 (Zustand for UI-only state), Task 15 (job polling hook); §7 (manual QA only) → every task's verification step is a manual dev-server check, Task 21 is the formal checklist gate.

**Placeholder scan:** no `TBD`/`TODO` remain; every step shows complete code. The two intentionally-deferred no-ops (`onKmzPreview={() => {}}` in Task 13, `onRouteVertexMoved={() => {}}` in Task 10) are explicitly documented as temporary and are replaced by name in Tasks 14 and 17 respectively — not left dangling.

**Type consistency:** `LayerName` is defined once (Task 3, `lib/store/uiStore.ts`) and imported everywhere else (`SurgeMapEngine`, `MapCanvasProps`) rather than redefined. `FeatureCollection` comes from `@types/geojson` throughout, never redeclared. `MapCanvasHandle`/`MapCanvasProps` are defined once in Task 10 and only extended (never redefined) in Tasks 19–20. `ProjectMapData` (Task 9) is the single source for grouped GeoJSON + counts, consumed identically by `MapAreaContent`, `AssetSummary`, and `BomStrip`/`BomPane`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-12-web-map-frontend-redesign.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
