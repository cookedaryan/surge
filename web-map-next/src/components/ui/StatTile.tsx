import clsx from 'clsx';
import { ReactNode } from 'react';
import { AnimatedNumber } from './AnimatedNumber';

interface StatTileProps {
  label: string;
  /** A number animates on change; a string is rendered as given, including em-dash for absent. */
  value: number | string | null | undefined;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  tone?: 'default' | 'warn' | 'danger' | 'success';
  hint?: ReactNode;
  className?: string;
}

const TONE_RING: Record<string, string> = {
  default: 'border-border',
  warn: 'border-warning/45',
  danger: 'border-danger/50',
  success: 'border-success/40'
};

const TONE_TEXT: Record<string, string> = {
  default: 'text-text',
  warn: 'text-warning',
  danger: 'text-danger',
  success: 'text-success'
};

/**
 * One labelled engineering figure.
 *
 * <p>Extracted from three near-identical inline copies (asset counts, BOM strip, decision summary)
 * that had already drifted apart in padding and type size.
 *
 * <p>A missing figure renders as an em-dash in the faint tier, never as zero. Zero is a measurement
 * and absence is not, and the difference matters on a screen an engineer costs a network from.
 */
export function StatTile({
  label,
  value,
  decimals = 0,
  prefix,
  suffix,
  tone = 'default',
  hint,
  className
}: StatTileProps) {
  const absent = value === null || value === undefined || value === '';

  return (
    <div
      className={clsx(
        'rounded-md border bg-surface2 px-2 pt-2 pb-1.5 transition-colors duration-fast ease-out',
        TONE_RING[tone],
        className
      )}
    >
      <div className={clsx('font-mono text-base font-semibold tabular leading-none', absent ? 'text-textFaint' : TONE_TEXT[tone])}>
        {absent ? (
          '—'
        ) : typeof value === 'number' ? (
          <AnimatedNumber value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
        ) : (
          <>
            {prefix}
            {value}
            {suffix}
          </>
        )}
      </div>
      <div className="text-sm text-textFaint mt-1">{label}</div>
      {hint && <div className="text-xs text-textFaint mt-0.5">{hint}</div>}
    </div>
  );
}
