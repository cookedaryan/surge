import { useEffect } from 'react';
import { useCreateProject, useProjects } from '../../lib/query';
import { useAuthStore, useUiStore } from '../../lib/store';
import { Select, Button } from '../../components/ui';
import { NewProjectModal } from './NewProjectModal';

export function ProjectSelector() {
  const { data: projects = [], isSuccess } = useProjects();
  const createProject = useCreateProject();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const setNewProjectModalOpen = useUiStore((s) => s.setNewProjectModalOpen);

  useEffect(() => {
    // Only a signed-in caller can be genuinely empty. Without this guard the pre-login render
    // reads as "no projects" and seeds a stray project every time the app is opened.
    if (!isSuccess || !isAuthenticated) return;
    if (projects.length === 0 && !createProject.isPending && !createProject.data) {
      createProject.mutate({ name: 'Default Workstation Project', description: 'Default Grid Evacuation Workspace' });
      return;
    }
    if (!currentProjectId && projects.length > 0) {
      setCurrentProjectId(projects[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuccess, isAuthenticated, projects, currentProjectId]);

  useEffect(() => {
    if (createProject.data && !currentProjectId) setCurrentProjectId(createProject.data.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createProject.data]);

  return (
    <>
      <Select
        value={currentProjectId || ''}
        onValueChange={setCurrentProjectId}
        options={projects.map((p) => ({ value: p.id, label: p.name }))}
        className="min-w-[160px]"
      />
      <Button size="sm" onClick={() => setNewProjectModalOpen(true)}>+ New</Button>
      <NewProjectModal />
    </>
  );
}
