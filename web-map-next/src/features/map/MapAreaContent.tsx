import { useEffect } from 'react';
import type { RefObject } from 'react';
import { useUiStore } from '../../lib/store';
import { useProjectData } from './useProjectData';
import { MapCanvas, type MapCanvasHandle } from './MapCanvas';
import { BomStrip } from '../bom/BomStrip';
import { MapLegendToggle } from './MapLegend';
import { Tooltip } from '../../components/ui';

interface MapAreaContentProps {
  mapRef: RefObject<MapCanvasHandle>;
}

export function MapAreaContent({ mapRef }: MapAreaContentProps) {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const resultJobId = useUiStore((s) => s.resultJobId);
  const layerVisibility = useUiStore((s) => s.layerVisibility);
  const parcelOpacity = useUiStore((s) => s.parcelOpacity);
  const restrictedOpacity = useUiStore((s) => s.restrictedOpacity);
  const routeEditMode = useUiStore((s) => s.routeEditMode);
  const setLiveBomOverride = useUiStore((s) => s.setLiveBomOverride);
  const routeColorOverride = useUiStore((s) => s.routeColorOverride);

  const data = useProjectData(currentProjectId, resultJobId);

  useEffect(() => {
    if (!data.isLoading) mapRef.current?.fitAllBounds();
  }, [currentProjectId, resultJobId, data.isLoading]);

  useEffect(() => {
    setLiveBomOverride(null);
  }, [currentProjectId, resultJobId, setLiveBomOverride]);

  return (
    <>
      <MapCanvas
        ref={mapRef}
        wtgs={data.wtgs}
        substations={data.substations}
        towers={data.towers}
        referenceLines={data.referenceLines}
        routes={data.routes}
        poles={data.poles}
        parcels={data.parcels}
        restrictedAreas={data.restrictedAreas}
        layerVisibility={layerVisibility}
        parcelOpacity={parcelOpacity}
        restrictedOpacity={restrictedOpacity}
        routeEditMode={routeEditMode}
        onRouteVertexMoved={(lengthMeters, poles, cost) =>
          setLiveBomOverride({ lengthKm: (lengthMeters / 1000).toFixed(2), poles, cost })
        }
        routeColorOverride={routeColorOverride}
      />
      {data.loadError && (
        // Deliberately loud and not dismissible. A blank map looks identical to a network with no
        // routes, so an operator has no way to tell that they are looking at incomplete data.
        <div
          role="alert"
          className="absolute left-1/2 top-3.5 z-[1020] -translate-x-1/2 rounded-lg border border-danger bg-panel px-4 py-2.5 font-ui text-[12.5px] text-danger shadow-lg"
        >
          {data.loadError}
        </div>
      )}
      {/* Sits above the BOM strip and clear of Leaflet's own controls on the right. */}
      <div className="absolute bottom-[86px] left-3.5 z-[1010] flex flex-col items-start gap-2">
        <MapLegendToggle />
        <Tooltip label="Zoom to fit all assets" side="top">
          <button
            onClick={() => mapRef.current?.fitAllBounds()}
            aria-label="Zoom to fit all assets"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-borderStrong bg-panel/95
                       text-textMuted shadow-2 backdrop-blur-sm transition-colors duration-fast ease-out
                       hover:text-text hover:border-textFaint"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
            </svg>
          </button>
        </Tooltip>
      </div>
      <BomStrip />
    </>
  );
}
