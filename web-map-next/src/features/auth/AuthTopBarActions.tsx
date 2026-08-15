import { useAuthStore } from '../../lib/store';
import { Button } from '../../components/ui';

export function AuthTopBarActions() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const username = useAuthStore((s) => s.username);
  const role = useAuthStore((s) => s.role);
  const logout = useAuthStore((s) => s.logout);

  if (!isAuthenticated) return null;
  const cleanRole = (role || 'ENGINEER').replace('ROLE_', '');

  return (
    <>
      <span className="text-[11.5px] text-textMuted">
        {username || 'Engineer'} ({cleanRole})
      </span>
      <Button size="sm" onClick={logout}>Logout</Button>
    </>
  );
}
