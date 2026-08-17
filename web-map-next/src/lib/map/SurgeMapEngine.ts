import L from 'leaflet';
import type { FeatureCollection } from 'geojson';
import { SVG_ICONS } from './icons';
import { FEEDER_COLORS, assignFeederColors, assignFeederDashPatterns, feederNameOf } from './feederColors';
import type { LayerName } from '../store';

import {
  asKm,
  asMoney,
  asMw,
  asPercent,
  asRatePerM2,
  isHighUtilisation,
  shown
} from './popupValues';

export class SurgeMapEngine {
  map: L.Map;
  layers: Record<LayerName, L.FeatureGroup>;
  parcelGeoJson?: FeatureCollection;
  restrictedGeoJson?: FeatureCollection;
  editHandleLayer?: L.LayerGroup;

  constructor(containerId: string) {
    // preferCanvas draws vector layers onto a single canvas instead of one SVG element each. A
    // completed run places several hundred poles — 606 on the reference project — and as SVG that
    // is several hundred DOM nodes to create, style and reflow every time the result changes.
    this.map = L.map(containerId, {
      center: [23.2350, 69.8210],
      zoom: 13,
      zoomControl: false,
      preferCanvas: true
    });
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    const darkCarto = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; CartoDB &copy; OpenStreetMap'
    });
    const esriSatellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 19, attribution: 'Esri World Imagery' }
    );
    darkCarto.addTo(this.map);
    L.control.layers({ 'Dark Grid': darkCarto, Satellite: esriSatellite }, undefined, { position: 'topright' }).addTo(this.map);

    this.layers = {
      wtgs: L.featureGroup().addTo(this.map),
      substations: L.featureGroup().addTo(this.map),
      towers: L.featureGroup().addTo(this.map),
      referenceLines: L.featureGroup().addTo(this.map),
      routes: L.featureGroup().addTo(this.map),
      polesTerminal: L.featureGroup().addTo(this.map),
      polesAngle: L.featureGroup().addTo(this.map),
      polesIntermediate: L.featureGroup().addTo(this.map),
      polesJunction: L.featureGroup().addTo(this.map),
      parcels: L.featureGroup().addTo(this.map),
      restricted: L.featureGroup().addTo(this.map),
      imported: L.featureGroup().addTo(this.map)
    };
  }

  clearAll(): void {
    Object.values(this.layers).forEach((layerGroup) => layerGroup.clearLayers());
  }

  renderWtgs(geoJson: FeatureCollection): void {
    this.layers.wtgs.clearLayers();
    if (!geoJson || !geoJson.features) return;
    L.geoJSON(geoJson, {
      pointToLayer: (feature, latlng) => {
        const props = (feature.properties || {}) as Record<string, any>;
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
            <div class="popup-row"><span>Capacity:</span> <strong>${shown(props.capacityMw, asMw)}</strong></div>
            <div class="popup-row"><span>Status:</span> <strong>${status.replace(/_/g, ' ')}</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
            ${excluded ? '<div class="popup-note">Excluded from optimisation by status.</div>' : ''}
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.wtgs);
  }

  renderSubstations(geoJson: FeatureCollection): void {
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
        const props = (feature.properties || {}) as Record<string, any>;
        marker.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.substation} Substation</h4>
            <div class="popup-row"><span>Substation ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Grid Capacity:</span> <strong>${shown(props.capacityMw, asMw)}</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.substations);
  }

  renderTowers(geoJson: FeatureCollection): void {
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
        const props = (feature.properties || {}) as Record<string, any>;
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

  renderReferenceLines(geoJson: FeatureCollection): void {
    this.layers.referenceLines.clearLayers();
    if (!geoJson || !geoJson.features) return;

    const STYLES: Record<string, { color: string; weight: number; dashArray: string | null; label: string }> = {
      ROAD: { color: '#A8A29E', weight: 2, dashArray: null, label: 'Road' },
      HT_LINE: { color: '#F472B6', weight: 2.5, dashArray: '10 4', label: 'HT / EHV line' },
      WATERCOURSE: { color: '#38BDF8', weight: 2.5, dashArray: null, label: 'Watercourse' },
      EVACUATION_ROUTE: { color: '#A78BFA', weight: 2, dashArray: '4 4', label: 'Existing route' },
      UNKNOWN: { color: '#64748B', weight: 1.5, dashArray: '2 4', label: 'Unclassified line' }
    };

    L.geoJSON(geoJson, {
      style: (feature) => {
        const style = STYLES[feature?.properties?.lineType] || STYLES.UNKNOWN;
        return { color: style.color, weight: style.weight, dashArray: style.dashArray ?? undefined, opacity: 0.75 };
      },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        const style = STYLES[props.lineType] || STYLES.UNKNOWN;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${style.label}</h4>
            <div class="popup-row"><span>Name:</span> <strong>${props.externalId || 'unnamed'}</strong></div>
            ${props.voltageKv ? `<div class="popup-row"><span>Voltage:</span> <strong>${props.voltageKv} kV</strong></div>` : ''}
            <div class="popup-note">${
              props.crossingConstraint ? 'Crossing this feature adds cost to a route.' : 'Reference only — no routing constraint.'
            }</div>
          </div>
        `);
        layer.on('mouseover', () => (layer as L.Path).setStyle({ weight: style.weight + 2, opacity: 1 }));
        layer.on('mouseout', () => (layer as L.Path).setStyle({ weight: style.weight, opacity: 0.75 }));
      }
    }).addTo(this.layers.referenceLines);
  }

  renderRoutes(geoJson: FeatureCollection, customColor: string | null = null): void {
    this.layers.routes.clearLayers();
    if (!geoJson || !geoJson.features) return;
    const feederColour = assignFeederColors(geoJson.features);
    const feederDash = assignFeederDashPatterns(geoJson.features);

    L.geoJSON(geoJson, {
      style: (feature) => {
        const name = feederNameOf(feature);
        return {
          color: customColor || feederColour.get(name) || FEEDER_COLORS[0],
          weight: 5,
          opacity: 0.85,
          // Pattern carries feeder identity alongside colour, so the network stays readable to
          // colour-blind operators and in a greyscale print of the PDF export. A single
          // highlighted route keeps the original dash so it still reads as one selection.
          dashArray: customColor ? '10, 6' : feederDash.get(name) ?? undefined,
          lineCap: 'round'
        };
      },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        const lengthMeters = props.totalLengthMeters ?? props.length_m ?? null;
        // Utilisation says whether the conductor choice is comfortable or marginal, which the type
        // alone does not. Flagged past 85% because that is where an engineer wants to look.
        const utilisation = props.cableUtilisationPct;
        const utilisationClass = isHighUtilisation(utilisation) ? 'popup-warn' : '';
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.route} Feeder Route</h4>
            <div class="popup-row"><span>Feeder:</span> <strong>${shown(props.feederName ?? props.feeder_id)}</strong></div>
            ${props.segmentId ? `<div class="popup-row"><span>Segment:</span> <strong>${props.segmentId}</strong></div>` : ''}
            <div class="popup-row"><span>Length:</span> <strong>${shown(
              lengthMeters,
              asKm
            )}</strong></div>
            <div class="popup-row"><span>Poles Placed:</span> <strong>${shown(props.poleCount)}</strong></div>
            <div class="popup-row"><span>Conductor:</span> <strong>${shown(props.cableTypeId)}</strong></div>
            <div class="popup-row"><span>Utilisation:</span> <strong class="${utilisationClass}">${shown(
              utilisation,
              asPercent
            )}</strong></div>
            ${
              props.cableRequiredCurrentA !== null && props.cableRequiredCurrentA !== undefined
                ? `<div class="popup-row"><span>Current:</span> <strong>${props.cableRequiredCurrentA} A of ${shown(props.cableEffectiveAmpacityA)} A</strong></div>`
                : ''
            }
            <div class="popup-row"><span>Estimated Cost:</span> <strong>${shown(props.totalCost, asMoney)}</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.routes);
  }

  private static readonly POLE_ROLE_STYLE: Record<string, { color: string; radius: number; layer: LayerName }> = {
    terminal: { color: '#F59E0B', radius: 5, layer: 'polesTerminal' },
    angle: { color: '#EF4444', radius: 5, layer: 'polesAngle' },
    junction: { color: '#8B5CF6', radius: 5, layer: 'polesJunction' },
    intermediate: { color: '#94A3B8', radius: 3, layer: 'polesIntermediate' }
  };

  renderPoles(geoJson: FeatureCollection): void {
    this.layers.polesTerminal.clearLayers();
    this.layers.polesAngle.clearLayers();
    this.layers.polesIntermediate.clearLayers();
    this.layers.polesJunction.clearLayers();
    if (!geoJson || !geoJson.features) return;

    for (const feature of geoJson.features) {
      if (feature.geometry?.type !== 'Point') continue;
      const [lng, lat] = feature.geometry.coordinates;
      const props = (feature.properties || {}) as Record<string, any>;
      const role = String(props.poleRole || 'intermediate').toLowerCase();
      const style = SurgeMapEngine.POLE_ROLE_STYLE[role] || SurgeMapEngine.POLE_ROLE_STYLE.intermediate;
      const poleId: string = props.poleId || String(feature.id ?? '');
      const sequenceMatch = poleId.match(/-P0*(\d+)$/);

      const marker = L.circleMarker([lat, lng], {
        radius: style.radius,
        color: style.color,
        weight: 1.5,
        fillColor: style.color,
        fillOpacity: 0.85
      });
      marker.bindPopup(`
        <div class="popup-card">
          <h4>${SVG_ICONS.genericPoint} Pole</h4>
          <div class="popup-row"><span>Pole ID:</span> <strong>${poleId}</strong></div>
          ${props.feederName ? `<div class="popup-row"><span>Feeder:</span> <strong>${props.feederName}</strong></div>` : ''}
          ${sequenceMatch ? `<div class="popup-row"><span>Sequence:</span> <strong>${parseInt(sequenceMatch[1], 10)}</strong></div>` : ''}
          <div class="popup-row"><span>Type:</span> <strong>${props.recommendedPoleType || role}</strong></div>
          <div class="popup-note">Preliminary geometry-based recommendation — not a structural design.</div>
        </div>
      `);
      marker.addTo(this.layers[style.layer]);
    }
  }

  renderParcels(geoJson: FeatureCollection, fillOpacity = 0.25): void {
    this.layers.parcels.clearLayers();
    if (!geoJson || !geoJson.features) return;
    this.parcelGeoJson = geoJson;
    L.geoJSON(geoJson, {
      style: { color: '#8B5CF6', weight: 2, fillColor: '#8B5CF6', fillOpacity },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
        layer.bindPopup(`
          <div class="popup-card">
            <h4>${SVG_ICONS.parcel} Cadastral Land Parcel</h4>
            <div class="popup-row"><span>Parcel ID:</span> <strong>${props.parcelId || feature.id}</strong></div>
            <div class="popup-row"><span>Owner:</span> <strong>${shown(props.ownerName)}</strong></div>
            <div class="popup-row"><span>Acquisition Rate:</span> <strong>${shown(
              props.acquisitionCostPerM2,
              asRatePerM2
            )}</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.parcels);
  }

  renderRestrictedAreas(geoJson: FeatureCollection, fillOpacity = 0.35): void {
    this.layers.restricted.clearLayers();
    if (!geoJson || !geoJson.features) return;
    this.restrictedGeoJson = geoJson;
    L.geoJSON(geoJson, {
      style: { color: '#EF4444', weight: 2, fillColor: '#EF4444', fillOpacity, dashArray: '4, 4' },
      onEachFeature: (feature, layer) => {
        const props = (feature.properties || {}) as Record<string, any>;
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

  setLayerOpacity(layerName: 'parcels' | 'restricted', opacity: number): void {
    if (layerName === 'parcels' && this.parcelGeoJson) {
      this.renderParcels(this.parcelGeoJson, opacity);
    } else if (layerName === 'restricted' && this.restrictedGeoJson) {
      this.renderRestrictedAreas(this.restrictedGeoJson, opacity);
    }
  }

  clearImported(): void {
    this.layers.imported.clearLayers();
  }

  invalidateSize(): void {
    this.map.invalidateSize({ animate: false });
  }

  renderImportedGeoJson(geoJson: FeatureCollection): void {
    if (!geoJson) return;
    const importedLayer = L.geoJSON(geoJson, {
      style: (feature) => {
        const geomType = feature?.geometry ? feature.geometry.type : '';
        if (geomType.includes('Polygon')) return { color: '#06B6D4', weight: 2, fillColor: '#06B6D4', fillOpacity: 0.35 };
        if (geomType.includes('LineString')) return { color: '#10B981', weight: 4, opacity: 0.9, dashArray: '8, 4' };
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
        const props = (feature.properties || {}) as Record<string, any>;
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
        const props = (feature.properties || {}) as Record<string, any>;
        const keys = Object.keys(props).slice(0, 4);
        const rowsHtml = keys.map((k) => `<div class="popup-row"><span>${k}:</span> <strong>${props[k]}</strong></div>`).join('');
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
      if (bounds && bounds.isValid()) this.map.fitBounds(bounds, { padding: [50, 50] });
    } catch (err) {
      console.warn('Could not fit bounds to imported GeoJSON:', err);
    }
  }

  fitAllBounds(): void {
    const allLayers: L.Layer[] = [];
    Object.values(this.layers).forEach((layerGroup) => layerGroup.eachLayer((layer) => allLayers.push(layer)));
    if (allLayers.length === 0) return;
    try {
      const group = L.featureGroup(allLayers);
      const bounds = group.getBounds();
      if (bounds && bounds.isValid()) this.map.fitBounds(bounds, { padding: [40, 40] });
    } catch (e) {
      console.warn('Could not fit bounds:', e);
    }
  }

  setLayerVisibility(layerName: LayerName, visible: boolean): void {
    if (!this.layers[layerName]) return;
    if (visible) this.map.addLayer(this.layers[layerName]);
    else this.map.removeLayer(this.layers[layerName]);
  }

  enableRouteEditing(enabled: boolean, onVertexMoved?: (lengthMeters: number, poles: number, cost: number) => void): void {
    if (this.editHandleLayer) {
      this.map.removeLayer(this.editHandleLayer);
      this.editHandleLayer = undefined;
    }
    if (!enabled) return;

    this.editHandleLayer = L.layerGroup().addTo(this.map);

    this.layers.routes.eachLayer((layerGroup) => {
      if (layerGroup instanceof L.GeoJSON) {
        layerGroup.eachLayer((polylineLayer) => {
          if (polylineLayer instanceof L.Polyline) {
            const latlngs = polylineLayer.getLatLngs() as L.LatLng[];
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
                const newLatLng = (e.target as L.Marker).getLatLng();
                latlngs[index] = newLatLng;
                polylineLayer.setLatLngs(latlngs);
                let totalDist = 0;
                for (let i = 0; i < latlngs.length - 1; i++) totalDist += latlngs[i].distanceTo(latlngs[i + 1]);
                const newPoles = Math.ceil(totalDist / 150.0);
                const newCost = Math.round(totalDist * 80.0);
                if (onVertexMoved) onVertexMoved(totalDist, newPoles, newCost);
              });
              handle.addTo(this.editHandleLayer!);
            });
          }
        });
      }
    });
  }
}
