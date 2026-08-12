import { useMemo } from 'react';
import type { Feature, FeatureCollection } from 'geojson';
import { useBomReport, useParcels, useProjectAssets, useRestrictedAreas, useRoutes } from '../../lib/query';
import type { BomReport } from '../../lib/api';

export interface ProjectMapData {
  wtgs: FeatureCollection;
  substations: FeatureCollection;
  towers: FeatureCollection;
  referenceLines: FeatureCollection;
  parcels: FeatureCollection;
  restrictedAreas: FeatureCollection;
  routes: FeatureCollection;
  counts: {
    wtgsTotal: number;
    wtgsOptimisable: number;
    substations: number;
    towers: number;
    referenceLines: number;
    parcels: number;
    restrictedAreas: number;
  };
  bom: BomReport | undefined;
  isLoading: boolean;
}

function byType(fc: FeatureCollection | undefined, type: string): Feature[] {
  return (fc?.features || []).filter((f) => ((f.properties as any)?.assetType || '').toUpperCase() === type);
}

function toCollection(features: Feature[]): FeatureCollection {
  return { type: 'FeatureCollection', features };
}

export function useProjectData(projectId: string | null, jobId: string | null): ProjectMapData {
  const assetsQuery = useProjectAssets(projectId);
  const parcelsQuery = useParcels(projectId);
  const restrictedQuery = useRestrictedAreas(projectId);
  const routesQuery = useRoutes(projectId, jobId);
  const bomQuery = useBomReport(projectId);

  return useMemo(() => {
    const wtgsList = byType(assetsQuery.data, 'WTG');
    const subList = byType(assetsQuery.data, 'SUBSTATION');
    const towerList = byType(assetsQuery.data, 'EVACUATION_TOWER');
    const lineList = byType(assetsQuery.data, 'REFERENCE_LINE');
    const wtgsOptimisable = wtgsList.filter((f) => (f.properties as any)?.optimisable !== false).length;

    return {
      wtgs: toCollection(wtgsList),
      substations: toCollection(subList),
      towers: toCollection(towerList),
      referenceLines: toCollection(lineList),
      parcels: parcelsQuery.data ?? { type: 'FeatureCollection', features: [] },
      restrictedAreas: restrictedQuery.data ?? { type: 'FeatureCollection', features: [] },
      routes: routesQuery.data ?? { type: 'FeatureCollection', features: [] },
      counts: {
        wtgsTotal: wtgsList.length,
        wtgsOptimisable,
        substations: subList.length,
        towers: towerList.length,
        referenceLines: lineList.length,
        parcels: (parcelsQuery.data?.features || []).length,
        restrictedAreas: (restrictedQuery.data?.features || []).length
      },
      bom: bomQuery.data,
      isLoading: assetsQuery.isLoading || parcelsQuery.isLoading || restrictedQuery.isLoading || routesQuery.isLoading
    };
  }, [assetsQuery.data, parcelsQuery.data, restrictedQuery.data, routesQuery.data, bomQuery.data, assetsQuery.isLoading, parcelsQuery.isLoading, restrictedQuery.isLoading, routesQuery.isLoading]);
}
