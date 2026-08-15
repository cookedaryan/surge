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
import { OptimizationPane } from './features/optimization/OptimizationPane';
import { LayersPane } from './features/layers/LayersPane';
import { BomPane } from './features/bom/BomPane';
import { ExportPdfButton } from './features/bom/ExportPdfButton';
import { AuditPane } from './features/audit/AuditPane';
import { AdminPane } from './features/admin/AdminPane';
import { CompareScenariosButton } from './features/scenarios/CompareScenariosButton';
import { ScenarioComparisonModal } from './features/scenarios/ScenarioComparisonModal';

export default function App() {
  const mapRef = useRef<MapCanvasHandle>(null);
  useSessionRestore();

  return (
    <div className="h-full flex flex-col font-ui text-text">
      <AuthGateway />
      <Toast />
      <ScenarioComparisonModal />
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
  );
}
