import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ProjectSelector } from './ProjectSelector';
import { useUiStore, useAuthStore } from '../../lib/store';

/**
 * The selector must never create a project on the operator's behalf.
 *
 * <p>It used to, whenever the list came back empty — and an empty list is not only an empty
 * account. A failed or rejected request produced the same `[]`, so a server the app could not read
 * yet was indistinguishable from one holding nothing, and the app answered by writing to it.
 */

const createProject = vi.fn();
let projectsState: { data?: unknown[]; isLoading: boolean; isError: boolean } = {
  data: [],
  isLoading: false,
  isError: false
};

vi.mock('../../lib/query', () => ({
  useProjects: () => ({ ...projectsState, isSuccess: !projectsState.isError && !projectsState.isLoading, refetch: vi.fn(), isFetching: false }),
  useCreateProject: () => ({ mutateAsync: createProject, mutate: createProject, isPending: false, data: undefined })
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('ProjectSelector', () => {
  beforeEach(() => {
    createProject.mockReset();
    useAuthStore.setState({ isAuthenticated: true, username: 'admin', role: 'ROLE_ADMIN' });
    useUiStore.setState({ currentProjectId: null, newProjectModalOpen: false });
  });

  it('invents nothing for an account with no projects', async () => {
    projectsState = { data: [], isLoading: false, isError: false };
    render(<ProjectSelector />, { wrapper });

    expect(await screen.findByText(/no projects yet/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /create the first project/i })).toBeTruthy();

    // The whole point: an empty account is offered a project, never given one.
    await waitFor(() => expect(createProject).not.toHaveBeenCalled());
    expect(useUiStore.getState().currentProjectId).toBeNull();
  });

  it('reports a failed load as a failure rather than as an empty account', async () => {
    projectsState = { data: undefined, isLoading: false, isError: true };
    render(<ProjectSelector />, { wrapper });

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy();
    // Nothing may be written on top of data the app could not read.
    expect(createProject).not.toHaveBeenCalled();
    expect(screen.queryByText(/no projects yet/i)).toBeNull();
  });

  it('says it is loading rather than showing an empty account', () => {
    projectsState = { data: undefined, isLoading: true, isError: false };
    render(<ProjectSelector />, { wrapper });

    expect(screen.getByRole('status')).toBeTruthy();
    expect(screen.queryByText(/no projects yet/i)).toBeNull();
    expect(createProject).not.toHaveBeenCalled();
  });

  it('selects the first project the server actually returned', async () => {
    projectsState = { data: [{ id: 'p1', name: 'Kutch' }, { id: 'p2', name: 'Bhuj' }], isLoading: false, isError: false };
    render(<ProjectSelector />, { wrapper });

    await waitFor(() => expect(useUiStore.getState().currentProjectId).toBe('p1'));
    expect(createProject).not.toHaveBeenCalled();
  });

  it('falls back when the selected project is no longer in the list', async () => {
    // A project deleted elsewhere, or a different account signing in. Holding the stale id means
    // every subsequent request is made against something the API will reject.
    useUiStore.setState({ currentProjectId: 'gone' });
    projectsState = { data: [{ id: 'p1', name: 'Kutch' }], isLoading: false, isError: false };
    render(<ProjectSelector />, { wrapper });

    await waitFor(() => expect(useUiStore.getState().currentProjectId).toBe('p1'));
  });
});
