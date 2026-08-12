import { useState } from 'react';
import type { RefObject } from 'react';
import type { MapCanvasHandle } from '../map/MapCanvas';
import type { ImportPreview } from '../../lib/api';
import { AssetDropzone } from './AssetDropzone';
import { AssetSummary } from './AssetSummary';
import { ImportPreviewModal } from './ImportPreviewModal';

interface AssetsPaneProps {
  mapRef: RefObject<MapCanvasHandle>;
}

export function AssetsPane({ mapRef }: AssetsPaneProps) {
  const [preview, setPreview] = useState<ImportPreview | null>(null);

  return (
    <>
      <AssetDropzone mapRef={mapRef} onKmzPreview={setPreview} />
      <AssetSummary />
      <ImportPreviewModal preview={preview} onClose={() => setPreview(null)} />
    </>
  );
}
