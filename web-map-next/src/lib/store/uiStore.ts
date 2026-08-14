import { create } from 'zustand';

export type LayerName =
  | 'wtgs' | 'substations' | 'towers' | 'referenceLines'
  | 'routes' | 'poles' | 'parcels' | 'restricted' | 'imported';

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
  setCurrentProjectId: (id) => set({ currentProjectId: id }),

  currentJobId: null,
  setCurrentJobId: (id) => set({ currentJobId: id }),

  layerVisibility: {
    wtgs: true, substations: true, towers: true, referenceLines: true,
    routes: true, poles: true, parcels: true, restricted: false, imported: true
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
  setImportPreviewOpen: (v) => set({ importPreviewOpen: v }),

  toast: null,
  showToast: (message, variant = 'info') => set({ toast: { message, variant } }),
  clearToast: () => set({ toast: null }),

  liveBomOverride: null,
  setLiveBomOverride: (v) => set({ liveBomOverride: v }),

  routeColorOverride: null,
  setRouteColorOverride: (v) => set({ routeColorOverride: v })
}));
