import { useEffect } from 'react';
import { api, getToken } from '../../lib/api';
import { useAuthStore } from '../../lib/store';

/**
 * Rehydrates the signed-in identity after a page reload.
 *
 * The store infers "signed in" from a token existing in storage, but the username and role live
 * only in memory and are lost on reload. Without this an administrator would come back with no
 * role and silently lose the admin tab. Asking the server also revalidates the token, so an
 * expired session is caught on load rather than at the first action.
 */
export function useSessionRestore(): void {
  const username = useAuthStore((s) => s.username);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const login = useAuthStore((s) => s.login);

  useEffect(() => {
    if (!isAuthenticated || username || !getToken()) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.getCurrentUser();
        if (!cancelled) login(me.username, me.role);
      } catch {
        // A rejected token already triggers the shared unauthorized handler, which signs out.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, username, login]);
}
