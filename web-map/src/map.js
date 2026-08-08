/* ==========================================================================
   SURGE GIS Web Application — Leaflet Map Engine & Layers
   ========================================================================== */

/* global L */

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
      wtgs: L.layerGroup().addTo(this.map),
      substations: L.layerGroup().addTo(this.map),
      routes: L.layerGroup().addTo(this.map),
      parcels: L.layerGroup().addTo(this.map),
      restricted: L.layerGroup().addTo(this.map)
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
        const icon = L.divIcon({
          className: 'custom-leaflet-marker wtg-marker',
          html: `<div class="marker-pin wtg-pin"><i class="fa-solid fa-fan"></i></div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });
        const marker = L.marker(latlng, { icon });
        const props = feature.properties || {};
        marker.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-fan text-blue"></i> Wind Turbine Generator</h4>
            <div class="popup-row"><span>Turbine ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Capacity:</span> <strong>${props.capacityMw || 3.0} MW</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
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
          html: `<div class="marker-pin sub-pin"><i class="fa-solid fa-bolt"></i></div>`,
          iconSize: [34, 34],
          iconAnchor: [17, 17]
        });
        const marker = L.marker(latlng, { icon });
        const props = feature.properties || {};
        marker.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-building-zap text-yellow"></i> Substation</h4>
            <div class="popup-row"><span>Substation ID:</span> <strong>${props.externalId || props.id || feature.id}</strong></div>
            <div class="popup-row"><span>Grid Capacity:</span> <strong>${props.capacityMw || 100} MW</strong></div>
            <div class="popup-row"><span>Coordinates:</span> <strong>${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}</strong></div>
          </div>
        `);
        return marker;
      }
    }).addTo(this.layers.substations);
  }

  // Render Feeder Routes
  renderRoutes(geoJson) {
    this.layers.routes.clearLayers();
    if (!geoJson || !geoJson.features) return;

    const colors = ['#10B981', '#06B6D4', '#3B82F6', '#8B5CF6', '#F59E0B'];
    let idx = 0;

    L.geoJSON(geoJson, {
      style: (feature) => ({
        color: colors[idx++ % colors.length],
        weight: 5,
        opacity: 0.85,
        dashArray: '10, 6',
        lineCap: 'round'
      }),
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        layer.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-route text-green"></i> Feeder Route</h4>
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
  renderParcels(geoJson) {
    this.layers.parcels.clearLayers();
    if (!geoJson || !geoJson.features) return;

    L.geoJSON(geoJson, {
      style: {
        color: '#8B5CF6',
        weight: 2,
        fillColor: '#8B5CF6',
        fillOpacity: 0.25
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        layer.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-draw-polygon text-purple"></i> Cadastral Land Parcel</h4>
            <div class="popup-row"><span>Parcel ID:</span> <strong>${props.parcelId || feature.id}</strong></div>
            <div class="popup-row"><span>Owner:</span> <strong>${props.ownerName || 'Private Owner'}</strong></div>
            <div class="popup-row"><span>Acquisition Rate:</span> <strong>$${props.acquisitionCostPerM2 || 100}/m²</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.parcels);
  }

  // Render Restricted Areas
  renderRestrictedAreas(geoJson) {
    this.layers.restricted.clearLayers();
    if (!geoJson || !geoJson.features) return;

    L.geoJSON(geoJson, {
      style: {
        color: '#EF4444',
        weight: 2,
        fillColor: '#EF4444',
        fillOpacity: 0.35,
        dashArray: '4, 4'
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        layer.bindPopup(`
          <div class="popup-card">
            <h4><i class="fa-solid fa-ban text-red"></i> Restricted Area</h4>
            <div class="popup-row"><span>Zone Name:</span> <strong>${props.name || 'Exclusion Zone'}</strong></div>
            <div class="popup-row"><span>Restriction Type:</span> <strong>${props.restrictionType || 'ENVIRONMENTAL'}</strong></div>
            <div class="popup-row"><span>Buffer Distance:</span> <strong>${props.bufferMeters || 0} m</strong></div>
          </div>
        `);
      }
    }).addTo(this.layers.restricted);
  }

  // Auto Zoom & Fit Bounds to Layer Data
  fitAllBounds() {
    const featureGroup = L.featureGroup([
      this.layers.wtgs,
      this.layers.substations,
      this.layers.routes,
      this.layers.parcels,
      this.layers.restricted
    ]);

    if (featureGroup.getLayers().length > 0) {
      try {
        this.map.fitBounds(featureGroup.getBounds(), { padding: [40, 40] });
      } catch (e) {
        console.warn('Could not fit bounds:', e);
      }
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
}
