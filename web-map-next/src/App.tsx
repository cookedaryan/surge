import { useRef } from 'react';
import { TopBar } from './app/TopBar';
import { RailNav } from './app/RailNav';
import { SidePanel, Pane } from './app/SidePanel';
import { MapArea } from './app/MapArea';
import { AuthGateway } from './features/auth/AuthGateway';
import { useSessionRestore } from './features/auth/useSessionRestore';
import { AuthTopBarActions } from './features/auth/AuthTopBarActions';
import { ProjectSelector } from './features/projects/ProjectSelector';
import { AssetsPane } from './features/assets/AssetsPane';
import { MapAreaContent } from './features/map/MapAreaContent';
import type { MapCanvasHandle } from './features/map/MapCanvas';
import { Toast } from './components/Toast';
import { TooltipProvider } from './components/ui';
import { OptimizationPane } from './features/optimization/OptimizationPane';
import { LayersPane } from './features/layers/LayersPane';
import { BomPane } from './features/bom/BomPane';
import { ExportPdfButton } from './features/bom/ExportPdfButton';
import { AuditPane } from './features/audit/AuditPane';
import { AdminPane } from './features/admin/AdminPane';
import { CompareScenariosButton } from './features/scenarios/CompareScenariosButton';
import { ScenarioComparisonModal } from './features/scenarios/ScenarioComparisonModal';
import { ResultsSheet } from './features/optimization/ResultsSheet';
import { useAuthStore } from './lib/store';

export default function App() {
  const mapRef = useRef<MapCanvasHandle>(null);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  useSessionRestore();

  // The workstation is not rendered behind the sign-in screen. It used to be, which meant the
  // whole app — nav, panel, map — stayed in the tab order underneath the overlay, so a keyboard
  // user could tab straight past sign-in into controls they were not authenticated for. It also
  // fired every project query on load only to have them rejected and cached as failures.
  //
  // Gating on isAuthenticated is safe to do synchronously: the store derives it from the stored
  // token during creation, so there is no restoring phase to flash through.
  if (!isAuthenticated) {
    return (
      <>
        <AuthGateway />
        <Toast />
      </>
    );
  }

  return (
    <TooltipProvider>
      <div className="h-full flex flex-col font-ui text-text">
        <Toast />
        <ScenarioComparisonModal />
        <ResultsSheet />
        <TopBar
          projectSlot={<ProjectSelector />}
          actionsSlot={<><CompareScenariosButton /><ExportPdfButton /><AuthTopBarActions /></>}
        />
        <div className="flex-1 flex min-h-0">
          <RailNav />
          <SidePanel>
            <Pane tab="assets"><AssetsPane mapRef={mapRef} /></Pane>
            <Pane tab="optimize"><OptimizationPane /></Pane>
            <Pane tab="layers"><LayersPane /></Pane>
            <Pane tab="bom"><BomPane /></Pane>
            <Pane tab="audit"><AuditPane /></Pane>
            <Pane tab="admin"><AdminPane /></Pane>
          </SidePanel>
          <MapArea>
            <MapAreaContent mapRef={mapRef} />
          </MapArea>
        </div>
      </div>
    </TooltipProvider>
  );
}
