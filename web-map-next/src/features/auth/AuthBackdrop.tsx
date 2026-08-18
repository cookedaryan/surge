/**
 * The ambient field behind the sign-in screen.
 *
 * <p>An abstraction of what the product does: a substation, turbines around it, and feeders drawn
 * between them. Deliberately not a real network — no site's geometry, no claim to be data.
 *
 * <p>Pure SVG and CSS. No canvas, no per-frame JavaScript, nothing running after the animation
 * settles; this sits behind a login screen that may be left open, and a backdrop that keeps a core
 * busy indefinitely to look impressive is not a trade worth making.
 *
 * <p>Marked aria-hidden and drawn entirely in decorative tones — it carries no information, and
 * under reduced motion the paths render in their final state rather than animating in.
 */

/** Feeder runs, as [substation-relative] cubic paths with their approximate lengths for the draw. */
const FEEDERS: { d: string; len: number; delay: number }[] = [
  { d: 'M300 300 C 220 280, 170 220, 120 150', len: 230, delay: 0 },
  { d: 'M300 300 C 250 210, 260 140, 250 60', len: 250, delay: 140 },
  { d: 'M300 300 C 380 250, 420 200, 470 130', len: 240, delay: 280 },
  { d: 'M300 300 C 390 320, 450 350, 520 340', len: 230, delay: 420 },
  { d: 'M300 300 C 250 380, 200 420, 130 440', len: 230, delay: 560 },
  { d: 'M300 300 C 320 390, 340 440, 330 510', len: 220, delay: 700 }
];

/** Turbine positions, matched to the far end of each feeder. */
const TURBINES: { x: number; y: number; delay: number }[] = [
  { x: 120, y: 150, delay: 900 },
  { x: 250, y: 60, delay: 1000 },
  { x: 470, y: 130, delay: 1100 },
  { x: 520, y: 340, delay: 1200 },
  { x: 130, y: 440, delay: 1300 },
  { x: 330, y: 510, delay: 1400 }
];

export function AuthBackdrop() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      <svg
        viewBox="0 0 640 580"
        className="absolute left-1/2 top-1/2 h-[125%] w-auto min-w-[125%] -translate-x-1/2 -translate-y-1/2 opacity-[0.55]"
        fill="none"
      >
        <defs>
          <pattern id="surge-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0H0V40" stroke="var(--border)" strokeWidth="1" fill="none" />
          </pattern>
          <radialGradient id="surge-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.20" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </radialGradient>
          {/* Fades the grid out at the edges so it reads as depth rather than as a tiled texture. */}
          <radialGradient id="surge-grid-fade" cx="50%" cy="50%" r="50%">
            <stop offset="40%" stopColor="#fff" stopOpacity="1" />
            <stop offset="100%" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
          <mask id="surge-grid-mask">
            <rect width="640" height="580" fill="url(#surge-grid-fade)" />
          </mask>
        </defs>

        <rect width="640" height="580" fill="url(#surge-grid)" mask="url(#surge-grid-mask)" />
        <circle cx="300" cy="300" r="240" fill="url(#surge-glow)" />

        {FEEDERS.map((f, i) => (
          <path
            key={i}
            d={f.d}
            stroke="var(--accent)"
            strokeOpacity={0.5}
            strokeWidth={1.5}
            strokeLinecap="round"
            className="animate-draw"
            style={{
              // The dash gap is the path's own length, so the stroke starts fully retracted and the
              // keyframe pulls the offset to zero — drawing the line on rather than fading it in.
              strokeDasharray: f.len,
              ['--draw-len' as string]: f.len,
              animationDelay: `${f.delay}ms`
            }}
          />
        ))}

        {TURBINES.map((t, i) => (
          <g key={i} className="animate-fade-in" style={{ animationDelay: `${t.delay}ms`, animationFillMode: 'backwards' }}>
            <circle cx={t.x} cy={t.y} r={9} fill="var(--accent)" fillOpacity={0.10} />
            <circle cx={t.x} cy={t.y} r={3.5} fill="var(--accent)" fillOpacity={0.85} />
          </g>
        ))}

        <g className="animate-fade-in" style={{ animationDelay: '820ms', animationFillMode: 'backwards' }}>
          <circle cx={300} cy={300} r={16} fill="var(--warning)" fillOpacity={0.12} />
          <rect x={292} y={292} width={16} height={16} rx={3} fill="var(--warning)" fillOpacity={0.9} />
        </g>
      </svg>

      {/* Sinks the backdrop toward the page edges so the card always has contrast behind it,
          whatever the viewport does to the SVG's scale. */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_20%,var(--bg)_78%)]" />
    </div>
  );
}
