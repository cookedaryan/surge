import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import type { FeatureCollection } from 'geojson';
import { SurgeMapEngine } from '../../lib/map/SurgeMapEngine';
import type { LayerName } from '../../lib/store';

export interface MapCanvasProps {
  wtgs: FeatureCollection;
  substations: FeatureCollection;
  towers: FeatureCollection;
  referenceLines: FeatureCollection;
  routes: FeatureCollection;
  parcels: FeatureCollection;
  restrictedAreas: FeatureCollection;
  layerVisibility: Record<LayerName, boolean>;
  parcelOpacity: number;
  restrictedOpacity: number;
  routeEditMode: boolean;
  onRouteVertexMoved: (lengthMeters: number, poles: number, cost: number) => void;
  routeColorOverride: string | null;
}

export interface MapCanvasHandle {
  renderImportedGeoJson: (geoJson: FeatureCollection) => void;
  clearImported: () => void;
  invalidateSize: () => void;
  fitAllBounds: () => void;
}

const MAP_CONTAINER_ID = 'surge-leaflet-container';

export const MapCanvas = forwardRef<MapCanvasHandle, MapCanvasProps>(function MapCanvas(props, ref) {
  const engineRef = useRef<SurgeMapEngine | null>(null);

  useEffect(() => {
    engineRef.current = new SurgeMapEngine(MAP_CONTAINER_ID);
    return () => {
      engineRef.current?.map.remove();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => { engineRef.current?.renderWtgs(props.wtgs); }, [props.wtgs]);
  useEffect(() => { engineRef.current?.renderSubstations(props.substations); }, [props.substations]);
  useEffect(() => { engineRef.current?.renderTowers(props.towers); }, [props.towers]);
  useEffect(() => { engineRef.current?.renderReferenceLines(props.referenceLines); }, [props.referenceLines]);
  useEffect(() => {
    engineRef.current?.renderRoutes(props.routes, props.routeColorOverride);
  }, [props.routes, props.routeColorOverride]);
  useEffect(() => {
    engineRef.current?.renderParcels(props.parcels, props.parcelOpacity);
  }, [props.parcels, props.parcelOpacity]);
  useEffect(() => {
    engineRef.current?.renderRestrictedAreas(props.restrictedAreas, props.restrictedOpacity);
  }, [props.restrictedAreas, props.restrictedOpacity]);

  useEffect(() => {
    if (!engineRef.current) return;
    (Object.keys(props.layerVisibility) as LayerName[]).forEach((layer) => {
      engineRef.current!.setLayerVisibility(layer, props.layerVisibility[layer]);
    });
  }, [props.layerVisibility]);

  useEffect(() => {
    engineRef.current?.enableRouteEditing(props.routeEditMode, props.onRouteVertexMoved);
  }, [props.routeEditMode, props.routes]);

  useImperativeHandle(
    ref,
    () => ({
      renderImportedGeoJson: (geoJson) => engineRef.current?.renderImportedGeoJson(geoJson),
      clearImported: () => engineRef.current?.clearImported(),
      invalidateSize: () => engineRef.current?.invalidateSize(),
      fitAllBounds: () => engineRef.current?.fitAllBounds()
    }),
    []
  );

  return <div id={MAP_CONTAINER_ID} className="absolute inset-0" />;
});
