import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: api.listProjects });
}

export function useProjectAssets(projectId: string | null) {
  return useQuery({
    queryKey: ['assets', projectId],
    queryFn: () => api.getProjectAssetsGeoJson(projectId as string),
    enabled: !!projectId
  });
}

export function useParcels(projectId: string | null) {
  return useQuery({
    queryKey: ['parcels', projectId],
    queryFn: () => api.getParcelsGeoJson(projectId as string),
    enabled: !!projectId
  });
}

export function useRestrictedAreas(projectId: string | null) {
  return useQuery({
    queryKey: ['restrictedAreas', projectId],
    queryFn: () => api.getRestrictedAreasGeoJson(projectId as string),
    enabled: !!projectId
  });
}

export function useRoutes(projectId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ['routes', projectId, jobId],
    queryFn: () => api.getRoutesGeoJson(projectId as string, jobId),
    enabled: !!projectId
  });
}

export function useBomReport(projectId: string | null) {
  return useQuery({
    queryKey: ['bom', projectId],
    queryFn: () => api.getBomReport(projectId as string),
    enabled: !!projectId
  });
}

export function useAuditLogs() {
  return useQuery({ queryKey: ['auditLogs'], queryFn: api.getAuditLogs });
}

export function useScenarioComparison(projectId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['scenarioComparison', projectId],
    queryFn: () => api.getScenarioComparison(projectId as string),
    enabled: !!projectId && enabled
  });
}
