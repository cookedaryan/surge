/* ==========================================================================
   SURGE GIS Web Application — Leaflet Map Engine & Layers
   ========================================================================== */

/* global L */
import { SVG_ICONS } from './icons.js';

export class SurgeMapEngine {
  constructor(containerId) {
    this.map = L.map(containerId, {
      center: [23.2350, 69.8210],
      zoom: 13,
      zoomControl: false
    });

    // Add Zoom Control to bottom right
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    // Basemaps
    const darkCarto = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; CartoDB &copy; OpenStreetMap'
    });

    const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Esri World Imagery'
    });

    // Default to Dark Carto
    darkCarto.addTo(this.map);

    const baseMaps = {
      "Dark Grid": darkCarto,
      "Satellite": esriSatellite
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(this.map);

    // Layer Groups
    this.layers = {
      wtgs: L.featureGroup().addTo(this.map),
      substations: L.featureGroup().addTo(this.map),
      towers: L.featureGroup().addTo(this.map),
      referenceLines: L.featureGroup().addTo(this.map),
      routes: L.featureGroup().addTo(this.map),
      parcels: L.featureGroup().addTo(this.map),
      restricted: L.featureGroup().addTo(this.map),
      imported: L.featureGroup().addTo(this.map)
    };
  }

  // Clear all or specific layers
  clearAll() {
    Object.values(this.layers).forEach(layerGroup => layerGroup.clearLayers());
  }

  // Render WTG Points
  renderWtgs(geoJson) {
    this.layers.wtgs.clearLayers();
    if (!geoJson || !geoJson.features) return;

    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const props = feature.properties || {};
        // Turbines whose micro-siting status excludes them (cancelled, low AEP, to be shifted) are
        // drawn dimmed so it is obvious at a glance which locations the optimiser will actually use.
        const excluded = props.optimisable === false;
        const icon = L.divIcon({
          className: `custom-leaflet-marker wtg-marker${excluded ? ' wtg-excluded' : ''}`,
          html: `<div class="marker-pin wtg-pin${excluded ? ' wtg-pin-excluded' : ''}">${SVG_ICONS.wtg}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });
        const marker = L.marker(latlng, { icon });
        const status = props.status || 'UNKNOWN';
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.wtg} Wind Turbine Generator</h4>
            <div class="popup-row"><span>Turbine ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Capacity:</span> <strong>${props.capacityMw || 3.0} MW</strong></div>
            <div class="popup-row"><span>Status:</span> <strong>${status.replace(/_/g, ' ')}</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
            ${excluded ? '<div class="popup-note">Excluded from optimisation by status.</div>' : ''}
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.wtgs);
  }

  // Render Substation Points
  renderSubstations(geoJson) {
    this.layers.substations.clearLayers();
    if (!geoJson || !geoJson.features) return;

    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const icon = L.divIcon({
          className: 'custom-leaflet-marker sub-marker',
          html: `<div class="marker-pin sub-pin">${SVG_ICONS.substation}</div>`,
          iconSize: [34, 34],
          iconAnchor: [17, 17]
        });
        const marker = L.marker(latlng, { icon });
        const props = feature.properties || {};
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.substation} Substation</h4>
            <div class="popup-row"><span>Substation ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Grid Capacity:</span> <strong>${props.capacityMw || 100} MW</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.substations);
  }

  // Render Evacuation / Transmission Towers
  // Reference assets: existing line structures that are displayed but excluded from optimisation.
  renderTowers(geoJson) {
    this.layers.towers.clearLayers();
    if (!geoJson || !geoJson.features) return;

    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const icon = L.divIcon({
          className: 'custom-leaflet-marker tower-marker',
          html: `<div class="marker-pin tower-pin">${SVG_ICONS.tower}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });
        const marker = L.marker(latlng, { icon });
        const props = feature.properties || {};
        const towerType = props.towerType ? props.towerType.replace('_', ' ') : 'Tower';
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.tower} Evacuation Tower</h4>
            <div class="popup-row"><span>Tower ID:</span> <strong>${props.externalId || feature.id}</strong></div>
            <div class="popup-row"><span>Structure:</span> <strong>${towerType}</strong></div>
            ${props.lineSection ? `<div class="popup-row"><span>Line section:</span> <strong>${props.lineSection}</strong></div>` : ''}
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
            <div class="popup-note">Existing asset — not part of collector optimisation.</div>
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.towers);
  }

  // Render existing linear site features: roads, HT/EHV lines, watercourses, prior routes.
  // Styled to read as background context, never as SURGE output — generated feeder routes are the
  // only bright solid lines on this map.
  renderReferenceLines(geoJson) {
    this.layers.referenceLines.clearLayers();
    if (!geoJson || !geoJson.features) return;

    const STYLES = {
      ROAD:             { color: '#A8A29E', weight: 2,   dashArray: null,    label: 'Road' },
      HT_LINE:          { color: '#F472B6', weight: 2.5, dashArray: '10 4',  label: 'HT / EHV line' },
      WATERCOURSE:      { color: '#38BDF8', weight: 2.5, dashArray: null,    label: 'Watercourse' },
      EVACUATION_ROUTE: { color: '#A78BFA', weight: 2,   dashArray: '4 4',   label: 'Existing route' },
      UNKNOWN:          { color: '#64748B', weight: 1.5, dashArray: '2 4',   label: 'Unclassified line' }
    };

    L.geoJSON(geoJson, {
      style: (feature) => {
        const style = STYLES[feature.properties?.lineType] || STYLES.UNKNOWN;
        return { color: style.color, weight: style.weight, dashArray: style.dashArray, opacity: 0.75 };
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        const style = STYLES[props.lineType] || STYLES.UNKNOWN;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${style.label}</h4>
            <div class="popup-row"><span>Name:</span> <strong>${props.externalId || 'unnamed'}</strong></div>
            ${props.voltageKv ? `<div class="popup-row"><span>Voltage:</span> <strong>${props.voltageKv} kV</strong></div>` : ''}
            <div class="popup-note">${props.crossingConstraint
              ? 'Crossing this feature adds cost to a route.'
              : 'Reference only — no routing constraint.'}</div>
          </div>
        `);
        layer.on('mouseover', () => layer.setStyle({ weight: style.weight + 2, opacity: 1 }));
        layer.on('mouseout', () => layer.setStyle({ weight: style.weight, opacity: 0.75 }));
      }
    }).addTo(this.layers.referenceLines);
  }

  // Render Feeder Routes with optional scenario color override
  renderRoutes(geoJson, customColor = null) {
    this.layers.routes.clearLayers();
    if (!geoJson || !geoJson.features) return;

    const colors = customColor ? [customColor] : ['#10B981', '#06B6D4', '#3B82F6', '#8B5CF6', '#F59E0B'];
    let idx = 0;

    L.geoJSON(geoJson, {
      style: (feature) => ({
        color: customColor || colors[idx++ % colors.length],
        weight: 5,
        opacity: 0.85,
        dashArray: '10, 6',
        lineCap: 'round'
      }),
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.route} Feeder Route</h4>
            <div class="popup-row"><span>Feeder:</span> <strong>${props.feederName || 'Feeder'}</strong></div>
            <div class="popup-row"><span>Length:</span> <strong>${props.totalLengthMeters ? (props.totalLengthMeters / 1000).toFixed(2) + ' km' : 'N/A'}</strong></div>
            <div class="popup-row"><span>Poles Placed:</span> <strong>${props.poleCount || 0}</strong></div>
            <div class="popup-row"><span>Estimated Cost:</span> <strong>$${(props.totalCost || 0).toLocaleString()}</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.routes);
  }

  // Render Cadastral Parcels
  renderParcels(geoJson, fillOpacity = 0.25) {
    this.layers.parcels.clearLayers();
    if (!geoJson || !geoJson.features) return;

    this.parcelGeoJson = geoJson;
    L.geoJSON(geoJson, {
      style: {
        color: '#8B5CF6',
        weight: 2,
        fillColor: '#8B5CF6',
        fillOpacity: fillOpacity
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.parcel} Cadastral Land Parcel</h4>
            <div class="popup-row"><span>Parcel ID:</span> <strong>${props.parcelId || feature.id}</strong></div>
            <div class="popup-row"><span>Owner:</span> <strong>${props.ownerName || 'Private Owner'}</strong></div>
            <div class="popup-row"><span>Acquisition Rate:</span> <strong>$${props.acquisitionCostPerM2 || 100}/m²</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.parcels);
  }

  // Render Restricted Areas
  renderRestrictedAreas(geoJson, fillOpacity = 0.35) {
    this.layers.restricted.clearLayers();
    if (!geoJson || !geoJson.features) return;

    this.restrictedGeoJson = geoJson;
    L.geoJSON(geoJson, {
      style: {
        color: '#EF4444',
        weight: 2,
        fillColor: '#EF4444',
        fillOpacity: fillOpacity,
        dashArray: '4, 4'
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.restricted} Restricted Area</h4>
            <div class="popup-row"><span>Zone Name:</span> <strong>${props.name || 'Exclusion Zone'}</strong></div>
            <div class="popup-row"><span>Restriction Type:</span> <strong>${props.restrictionType || 'ENVIRONMENTAL'}</strong></div>
            <div class="popup-row"><span>Buffer Distance:</span> <strong>${props.bufferMeters || 0} m</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.restricted);
  }

  // Layer Opacity Setter
  setLayerOpacity(layerName, opacity) {
    if (layerName === 'parcels' && this.parcelGeoJson) {
      this.renderParcels(this.parcelGeoJson, parseFloat(opacity));
    } else if (layerName === 'restricted' && this.restrictedGeoJson) {
      this.renderRestrictedAreas(this.restrictedGeoJson, parseFloat(opacity));
    }
  }

  // Clear imported layer explicitly
  clearImported() {
    this.layers.imported.clearLayers();
  }

  // Force Leaflet to recalculate map container size
  // Must be called after any DOM resize that affects the map container
  invalidateSize() {
    this.map.invalidateSize({ animate: false });
  }

  // Render any custom imported GeoJSON file feature collection live (additive — does NOT clear between files)
  renderImportedGeoJson(geoJson) {
    if (!geoJson) return;

    const importedLayer = L.geoJSON(geoJson, {
      style: (feature) => {
        const geomType = feature.geometry ? feature.geometry.type : '';
        if (geomType.includes('Polygon')) {
          return {
            color: '#06B6D4',
            weight: 2,
            fillColor: '#06B6D4',
            fillOpacity: 0.35
          };
        }
        if (geomType.includes('LineString')) {
          return {
            color: '#10B981',
            weight: 4,
            opacity: 0.9,
            dashArray: '8, 4'
          };
        }
        return { color: '#3B82F6', weight: 2 };
      },
      pointToLayer: (feature, latlng) => {
        const icon = L.divIcon({
          className: 'custom-leaflet-marker wtg-marker',
          html: `<div class="marker-pin wtg-pin">${SVG_ICONS.genericPoint}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });
        const marker = L.marker(latlng, { icon });
        const props = feature.properties || {};
        const title = props.externalId || props.name || props.id || 'Imported Feature';
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.genericPoint} ${title}</h4>
            <div class="popup-row"><span>Type:</span> <strong>${feature.geometry ? feature.geometry.type : 'Point'}</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
          </div>
        `);
        return marker;
      },
      onEachFeature: (feature, layer) => {
        if (feature.geometry && feature.geometry.type.includes('Point')) return;
        const props = feature.properties || {};
        const keys = Object.keys(props).slice(0, 4);
        const rowsHtml = keys.map(k => `<div class="popup-row"><span>${k}:</span> <strong>${props[k]}</strong></div>`).join('');
        layer.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-layer-group text-cyan"></i> Imported GeoJSON Feature</h4>
            ${rowsHtml || '<div class="popup-row"><span>Geometry:</span> <strong>' + feature.geometry.type + '</strong></div>'}
          </div>
        `);
      }
    }).addTo(this.layers.imported);

    try {
      const bounds = importedLayer.getBounds();
      if (bounds && bounds.isValid()) {
        this.map.fitBounds(bounds, { padding: [50, 50] });
      }
    } catch (err) {
      console.warn('Could not fit bounds to imported GeoJSON:', err);
    }
  }

  // Auto Zoom & Fit Bounds to Layer Data
  fitAllBounds() {
    // Collect all individual child layers from every layer group
    const allLayers = [];
    Object.values(this.layers).forEach(layerGroup => {
      layerGroup.eachLayer(layer => allLayers.push(layer));
    });

    if (allLayers.length === 0) return;

    try {
      const group = L.featureGroup(allLayers);
      const bounds = group.getBounds();
      if (bounds && bounds.isValid()) {
        this.map.fitBounds(bounds, { padding: [40, 40] });
      }
    } catch (e) {
      console.warn('Could not fit bounds:', e);
    }
  }

  setLayerVisibility(layerName, visible) {
    if (this.layers[layerName]) {
      if (visible) {
        this.map.addLayer(this.layers[layerName]);
      } else {
        this.map.removeLayer(this.layers[layerName]);
      }
    }
  }

  // Interactive Polyline Vertex Dragging
  enableRouteEditing(enabled, onVertexMoved) {
    if (this.editHandleLayer) {
      this.map.removeLayer(this.editHandleLayer);
      this.editHandleLayer = null;
    }

    if (!enabled) return;

    this.editHandleLayer = L.layerGroup().addTo(this.map);

    this.layers.routes.eachLayer(layerGroup => {
      if (layerGroup instanceof L.GeoJSON) {
        layerGroup.eachLayer(polylineLayer => {
          if (polylineLayer instanceof L.Polyline) {
            const latlngs = polylineLayer.getLatLngs();

            latlngs.forEach((latlng, index) => {
              const handle = L.marker(latlng, {
                draggable: true,
                icon: L.divIcon({
                  className: 'vertex-drag-handle',
                  html: `<div style="width:12px;height:12px;background:#F59E0B;border:2px solid #ffffff;border-radius:50%;cursor:grab;"></div>`,
                  iconSize: [12, 12],
                  iconAnchor: [6, 6]
                })
              });

              handle.on('drag', (e) => {
                const newLatLng = e.target.getLatLng();
                latlngs[index] = newLatLng;
                polylineLayer.setLatLngs(latlngs);

                // Calculate updated path length
                let totalDist = 0;
                for (let i = 0; i < latlngs.length - 1; i++) {
                  totalDist += latlngs[i].distanceTo(latlngs[i + 1]);
                }

                const newPoles = Math.ceil(totalDist / 150.0);
                const newCost = Math.round(totalDist * 80.0);

                if (onVertexMoved) {
                  onVertexMoved(totalDist, newPoles, newCost);
                }
              });

              handle.addTo(this.editHandleLayer);
            });
          }
        });
      }
    });
  }

  // Interactive SVG Route Elevation Profile Render
  renderElevationProfile(svgId, routeGeoJson) {
    const svg = document.getElementById(svgId);
    if (!svg) return;

    // Generate elevation profile points along route coordinates
    let coords = [];
    if (routeGeoJson && routeGeoJson.features && routeGeoJson.features.length > 0) {
      const feat = routeGeoJson.features[0];
      if (feat.geometry && feat.geometry.coordinates) {
        coords = feat.geometry.coordinates;
      }
    }

    if (coords.length < 2) {
      coords = [[69.8210, 23.2350], [69.8150, 23.2280], [69.8050, 23.2200]];
    }

    // Build synthetic elevation profile curve (meters MSL)
    const points = [];
    let cumDist = 0;
    const baseElevation = 45;

    for (let i = 0; i < coords.length; i++) {
      if (i > 0) {
        const p1 = L.latLng(coords[i - 1][1], coords[i - 1][0]);
        const p2 = L.latLng(coords[i][1], coords[i][0]);
        cumDist += p1.distanceTo(p2);
      }
      // Synthetic terrain fluctuation curve
      const elev = baseElevation + Math.sin(i * 1.5) * 18 + Math.cos(i * 0.8) * 12;
      points.push({ dist: cumDist, elev });
    }

    const totalDist = points[points.length - 1].dist || 5000;
    const minElev = 10;
    const maxElev = 90;

    const width = 800;
    const height = 160;
    const padding = 24;

    const scaleX = (d) => padding + (d / totalDist) * (width - 2 * padding);
    const scaleY = (e) => height - padding - ((e - minElev) / (maxElev - minElev)) * (height - 2 * padding);

    let pathD = `M ${scaleX(points[0].dist)},${scaleY(points[0].elev)}`;
    for (let i = 1; i < points.length; i++) {
      pathD += ` L ${scaleX(points[i].dist)},${scaleY(points[i].elev)}`;
    }

    const areaD = pathD + ` L ${scaleX(points[points.length - 1].dist)},${height - padding} L ${scaleX(points[0].dist)},${height - padding} Z`;

    // Render SVG Elements
    svg.innerHTML = `
      <defs>
        <linearGradient id="elevGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.4"/>
          <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.0"/>
        </linearGradient>
      </defs>

      <!-- Grid lines -->
      <line x1="${padding}" y1="${scaleY(30)}" x2="${width - padding}" y2="${scaleY(30)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>
      <line x1="${padding}" y1="${scaleY(60)}" x2="${width - padding}" y2="${scaleY(60)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>

      <!-- Area fill -->
      <path d="${areaD}" fill="url(#elevGrad)"/>

      <!-- Profile Line -->
      <path d="${pathD}" fill="none" stroke="#3B82F6" stroke-width="3" stroke-linecap="round"/>

      <!-- Pole markers along profile -->
      ${points.map((p, idx) => `
        <circle cx="${scaleX(p.dist)}" cy="${scaleY(p.elev)}" r="4" fill="#F59E0B" stroke="#ffffff" stroke-width="1.5">
          <title>Pole #${idx + 1}: ${p.dist.toFixed(0)}m, Elev: ${p.elev.toFixed(1)}m</title>
        </circle>
        <text x="${scaleX(p.dist)}" y="${scaleY(p.elev) - 10}" fill="#9CA3AF" font-size="10" text-anchor="middle">${p.elev.toFixed(0)}m</text>
      `).join('')}

      <!-- Axis Labels -->
      <text x="${padding}" y="${height - 6}" fill="#6B7280" font-size="10">0 m</text>
      <text x="${width - padding}" y="${height - 6}" fill="#6B7280" font-size="10" text-anchor="end">${(totalDist / 1000).toFixed(2)} km</text>
    `;
  }
}
