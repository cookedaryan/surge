import { ChangeEvent, DragEvent, RefObject, useRef, useState } from 'react';
import { useUiStore } from '../../lib/store';
import { Card, CardTitle, CardDescription } from '../../components/ui';
import type { ImportPreview } from '../../lib/api';
import type { MapCanvasHandle } from '../map/MapCanvas';
import { useAssetImport, type AssetImportType } from './useAssetImport';

const TYPE_OPTIONS: { value: AssetImportType; label: string }[] = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'wtg', label: 'WTGs' },
  { value: 'substation', label: 'Substation' },
  { value: 'parcel', label: 'Parcels' },
  { value: 'restricted', label: 'Restricted' }
];

interface AssetDropzoneProps {
  mapRef: RefObject<MapCanvasHandle>;
  onKmzPreview: (preview: ImportPreview) => void;
}

export function AssetDropzone({ mapRef, onKmzPreview }: AssetDropzoneProps) {
  const showToast = useUiStore((s) => s.showToast);
  const [selectedType, setSelectedType] = useState<AssetImportType>('auto');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { handleFiles, isProcessing } = useAssetImport({ mapRef, onKmzPreview, onToast: showToast });

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files, selectedType);
  }

  function onFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) handleFiles(e.target.files, selectedType);
    e.target.value = '';
  }

  return (
    <Card>
      <CardTitle>GeoJSON Ingestion</CardTitle>
      <CardDescription>Drag &amp; drop feature collections for WTGs, substations, restricted areas, or parcels.</CardDescription>
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border border-dashed rounded-md px-2.5 py-4 text-center cursor-pointer ${
          dragOver ? 'border-accent bg-accentSoft' : 'border-borderStrong bg-surface2'
        }`}
      >
        <p className="m-0 text-[11.5px] font-semibold text-text">{isProcessing ? 'Processing…' : 'Drop .geojson / .kmz / .kml'}</p>
        <span className="text-[11.5px] text-textFaint">or click to browse</span>
        <input ref={fileInputRef} type="file" multiple accept=".geojson,.json,.kmz,.kml" className="hidden" onChange={onFileInputChange} />
      </div>
      <div className="flex flex-wrap gap-1.5 mt-2.5 items-center justify-between">
        <div className="flex flex-wrap gap-1.5">
          {TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSelectedType(opt.value)}
              className={`text-[11.5px] font-semibold px-2.5 py-1 rounded-full border ${
                selectedType === opt.value ? 'bg-accent border-accent text-accentInk' : 'bg-surface2 border-borderStrong text-textMuted'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <a
          href="/sample_wind_farm.kmz"
          download="sample_wind_farm.kmz"
          className="text-[11.5px] font-medium text-accent hover:underline inline-flex items-center gap-1 mt-1 min-h-6 py-1"
        >
          ⬇️ Download Sample .KMZ
        </a>
      </div>
    </Card>
  );
}
