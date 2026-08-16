import { FormEvent, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { AdminUser, UserRole } from '../../lib/api';
import { useAdminUsers } from '../../lib/query';
import { useAuthStore, useUiStore } from '../../lib/store';
import { Card, CardTitle, Button, Select, ConfirmDialog } from '../../components/ui';

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: 'ROLE_ADMIN', label: 'Administrator' },
  { value: 'ROLE_ENGINEER', label: 'Engineer' },
  { value: 'ROLE_VIEWER', label: 'Viewer' }
];

const ROLE_LABEL: Record<UserRole, string> = {
  ROLE_ADMIN: 'Administrator',
  ROLE_ENGINEER: 'Engineer',
  ROLE_VIEWER: 'Viewer'
};

/** Minimum accepted by the backend; kept in sync so the user is told before the round trip. */
const MIN_PASSWORD_LENGTH = 8;

const inputClass =
  'h-8 w-full rounded-md border border-borderStrong bg-surface2 px-2.5 text-[11.5px] text-text outline-none focus:border-accent';

export function AdminPane() {
  const role = useAuthStore((s) => s.role);
  const currentUsername = useAuthStore((s) => s.username);
  const isAdmin = role === 'ROLE_ADMIN';
  const { data: users = [], isLoading, isError, refetch } = useAdminUsers(isAdmin);

  if (!isAdmin) {
    return (
      <Card>
        <CardTitle>User Administration</CardTitle>
        <p className="m-0 text-[11.5px] text-textMuted">
          Administrator access is required to manage accounts.
        </p>
      </Card>
    );
  }

  return (
    <>
      <CreateUserCard onDone={refetch} />
      <Card>
        <div className="flex items-center justify-between mb-2">
          <h3 className="m-0 text-[11.5px] font-bold uppercase tracking-wide text-textMuted">
            Accounts ({users.length})
          </h3>
          <Button size="sm" onClick={() => refetch()}>Refresh</Button>
        </div>
        {isLoading && <div className="text-[11.5px] text-textFaint">Loading…</div>}
        {isError && <div className="text-[11.5px] text-danger">Failed to load accounts.</div>}
        <div className="flex flex-col gap-2.5">
          {users.map((user) => (
            <UserRow key={user.id} user={user} isSelf={user.username === currentUsername} onChanged={refetch} />
          ))}
        </div>
      </Card>
    </>
  );
}

function CreateUserCard({ onDone }: { onDone: () => void }) {
  const showToast = useUiStore((s) => s.showToast);
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('ROLE_ENGINEER');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      showToast(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`, 'error');
      return;
    }
    setBusy(true);
    try {
      await api.createUser({ username: username.trim(), email: email.trim(), password, role: newRole });
      showToast(`Account "${username.trim()}" created.`, 'success');
      setUsername('');
      setEmail('');
      setPassword('');
      setNewRole('ROLE_ENGINEER');
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      onDone();
    } catch (err) {
      showToast(readError(err), 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle>User Administration</CardTitle>
        <Button size="sm" onClick={() => setOpen((v) => !v)}>{open ? 'Cancel' : '+ New user'}</Button>
      </div>
      {!open && (
        <p className="m-0 text-[11.5px] text-textMuted">
          Accounts are provisioned here. There is no self-service sign-up.
        </p>
      )}
      {open && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-2 mt-1">
          <input className={inputClass} placeholder="Username" value={username}
                 onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
          <input className={inputClass} placeholder="Email" type="email" value={email}
                 onChange={(e) => setEmail(e.target.value)} autoComplete="off" />
          <input className={inputClass} placeholder={`Initial password (min ${MIN_PASSWORD_LENGTH})`}
                 type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 autoComplete="new-password" />
          <Select value={newRole} onValueChange={(v) => setNewRole(v as UserRole)}
                  options={ROLE_OPTIONS} className="w-full" />
          <Button type="submit" variant="primary" disabled={busy} className="justify-center">
            {busy ? 'Creating…' : 'Create account'}
          </Button>
          <p className="m-0 text-[11.5px] text-textFaint">
            Share the initial password out of band — it is never shown again.
          </p>
        </form>
      )}
    </Card>
  );
}

function UserRow({ user, isSelf, onChanged }: { user: AdminUser; isSelf: boolean; onChanged: () => void }) {
  const showToast = useUiStore((s) => s.showToast);
  const queryClient = useQueryClient();
  const [resetting, setResetting] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [busy, setBusy] = useState(false);
  // Held until confirmed. Both of these take effect within a second now that the authentication
  // filter checks every token against its account, so a stray click is felt immediately.
  const [pendingRole, setPendingRole] = useState<UserRole | null>(null);
  const [pendingSuspend, setPendingSuspend] = useState(false);

  async function run(action: () => Promise<unknown>, successMessage: string) {
    setBusy(true);
    try {
      await action();
      showToast(successMessage, 'success');
      await queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      onChanged();
    } catch (err) {
      showToast(readError(err), 'error');
    } finally {
      setBusy(false);
    }
  }

  async function handleReset(e: FormEvent) {
    e.preventDefault();
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      showToast(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`, 'error');
      return;
    }
    await run(() => api.resetUserPassword(user.id, newPassword), `Password reset for "${user.username}".`);
    setNewPassword('');
    setResetting(false);
  }

  return (
    <div className="border-b border-border pb-2.5 last:border-b-0 flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[11.5px] text-text font-semibold truncate">{user.username}</span>
            {isSelf && <span className="text-[11.5px] text-accent uppercase tracking-wide">you</span>}
            {!user.enabled && (
              <span className="text-[11.5px] text-danger uppercase tracking-wide">suspended</span>
            )}
          </div>
          <div className="text-[11.5px] text-textFaint truncate">{user.email}</div>
        </div>
        <span className="text-[11.5px] text-textMuted flex-none">{ROLE_LABEL[user.role]}</span>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        <Select
          value={user.role}
          onValueChange={(v) => setPendingRole(v as UserRole)}
          options={ROLE_OPTIONS}
          className="flex-1 min-w-[120px]"
        />
        <Button
          size="sm"
          disabled={busy || isSelf}
          title={isSelf ? 'You cannot suspend your own account' : undefined}
          onClick={() => setPendingSuspend(true)}
        >
          {user.enabled ? 'Suspend' : 'Reinstate'}
        </Button>
        <Button size="sm" disabled={busy} onClick={() => setResetting((v) => !v)}>
          {resetting ? 'Cancel' : 'Reset password'}
        </Button>
      </div>

      {resetting && (
        <form onSubmit={handleReset} className="flex items-center gap-1.5">
          <input
            className={inputClass}
            placeholder={`New password (min ${MIN_PASSWORD_LENGTH})`}
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
          />
          <Button type="submit" variant="primary" size="sm" disabled={busy}>Set</Button>
        </form>
      )}

      <ConfirmDialog
        open={pendingRole !== null}
        title="Change this account's role?"
        body={
          `"${user.username}" becomes ${pendingRole ? ROLE_LABEL[pendingRole] : ''} instead of ${ROLE_LABEL[user.role]}. ` +
          `This applies straight away — if they are signed in, their access changes without them doing anything.`
        }
        confirmLabel="Change role"
        onCancel={() => setPendingRole(null)}
        onConfirm={() => {
          const role = pendingRole;
          setPendingRole(null);
          if (role) run(() => api.updateUser(user.id, { role }), `Role updated for "${user.username}".`);
        }}
      />

      <ConfirmDialog
        open={pendingSuspend}
        title={user.enabled ? 'Suspend this account?' : 'Reinstate this account?'}
        body={
          user.enabled
            ? `"${user.username}" will be signed out within seconds and will not be able to sign back in until reinstated.`
            : `"${user.username}" will be able to sign in again. They will need to sign in fresh; their old session is not restored.`
        }
        confirmLabel={user.enabled ? 'Suspend' : 'Reinstate'}
        onCancel={() => setPendingSuspend(false)}
        onConfirm={() => {
          setPendingSuspend(false);
          run(
            () => api.updateUser(user.id, { enabled: !user.enabled }),
            `"${user.username}" ${user.enabled ? 'suspended' : 'reinstated'}.`
          );
        }}
      />
    </div>
  );
}

/**
 * Backend errors arrive as a JSON envelope in the thrown message. Surface the human-readable part
 * so a refused action (e.g. "Cannot suspend the only remaining administrator") explains itself
 * rather than showing raw JSON.
 */
function readError(err: unknown): string {
  const raw = (err as Error)?.message ?? 'Request failed.';
  try {
    const parsed = JSON.parse(raw);
    return parsed.message || raw;
  } catch {
    return raw;
  }
}
