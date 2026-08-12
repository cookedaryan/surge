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
