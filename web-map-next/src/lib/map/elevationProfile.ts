import L from 'leaflet';
import type { FeatureCollection } from 'geojson';

export function renderElevationProfile(svg: SVGSVGElement, routeGeoJson: FeatureCollection): void {
  let coords: number[][] = [];
  if (routeGeoJson && routeGeoJson.features && routeGeoJson.features.length > 0) {
    const feat = routeGeoJson.features[0];
    if (feat.geometry && 'coordinates' in feat.geometry) {
      coords = feat.geometry.coordinates as number[][];
    }
  }
  if (coords.length < 2) {
    coords = [[69.8210, 23.2350], [69.8150, 23.2280], [69.8050, 23.2200]];
  }

  const points: { dist: number; elev: number }[] = [];
  let cumDist = 0;
  const baseElevation = 45;

  for (let i = 0; i < coords.length; i++) {
    if (i > 0) {
      const p1 = L.latLng(coords[i - 1][1], coords[i - 1][0]);
      const p2 = L.latLng(coords[i][1], coords[i][0]);
      cumDist += p1.distanceTo(p2);
    }
    const elev = baseElevation + Math.sin(i * 1.5) * 18 + Math.cos(i * 0.8) * 12;
    points.push({ dist: cumDist, elev });
  }

  const totalDist = points[points.length - 1].dist || 5000;
  const minElev = 10;
  const maxElev = 90;
  const width = 800;
  const height = 160;
  const padding = 24;

  const scaleX = (d: number) => padding + (d / totalDist) * (width - 2 * padding);
  const scaleY = (e: number) => height - padding - ((e - minElev) / (maxElev - minElev)) * (height - 2 * padding);

  let pathD = `M ${scaleX(points[0].dist)},${scaleY(points[0].elev)}`;
  for (let i = 1; i < points.length; i++) pathD += ` L ${scaleX(points[i].dist)},${scaleY(points[i].elev)}`;
  const areaD = `${pathD} L ${scaleX(points[points.length - 1].dist)},${height - padding} L ${scaleX(points[0].dist)},${height - padding} Z`;

  svg.innerHTML = `
    <defs>
      <linearGradient id="elevGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#4E8CFF" stop-opacity="0.4"/>
        <stop offset="100%" stop-color="#4E8CFF" stop-opacity="0.0"/>
      </linearGradient>
    </defs>
    <line x1="${padding}" y1="${scaleY(30)}" x2="${width - padding}" y2="${scaleY(30)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>
    <line x1="${padding}" y1="${scaleY(60)}" x2="${width - padding}" y2="${scaleY(60)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>
    <path d="${areaD}" fill="url(#elevGrad)"/>
    <path d="${pathD}" fill="none" stroke="#4E8CFF" stroke-width="3" stroke-linecap="round"/>
    ${points
      .map(
        (p, idx) => `
      <circle cx="${scaleX(p.dist)}" cy="${scaleY(p.elev)}" r="4" fill="#F5A524" stroke="#ffffff" stroke-width="1.5">
        <title>Pole #${idx + 1}: ${p.dist.toFixed(0)}m, Elev: ${p.elev.toFixed(1)}m</title>
      </circle>
      <text x="${scaleX(p.dist)}" y="${scaleY(p.elev) - 10}" fill="#8B909C" font-size="10" text-anchor="middle">${p.elev.toFixed(0)}m</text>
    `
      )
      .join('')}
    <text x="${padding}" y="${height - 6}" fill="#55585F" font-size="10">0 m</text>
    <text x="${width - padding}" y="${height - 6}" fill="#55585F" font-size="10" text-anchor="end">${(totalDist / 1000).toFixed(2)} km</text>
  `;
}
