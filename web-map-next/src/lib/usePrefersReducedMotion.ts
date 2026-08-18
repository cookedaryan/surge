import { useEffect, useState } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

/**
 * The reduced-motion preference, for animation that JavaScript drives.
 *
 * <p>CSS-driven motion does not need this — globals.css collapses every duration token under the
 * same media query. Only animation computed in JS, such as a counter stepping through values on
 * rAF, has to ask. Subscribed rather than read once, because the preference can be toggled while
 * the app is open and an operator who turns it on mid-session means it now.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia?.(QUERY).matches === true
  );

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia(QUERY);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  return reduced;
}
