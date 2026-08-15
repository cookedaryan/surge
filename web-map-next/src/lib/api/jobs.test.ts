import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listenJobProgress } from './jobs';
import { setToken, setUnauthorizedHandler } from './client';
import type { JobProgress } from './types';

const PROJECT = '11111111-1111-1111-1111-111111111111';
const JOB = '22222222-2222-2222-2222-222222222222';

/** Builds a Response whose body streams the given chunks verbatim. */
function streamingResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    }
  });
  return new Response(body, { status });
}

function frame(payload: Record<string, unknown>): string {
  return `event:progress\ndata:${JSON.stringify(payload)}\n\n`;
}

/** Resolves once the stream has been fully consumed and callbacks have run. */
function flush(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 10));
}

describe('listenJobProgress', () => {
  beforeEach(() => {
    setUnauthorizedHandler(() => {});
  });

  it('sends the bearer token, which EventSource could not do', async () => {
    setToken('a-real-token');
    const fetchMock = vi.fn().mockResolvedValue(
      streamingResponse([frame({ status: 'COMPLETED', progressPercent: 100 })])
    );
    vi.stubGlobal('fetch', fetchMock);

    listenJobProgress(PROJECT, JOB);
    await flush();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain(`/projects/${PROJECT}/jobs/${JOB}/progress`);
    expect(init.headers.Authorization).toBe('Bearer a-real-token');
    // The token must never travel in the query string, where it would land in access logs,
    // browser history and referrer headers.
    expect(String(url)).not.toContain('a-real-token');
  });

  it('reports each progress frame in order', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      frame({ status: 'RUNNING', progressPercent: 10, message: 'Validating' }),
      frame({ status: 'RUNNING', progressPercent: 60, message: 'Routing' }),
      frame({ status: 'COMPLETED', progressPercent: 100, message: 'Done' })
    ])));

    const seen: JobProgress[] = [];
    listenJobProgress(PROJECT, JOB, (p) => seen.push(p));
    await flush();

    expect(seen.map((p) => p.progressPercent)).toEqual([10, 60, 100]);
  });

  /**
   * The transport hands over arbitrary byte chunks, so a frame can be split anywhere — including
   * mid-JSON and between the two newlines that terminate it. Reassembly is the part of this client
   * most likely to break silently.
   */
  it('reassembles a frame split across chunk boundaries', async () => {
    const whole = frame({ status: 'COMPLETED', progressPercent: 100, message: 'Done' });
    const cutA = Math.floor(whole.length / 3);
    const cutB = whole.length - 1; // splits the terminating blank line
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      whole.slice(0, cutA),
      whole.slice(cutA, cutB),
      whole.slice(cutB)
    ])));

    const onComplete = vi.fn();
    listenJobProgress(PROJECT, JOB, undefined, undefined, onComplete);
    await flush();

    expect(onComplete).toHaveBeenCalledOnce();
    expect(onComplete.mock.calls[0][0].status).toBe('COMPLETED');
  });

  it('handles several frames arriving in a single chunk', async () => {
    const combined =
      frame({ status: 'RUNNING', progressPercent: 20 }) +
      frame({ status: 'RUNNING', progressPercent: 80 });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([combined])));

    const seen: JobProgress[] = [];
    listenJobProgress(PROJECT, JOB, (p) => seen.push(p));
    await flush();

    expect(seen.map((p) => p.progressPercent)).toEqual([20, 80]);
  });

  it('accepts CRLF line endings', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      `event:progress\r\ndata:${JSON.stringify({ status: 'COMPLETED' })}\r\n\r\n`
    ])));

    const onComplete = vi.fn();
    listenJobProgress(PROJECT, JOB, undefined, undefined, onComplete);
    await flush();

    expect(onComplete).toHaveBeenCalledOnce();
  });

  it('surfaces a FAILED job as an error rather than a completion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      frame({ status: 'FAILED', message: 'No feasible route' })
    ])));

    const onError = vi.fn();
    const onComplete = vi.fn();
    listenJobProgress(PROJECT, JOB, undefined, onError, onComplete);
    await flush();

    expect(onComplete).not.toHaveBeenCalled();
    expect(onError.mock.calls[0][0].message).toBe('No feasible route');
  });

  it('reports a terminal frame only once', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      frame({ status: 'COMPLETED', progressPercent: 100 }),
      frame({ status: 'COMPLETED', progressPercent: 100 })
    ])));

    const onComplete = vi.fn();
    listenJobProgress(PROJECT, JOB, undefined, undefined, onComplete);
    await flush();

    expect(onComplete).toHaveBeenCalledOnce();
  });

  it('ignores malformed JSON instead of tearing down the stream', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      'event:progress\ndata:{not valid json\n\n',
      frame({ status: 'COMPLETED', progressPercent: 100 })
    ])));
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const onComplete = vi.fn();
    const onError = vi.fn();
    listenJobProgress(PROJECT, JOB, undefined, onError, onComplete);
    await flush();

    expect(onComplete).toHaveBeenCalledOnce();
    expect(onError).not.toHaveBeenCalled();
  });

  /** A rejected token means the session is over; the app must return to the sign-in screen. */
  it('signs the operator out when the stream is rejected as unauthorized', async () => {
    setToken('an-expired-token');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 401 })));
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);

    const onError = vi.fn();
    listenJobProgress(PROJECT, JOB, undefined, onError);
    await flush();

    expect(onUnauthorized).toHaveBeenCalledOnce();
    expect(localStorage.getItem('surge_jwt_token')).toBeNull();
    expect(onError).toHaveBeenCalledOnce();
  });

  it('stops delivering progress once unsubscribed', async () => {
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      async start(controller) {
        controller.enqueue(encoder.encode(frame({ status: 'RUNNING', progressPercent: 10 })));
        await gate;
        controller.enqueue(encoder.encode(frame({ status: 'COMPLETED', progressPercent: 100 })));
        controller.close();
      }
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })));

    const seen: JobProgress[] = [];
    const stop = listenJobProgress(PROJECT, JOB, (p) => seen.push(p));
    await flush();
    stop();
    release?.();
    await flush();

    expect(seen.map((p) => p.progressPercent)).toEqual([10]);
  });
});
