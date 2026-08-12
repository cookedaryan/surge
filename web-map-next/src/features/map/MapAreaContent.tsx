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
