import { FormEvent, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuthStore } from '../../lib/store';
import { Button } from '../../components/ui';

export function AuthGateway() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const login = useAuthStore((s) => s.login);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const queryClient = useQueryClient();

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

  return (
    <div className="fixed inset-0 z-[20000] flex items-center justify-center bg-black/85 font-ui">
      <form onSubmit={handleSubmit} className="w-[320px] bg-panel border border-borderStrong rounded-lg p-5 flex flex-col gap-3">
        <h2 className="m-0 text-[13.5px] font-bold text-text">Sign in to SURGE</h2>
        <p className="m-0 text-[11.5px] text-textFaint">Engineering access is required to load or edit project data.</p>
        <input
          className="h-8 rounded-md border border-borderStrong bg-surface2 px-2.5 text-[11.5px] text-text outline-none focus:border-accent"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />
        <input
          className="h-8 rounded-md border border-borderStrong bg-surface2 px-2.5 text-[11.5px] text-text outline-none focus:border-accent"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {error && <div className="text-[11.5px] text-danger">{error}</div>}
        <Button type="submit" variant="primary" disabled={submitting} className="justify-center">
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </div>
  );
}
