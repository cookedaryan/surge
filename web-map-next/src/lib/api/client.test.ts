import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchJson, getToken, setToken, setUnauthorizedHandler, notifyUnauthorized } from './client';

describe('API client authentication handling', () => {
  beforeEach(() => {
    setUnauthorizedHandler(() => {});
  });

  it('attaches the bearer token when one is stored', async () => {
    setToken('a-token');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' }
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    await fetchJson('/api/v1/projects');

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer a-token');
  });

  it('omits the header entirely when signed out', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } })
    );
    vi.stubGlobal('fetch', fetchMock);

    await fetchJson('/api/v1/projects');

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  /**
   * Signed-in state is inferred from a token being present, so a rejected token has to actively
   * clear it. Otherwise the app looks signed in while every request fails, with no way back to the
   * login screen short of clearing storage by hand.
   */
  it('clears the session and notifies when the API rejects the token', async () => {
    setToken('an-expired-token');
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 401 })));

    await expect(fetchJson('/api/v1/projects')).rejects.toThrow();

    expect(getToken()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  /** 403 means "signed in but not allowed" — staying signed in is the correct response. */
  it('keeps the session on a forbidden response', async () => {
    setToken('a-valid-token');
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('nope', { status: 403 })));

    await expect(fetchJson('/api/v1/admin/users')).rejects.toThrow();

    expect(getToken()).toBe('a-valid-token');
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('surfaces the server error body so a refusal can explain itself', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('{"message":"Cannot suspend the only remaining administrator."}', { status: 400 })
    ));

    await expect(fetchJson('/api/v1/admin/users/x')).rejects.toThrow(/only remaining administrator/);
  });

  it('notifyUnauthorized is safe to call from any transport', () => {
    setToken('a-token');
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);

    notifyUnauthorized();

    expect(getToken()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });
});
