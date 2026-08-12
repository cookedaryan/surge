import type { RefObject } from 'react';
import type { MapCanvasHandle } from '../map/MapCanvas';
import { AssetDropzone } from './AssetDropzone';
import { AssetSummary } from './AssetSummary';

interface AssetsPaneProps {
  mapRef: RefObject<MapCanvasHandle>;
}

export function AssetsPane({ mapRef }: AssetsPaneProps) {
  return (
    <>
      <AssetDropzone mapRef={mapRef} onKmzPreview={() => {}} />
      <AssetSummary />
    </>
  );
}
