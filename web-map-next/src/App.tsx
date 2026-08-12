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
import { OptimizationPane } from './features/optimization/OptimizationPane';

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
          <Pane tab="optimize"><OptimizationPane /></Pane>
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
