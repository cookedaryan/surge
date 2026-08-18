import { useEffect, useRef, useState } from 'react';
import { usePrefersReducedMotion } from '../../lib/usePrefersReducedMotion';

interface AnimatedNumberProps {
  value: number;
  /** Decimal places; the count-up and the final value are formatted identically. */
  decimals?: number;
  /** Rendered before/after the number so they don't animate with it. */
  prefix?: string;
  suffix?: string;
  durationMs?: number;
}

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * A figure that counts up to its value when it changes.
 *
 * <p>Used for engineering readouts, which imposes two rules. It always lands exactly on `value` —
 * the final frame assigns the target rather than the interpolation, so a route length never settles
 * on 12.79 km when the server said 12.80. And under reduced motion it renders the value
 * immediately, because the number is the information; the animation is not.
 */
export function AnimatedNumber({ value, decimals = 0, prefix, suffix, durationMs = 650 }: AnimatedNumberProps) {
  const reducedMotion = usePrefersReducedMotion();
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const frameRef = useRef<number>();

  useEffect(() => {
    if (reducedMotion) {
      fromRef.current = value;
      setDisplay(value);
      return;
    }

    const from = fromRef.current;
    if (from === value) return;

    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      if (t >= 1) {
        setDisplay(value);
        fromRef.current = value;
        return;
      }
      setDisplay(from + (value - from) * easeOut(t));
      frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
      // Whatever interrupted the run — a new value, an unmount — the figure on screen must not be
      // left frozen partway to a number the server never reported.
      fromRef.current = value;
    };
  }, [value, durationMs, reducedMotion]);

  return (
    <span className="tabular">
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
