import { create } from 'zustand';

export type LayerName =
  | 'wtgs' | 'substations' | 'towers' | 'referenceLines'
  | 'routes' | 'polesTerminal' | 'polesAngle' | 'polesIntermediate' | 'polesJunction'
  | 'parcels' | 'restricted' | 'imported';

export type SidebarTab = 'assets' | 'optimize' | 'layers' | 'bom' | 'audit' | 'admin';

interface UiState {
  activeSidebarTab: SidebarTab;
  setActiveSidebarTab: (tab: SidebarTab) => void;

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

  toast: { message: string; variant: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, variant?: 'success' | 'error' | 'info') => void;
  clearToast: () => void;

  liveBomOverride: { lengthKm: string; poles: number; cost: number } | null;
  setLiveBomOverride: (v: { lengthKm: string; poles: number; cost: number } | null) => void;

  routeColorOverride: string | null;
  setRouteColorOverride: (v: string | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeSidebarTab: 'assets',
  setActiveSidebarTab: (tab) => set({ activeSidebarTab: tab }),

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

  toast: null,
  showToast: (message, variant = 'info') => set({ toast: { message, variant } }),
  clearToast: () => set({ toast: null }),

  liveBomOverride: null,
  setLiveBomOverride: (v) => set({ liveBomOverride: v }),

  routeColorOverride: null,
  setRouteColorOverride: (v) => set({ routeColorOverride: v })
}));
