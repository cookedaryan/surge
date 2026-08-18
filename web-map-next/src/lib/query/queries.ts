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

export function usePoles(projectId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ['poles', projectId, jobId],
    queryFn: () => api.getPolesGeoJson(projectId as string, jobId),
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

/**
 * The BOM for one specific run, rather than the project's latest.
 *
 * <p>The run breakdown shows costs next to the decision that produced them, so it must be the same
 * run's costs. `useBomReport` answers with whichever run was costed most recently, which is usually
 * but not always the one on screen.
 */
export function useJobBomReport(projectId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ['bom', projectId, jobId],
    queryFn: () => api.getJobBomReport(projectId as string, jobId as string),
    enabled: !!projectId && !!jobId
  });
}

export function useAuditLogs() {
  return useQuery({ queryKey: ['auditLogs'], queryFn: api.getAuditLogs });
}

const TERMINAL_JOB_STATUSES = ['COMPLETED', 'FAILED', 'CANCELLED'];

/**
 * The current job, polled until it reaches a terminal state.
 *
 * Held in the query cache rather than in component state so a run survives the pane unmounting —
 * the sidebar renders only the active tab, so switching tabs during a run would otherwise discard
 * the result and leave nothing to show when the job finished. It also means a reload lands back on
 * the finished job instead of an empty panel.
 */
export function useJob(projectId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ['job', projectId, jobId],
    queryFn: () => api.getJobStatus(projectId as string, jobId as string),
    enabled: !!projectId && !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && TERMINAL_JOB_STATUSES.includes(status) ? false : 3000;
    }
  });
}

/** Administrator-only; the endpoint 403s for anyone else, so do not fetch it for them. */
export function useAdminUsers(enabled: boolean) {
  return useQuery({ queryKey: ['adminUsers'], queryFn: api.listUsers, enabled });
}

export function useScenarioComparison(projectId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['scenarioComparison', projectId],
    queryFn: () => api.getScenarioComparison(projectId as string),
    enabled: !!projectId && enabled
  });
}
