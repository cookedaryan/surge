import { useEffect } from 'react';
import type { RefObject } from 'react';
import { useUiStore } from '../../lib/store';
import { useProjectData } from './useProjectData';
import { MapCanvas, type MapCanvasHandle } from './MapCanvas';
import { BomStrip } from '../bom/BomStrip';

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
      <BomStrip />
    </>
  );
}
