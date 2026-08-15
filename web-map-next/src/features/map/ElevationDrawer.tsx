import { useEffect, useRef } from 'react';
import type { FeatureCollection } from 'geojson';
import { renderElevationProfile } from '../../lib/map/elevationProfile';
import { useUiStore } from '../../lib/store';

interface ElevationDrawerProps {
  routes: FeatureCollection;
}

export function ElevationDrawer({ routes }: ElevationDrawerProps) {
  const open = useUiStore((s) => s.elevationDrawerOpen);
  const setOpen = useUiStore((s) => s.setElevationDrawerOpen);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const hasRoutes = routes.features.length > 0;
  useEffect(() => {
    if (hasRoutes) setOpen(true);
  }, [hasRoutes, setOpen]);

  useEffect(() => {
    if (open && svgRef.current) renderElevationProfile(svgRef.current, routes);
  }, [open, routes]);

  if (!open) return null;

  return (
    <div className="absolute left-3.5 right-3.5 bottom-3.5 h-[190px] z-[1010] bg-panel border border-borderStrong rounded-lg p-2.5 font-ui">
      <div className="flex items-center justify-between mb-1">
        <h4 className="m-0 text-[11.5px] uppercase tracking-wide text-textFaint font-bold">Elevation Profile</h4>
        {/* The glyph is small but the hit area must not be: this was a 10x12px target. */}
        <button
          onClick={() => setOpen(false)}
          aria-label="Close elevation profile"
          className="-mr-1 flex h-6 w-6 items-center justify-center rounded text-[11.5px] leading-none text-textFaint hover:bg-surface2 hover:text-text"
        >
          ✕
        </button>
      </div>
      <svg ref={svgRef} viewBox="0 0 800 160" className="w-full h-[160px]" />
    </div>
  );
}
