import { useEffect } from 'react';
import { useProjects } from '../../lib/query';
import { useAuthStore, useUiStore } from '../../lib/store';
import { Select, Button, Skeleton } from '../../components/ui';
import { NewProjectModal } from './NewProjectModal';

/**
 * Picks the project everything else in the workstation is scoped to.
 *
 * <p>This used to create a project called "Default Workstation Project" whenever the list came
 * back empty. Two things were wrong with that. An empty list is not only an empty account — a
 * rejected or failed request produced the same `[]`, so a server the app could not read yet was
 * indistinguishable from one with nothing in it, and the app responded by writing to it. And even
 * when the account really was empty, the operator was silently placed inside a project they had
 * not named, had no reason to trust, and would go on to import a real survey into.
 *
 * <p>So the four states are now distinguished and none of them writes: loading says so, a failure
 * says so and offers a retry, an empty account is invited to create the first project by hand, and
 * only a list with something in it selects anything.
 */
export function ProjectSelector() {
  const { data: projects, isLoading, isError, refetch, isFetching } = useProjects();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setCurrentProjectId = useUiStore((s) => s.setCurrentProjectId);
  const setNewProjectModalOpen = useUiStore((s) => s.setNewProjectModalOpen);

  useEffect(() => {
    if (!isAuthenticated || !projects || projects.length === 0) return;
    // Selecting the first project is a convenience, not a creation: it only ever points at
    // something the server already returned.
    if (!currentProjectId) setCurrentProjectId(projects[0].id);
    // The selected project can also disappear — deleted elsewhere, or belonging to an account that
    // just signed out and back in as someone else. Falling back beats holding an id the API will
    // reject on every subsequent request.
    else if (!projects.some((p) => p.id === currentProjectId)) setCurrentProjectId(projects[0].id);
  }, [isAuthenticated, projects, currentProjectId, setCurrentProjectId]);

  if (isLoading) {
    return (
      <>
        <Skeleton className="h-8 w-[160px] rounded-md" />
        <span className="sr-only" role="status">
          Loading projects
        </span>
      </>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2">
        <span role="alert" className="text-sm text-danger">
          Projects could not be loaded.
        </span>
        <Button size="sm" onClick={() => refetch()} loading={isFetching}>
          Retry
        </Button>
      </div>
    );
  }

  const hasProjects = !!projects && projects.length > 0;

  return (
    <>
      {hasProjects ? (
        <>
          <Select
            value={currentProjectId || ''}
            onValueChange={setCurrentProjectId}
            options={projects.map((p) => ({ value: p.id, label: p.name }))}
            className="min-w-[160px]"
          />
          <Button size="sm" onClick={() => setNewProjectModalOpen(true)}>
            + New
          </Button>
        </>
      ) : (
        <>
          <span className="text-sm text-textFaint">No projects yet</span>
          <Button size="sm" variant="primary" onClick={() => setNewProjectModalOpen(true)}>
            Create the first project
          </Button>
        </>
      )}
      <NewProjectModal />
    </>
  );
}
