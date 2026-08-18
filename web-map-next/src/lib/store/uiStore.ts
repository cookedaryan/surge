import { create } from 'zustand';

export type LayerName =
  | 'wtgs' | 'substations' | 'towers' | 'referenceLines'
  | 'routes' | 'polesTerminal' | 'polesAngle' | 'polesIntermediate' | 'polesJunction'
  | 'parcels' | 'restricted' | 'imported';

export type SidebarTab = 'assets' | 'optimize' | 'layers' | 'bom' | 'audit' | 'admin';

export type ToastVariant = 'success' | 'error' | 'info';
export interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

/** Enough to see a burst without the stack covering the map it is reporting on. */
const MAX_TOASTS = 3;
let nextToastId = 1;

const SIDEBAR_WIDTH_KEY = 'surge.sidebarWidth';
const SIDEBAR_COLLAPSED_KEY = 'surge.sidebarCollapsed';

export const SIDEBAR_MIN_WIDTH = 260;
export const SIDEBAR_MAX_WIDTH = 520;

/**
 * Panel geometry is read back from localStorage, which is user-writable and survives deploys that
 * change these bounds. A stored width is therefore treated as a suggestion and clamped, not
 * trusted — a stale or hand-edited value must not be able to render the panel unusable.
 */
function readStoredWidth(): number {
  if (typeof localStorage === 'undefined') return 300;
  const raw = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY));
  if (!Number.isFinite(raw) || raw <= 0) return 300;
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, raw));
}

function readStoredCollapsed(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
}

interface UiState {
  activeSidebarTab: SidebarTab;
  setActiveSidebarTab: (tab: SidebarTab) => void;

  sidebarWidth: number;
  setSidebarWidth: (w: number) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  /** The expanded run breakdown, shown over the map rather than in the panel. */
  resultsSheetOpen: boolean;
  setResultsSheetOpen: (v: boolean) => void;

  currentProjectId: string | null;
  setCurrentProjectId: (id: string | null) => void;

  /** The job being followed — set as soon as a run is queued, while it is still producing nothing. */
  currentJobId: string | null;
  setCurrentJobId: (id: string | null) => void;

  /**
   * The job whose results are on screen. Only advances once a run finishes.
   *
   * Kept separate from {@link currentJobId} because the map is keyed on it: pointing the map at a
   * job the moment it is queued makes it fetch results that do not exist yet, blanking the display
   * for the entire run. Holding the previous result until the new one is ready means the operator
   * keeps something to look at.
   */
  resultJobId: string | null;
  setResultJobId: (id: string | null) => void;

  layerVisibility: Record<LayerName, boolean>;
  toggleLayer: (layer: LayerName) => void;

  parcelOpacity: number;
  setParcelOpacity: (v: number) => void;

  restrictedOpacity: number;
  setRestrictedOpacity: (v: number) => void;

  routeEditMode: boolean;
  setRouteEditMode: (v: boolean) => void;

  scenarioComparisonOpen: boolean;
  setScenarioComparisonOpen: (v: boolean) => void;

  newProjectModalOpen: boolean;
  setNewProjectModalOpen: (v: boolean) => void;

  importPreviewOpen: boolean;
  setImportPreviewOpen: (v: boolean) => void;

  toasts: ToastItem[];
  showToast: (message: string, variant?: ToastVariant) => void;
  dismissToast: (id: number) => void;

  liveBomOverride: { lengthKm: string; poles: number; cost: number } | null;
  setLiveBomOverride: (v: { lengthKm: string; poles: number; cost: number } | null) => void;

  routeColorOverride: string | null;
  setRouteColorOverride: (v: string | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeSidebarTab: 'assets',
  setActiveSidebarTab: (tab) => set({ activeSidebarTab: tab }),

  sidebarWidth: readStoredWidth(),
  setSidebarWidth: (w) => {
    const clamped = Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, w));
    try {
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(clamped));
    } catch {
      // Private-browsing or a full quota. The panel still resizes for this session; only the
      // memory of it is lost, which is not worth failing the drag over.
    }
    set({ sidebarWidth: clamped });
  },
  sidebarCollapsed: readStoredCollapsed(),
  toggleSidebar: () =>
    set((s) => {
      const next = !s.sidebarCollapsed;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      } catch {
        // As above — a preference that cannot be stored is not a failure worth surfacing.
      }
      return { sidebarCollapsed: next };
    }),

  resultsSheetOpen: false,
  setResultsSheetOpen: (v) => set({ resultsSheetOpen: v }),

  currentProjectId: null,
  // Job ids belong to a project. Carrying them across a switch would poll and render another
  // project's run against the newly selected one, which the API answers with 400s.
  setCurrentProjectId: (id) =>
    set((state) =>
      state.currentProjectId === id
        ? { currentProjectId: id }
        : { currentProjectId: id, currentJobId: null, resultJobId: null }
    ),

  currentJobId: null,
  setCurrentJobId: (id) => set({ currentJobId: id }),

  resultJobId: null,
  setResultJobId: (id) => set({ resultJobId: id }),

  layerVisibility: {
    wtgs: true, substations: true, towers: true, referenceLines: true,
    routes: true,
    polesTerminal: true, polesAngle: true, polesIntermediate: true, polesJunction: true,
    parcels: true, restricted: false, imported: true
  },
  toggleLayer: (layer) =>
    set((s) => ({ layerVisibility: { ...s.layerVisibility, [layer]: !s.layerVisibility[layer] } })),

  parcelOpacity: 0.25,
  setParcelOpacity: (v) => set({ parcelOpacity: v }),

  restrictedOpacity: 0.35,
  setRestrictedOpacity: (v) => set({ restrictedOpacity: v }),

  routeEditMode: false,
  setRouteEditMode: (v) => set({ routeEditMode: v }),

  scenarioComparisonOpen: false,
  setScenarioComparisonOpen: (v) => set({ scenarioComparisonOpen: v }),

  newProjectModalOpen: false,
  setNewProjectModalOpen: (v) => set({ newProjectModalOpen: v }),

  importPreviewOpen: false,
  setImportPreviewOpen: (v) => set({ importPreviewOpen: v }),

  toasts: [],
  // A single-slot toast meant a run that failed and then a second action that succeeded left only
  // the success on screen — the report's C-11. Messages now queue instead of overwriting, with the
  // oldest dropped past MAX_TOASTS so a burst cannot bury the map.
  showToast: (message, variant = 'info') =>
    set((s) => ({ toasts: [...s.toasts, { id: nextToastId++, message, variant }].slice(-MAX_TOASTS) })),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  liveBomOverride: null,
  setLiveBomOverride: (v) => set({ liveBomOverride: v }),

  routeColorOverride: null,
  setRouteColorOverride: (v) => set({ routeColorOverride: v })
}));
