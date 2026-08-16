import { useState } from 'react';
import type { RefObject } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Feature } from 'geojson';
import { api } from '../../lib/api';
import type { ImportPreview } from '../../lib/api';
import { ASSET_TYPES, classifyGeoJsonFeature } from '../../lib/classify';
import { useUiStore } from '../../lib/store';
import type { MapCanvasHandle } from '../map/MapCanvas';

export type AssetImportType = 'auto' | 'wtg' | 'substation' | 'parcel' | 'restricted';

interface UseAssetImportOptions {
  mapRef: RefObject<MapCanvasHandle>;
  onKmzPreview: (preview: ImportPreview) => void;
  onToast: (message: string) => void;
}

function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target!.result as string);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

export function useAssetImport({ mapRef, onKmzPreview, onToast }: UseAssetImportOptions) {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const queryClient = useQueryClient();
  const [isProcessing, setIsProcessing] = useState(false);

  async function handleFiles(files: FileList | File[], selectedType: AssetImportType) {
    const fileList = Array.from(files);
    if (fileList.length === 0) return;

    // Refuse rather than invent a project. This used to fall back to a made-up 'proj-default' id
    // and then skip persistence for exactly that id, so an import drew on the map, looked like it
    // had worked, and was gone on the next refresh with nothing said.
    if (!currentProjectId) {
      onToast('Select or create a project before importing — imported assets are saved to a project.');
      return;
    }
    const projectId = currentProjectId;

    const kmzFiles = fileList.filter((f) => /\.(kmz|kml)$/i.test(f.name));
    const geoJsonFiles = fileList.filter((f) => !/\.(kmz|kml)$/i.test(f.name));

    const failedToSave: string[] = [];
    const failedToParse: string[] = [];

    setIsProcessing(true);
    try {
      for (const file of kmzFiles) {
        try {
          const preview = await api.previewKmzAssets(projectId, file);
          onKmzPreview(preview);
        } catch (err) {
          onToast(`Import error: ${(err as Error).message || err}`);
        }
      }

      if (geoJsonFiles.length === 0) return;

      mapRef.current?.clearImported();
      const unclassified: Feature[] = [];
      let totalFeatures = 0;

      for (const file of geoJsonFiles) {
        try {
          const text = await readFileText(file);
          const geoJson = JSON.parse(text);
          const features: Feature[] = geoJson.features || (geoJson.type === 'Feature' ? [geoJson] : []);
          totalFeatures += features.length;

          mapRef.current?.renderImportedGeoJson(geoJson);

          for (const feat of features) {
            if (!feat.properties) feat.properties = {};
            const props = feat.properties as Record<string, any>;

            if (selectedType === 'wtg') props.assetType = 'WTG';
            else if (selectedType === 'substation') props.assetType = 'SUBSTATION';
            else if (selectedType === 'parcel') props.assetType = 'PARCEL';
            else if (selectedType === 'restricted') props.assetType = 'RESTRICTED';

            const geomType = feat.geometry?.type || '';
            if (geomType === 'Point' || geomType === 'MultiPoint') {
              if (selectedType === 'auto') {
                const detected = classifyGeoJsonFeature(feat).assetType;
                props.assetType = detected;
                if (detected === ASSET_TYPES.UNKNOWN) unclassified.push(feat);
              }
            } else if (geomType !== 'LineString' && geomType !== 'MultiLineString' && geomType !== 'Polygon' && geomType !== 'MultiPolygon') {
              unclassified.push(feat);
            }
          }

          const payload = JSON.stringify(geoJson);
          const isParcel =
            selectedType === 'parcel' ||
            (selectedType === 'auto' &&
              features.some((f) => f.geometry?.type?.includes('Polygon') && !(f.properties as any)?.restrictionType));
          const isRestrictedPayload =
            selectedType === 'restricted' ||
            (selectedType === 'auto' &&
              features.some((f) => f.geometry?.type?.includes('Polygon') && (f.properties as any)?.restrictionType));

          // Awaited, and failures are reported. These were fire-and-forget with a console.warn,
          // so a rejected save left the features drawn on the map as though they had been stored —
          // the operator only found out when they reloaded and the work was gone.
          try {
            if (isParcel) {
              await api.importParcelsGeoJson(projectId, payload);
            } else if (isRestrictedPayload) {
              await api.importRestrictedAreasGeoJson(projectId, payload);
            } else {
              await api.importGeoJsonAssets(projectId, payload);
            }
          } catch (err) {
            failedToSave.push(file.name);
            console.error(`Failed to save ${file.name} to the project:`, err);
          }
        } catch (err) {
          failedToParse.push(file.name);
          console.error(`Failed to parse file ${file.name}:`, err);
        }
      }

      if (unclassified.length > 0) {
        const sample = unclassified
          .slice(0, 3)
          .map((f) => (f.properties as any)?.externalId || (f.properties as any)?.name || '?')
          .join(', ');
        onToast(
          `${unclassified.length} feature(s) could not be classified (${sample}${unclassified.length > 3 ? ', …' : ''}). ` +
            `Pick an asset type above and re-import, or upload as KMZ to use the preview.`
        );
      }

      mapRef.current?.invalidateSize();
      mapRef.current?.fitAllBounds();

      // What is on the map and what is in the project are different things. Saying "loaded" when
      // the save failed is the reason this class of loss went unnoticed: the features were right
      // there on screen.
      if (failedToParse.length > 0) {
        onToast(`Could not read ${failedToParse.join(', ')} — nothing was imported from ${failedToParse.length > 1 ? 'those files' : 'that file'}.`);
      }
      if (failedToSave.length > 0) {
        onToast(
          `Drawn on the map but NOT saved to the project: ${failedToSave.join(', ')}. ` +
            `These will disappear when you reload. Check your connection and import again.`
        );
      } else if (totalFeatures > 0) {
        onToast(`Imported and saved ${totalFeatures} feature${totalFeatures !== 1 ? 's' : ''} from ${fileList.length} file${fileList.length !== 1 ? 's' : ''}`);
      }

      await queryClient.invalidateQueries({ queryKey: ['assets', projectId] });
      await queryClient.invalidateQueries({ queryKey: ['parcels', projectId] });
      await queryClient.invalidateQueries({ queryKey: ['restrictedAreas', projectId] });
    } finally {
      setIsProcessing(false);
    }
  }

  return { handleFiles, isProcessing };
}
