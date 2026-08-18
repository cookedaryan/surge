import { FormEvent, useId, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuthStore } from '../../lib/store';
import { Button } from '../../components/ui';
import { AuthBackdrop } from './AuthBackdrop';

export function AuthGateway() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const sessionExpired = useAuthStore((s) => s.sessionExpired);
  const login = useAuthStore((s) => s.login);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const queryClient = useQueryClient();
  const userFieldId = useId();
  const passFieldId = useId();

  if (isAuthenticated) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.login(username.trim(), password.trim());
      login(res.username, res.role);
      // Queries that ran before sign-in were rejected and cached as failures. Without this the
      // workstation loads behind an empty project list until the operator reloads by hand.
      await queryClient.invalidateQueries();
    } catch (err) {
      setError('Authentication failed: ' + (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const fieldClass =
    'h-9 w-full rounded-md border border-borderStrong bg-surface2 px-2.5 text-sm text-text outline-none ' +
    'transition-[border-color,box-shadow] duration-fast ease-out ' +
    'placeholder:text-textFaint focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-100)]';

  return (
    <div className="fixed inset-0 z-[20000] flex items-center justify-center bg-bg font-ui">
      <AuthBackdrop />

      <form
        onSubmit={handleSubmit}
        className="relative w-[352px] max-w-[92vw] animate-slide-up rounded-xl border border-borderStrong bg-panel/95 p-6 shadow-3 backdrop-blur-sm"
      >
        <div className="mb-5 flex items-center gap-2.5">
          <svg viewBox="0 0 24 24" className="h-6 w-6 text-accent" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
          </svg>
          <div>
            <div className="text-lg font-bold tracking-wide text-text">SURGE</div>
            <div className="text-sm text-textFaint">Collector &amp; Evacuation Engine</div>
          </div>
        </div>

        {/* The e2e suite binds to this text, and it is also the heading. Kept as a real h2 rather
            than decorative markup so it is reachable by heading navigation. */}
        <h2 className="m-0 mb-2 text-base font-bold text-text">Sign in to SURGE</h2>

        {sessionExpired ? (
          <p role="status" className="m-0 mb-4 rounded-md border border-warning/40 bg-warningSoft px-2.5 py-2 text-sm text-text">
            Your session expired and you were signed out. Sign in again to carry on — any run
            already started keeps going on the server.
          </p>
        ) : (
          <p className="m-0 mb-4 text-sm text-textFaint">Engineering access is required to load or edit project data.</p>
        )}

        <div className="flex flex-col gap-3">
          <div className="animate-slide-up" style={{ animationDelay: '60ms', animationFillMode: 'backwards' }}>
            <label htmlFor={userFieldId} className="mb-1.5 block text-sm text-textMuted">
              Username
            </label>
            <input
              id={userFieldId}
              className={fieldClass}
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="animate-slide-up" style={{ animationDelay: '100ms', animationFillMode: 'backwards' }}>
            <label htmlFor={passFieldId} className="mb-1.5 block text-sm text-textMuted">
              Password
            </label>
            <div className="relative">
              <input
                id={passFieldId}
                className={`${fieldClass} pr-9`}
                placeholder="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                className="absolute right-1 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-textFaint
                           transition-colors duration-fast ease-out hover:text-text"
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  {showPassword ? (
                    <>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <path d="M1 1l22 22" />
                    </>
                  ) : (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </>
                  )}
                </svg>
              </button>
            </div>
          </div>

          {error && (
            <div role="alert" className="flex items-start gap-1.5 text-sm text-danger">
              <svg viewBox="0 0 24 24" className="mt-px h-3.5 w-3.5 flex-none" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <path d="M12 8v5m0 3.5h.01" />
                <circle cx="12" cy="12" r="10" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            loading={submitting}
            className="mt-1 h-9 justify-center animate-slide-up"
            style={{ animationDelay: '140ms', animationFillMode: 'backwards' }}
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </div>
      </form>
    </div>
  );
}
