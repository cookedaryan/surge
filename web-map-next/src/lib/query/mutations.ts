import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { CommitImportBody, OptimizationParams, Project } from '../api';

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description: string }) =>
      api.createProject(name, description),
    onSuccess: (project) => {
      qc.setQueryData<Project[]>(['projects'], (old) => (old ? [...old, project] : [project]));
    }
  });
}

export function usePreviewKmzImport(projectId: string | null) {
  return useMutation({
    mutationFn: (file: File) => api.previewKmzAssets(projectId as string, file)
  });
}

export function useCommitImport(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CommitImportBody) => api.commitAssetImport(projectId as string, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', projectId] });
      qc.invalidateQueries({ queryKey: ['parcels', projectId] });
      qc.invalidateQueries({ queryKey: ['restrictedAreas', projectId] });
    }
  });
}

export function useRunOptimization(projectId: string | null) {
  return useMutation({
    mutationFn: (params: OptimizationParams) => api.runOptimization(projectId as string, params)
  });
}
