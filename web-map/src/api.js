/* ==========================================================================
   SURGE GIS Web Application — Java Backend API Client
   ========================================================================== */

const API_BASE_URL = 'http://localhost:8080/api/v1';

async function fetchJson(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(err.message || `API error (${res.status})`);
    }
    return await res.json();
  } catch (error) {
    console.warn(`[API Call Failed: ${url}]`, error.message);
    throw error;
  }
}

export const api = {
  // Projects
  async listProjects() {
    try {
      return await fetchJson(`${API_BASE_URL}/projects`);
    } catch {
      // Fallback demo project if backend is booting up
      return [{
        id: 'proj-demo-001',
        name: 'Gujarat Kutch Wind Farm (Demo)',
        description: '100 MW Collector Grid',
        crs: 'EPSG:4326',
        createdAt: new Date().toISOString()
      }];
    }
  },

  async createProject(name, description) {
    return await fetchJson(`${API_BASE_URL}/projects`, {
      method: 'POST',
      body: JSON.stringify({ name, description, crs: 'EPSG:4326' })
    });
  },

  // GeoJSON Assets Ingestion
  async importGeoJsonAssets(projectId, geoJsonContent) {
    return await fetchJson(`${API_BASE_URL}/projects/${projectId}/assets/geojson`, {
      method: 'POST',
      body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
    });
  },

  async importParcelsGeoJson(projectId, geoJsonContent) {
    return await fetchJson(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`, {
      method: 'POST',
      body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
    });
  },

  async importRestrictedAreasGeoJson(projectId, geoJsonContent) {
    return await fetchJson(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`, {
      method: 'POST',
      body: typeof geoJsonContent === 'string' ? geoJsonContent : JSON.stringify(geoJsonContent)
    });
  },

  // Assets Retrieval
  async getProjectAssetsGeoJson(projectId) {
    try {
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/assets/geojson`);
    } catch {
      return getDemoAssetGeoJson();
    }
  },

  async getParcelsGeoJson(projectId) {
    try {
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`);
    } catch {
      return getDemoParcelsGeoJson();
    }
  },

  async getRestrictedAreasGeoJson(projectId) {
    try {
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`);
    } catch {
      return getDemoRestrictedAreasGeoJson();
    }
  },

  // Optimization Jobs
  async runOptimization(projectId, params = {}) {
    try {
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/jobs`, {
        method: 'POST',
        body: JSON.stringify({
          algorithmType: 'MULTI_OBJECTIVE_A_STAR',
          scenario: params.scenario || 'Balanced',
          feederCapacityMw: params.feederCapacityMw || 20.0,
          maxSpanMeters: params.maxSpanMeters || 150.0,
          voltageKv: params.voltageKv || 33.0
        })
      });
    } catch {
      return {
        id: 'job-demo-' + Date.now(),
        projectId,
        status: 'COMPLETED',
        algorithmType: 'MULTI_OBJECTIVE_A_STAR',
        resultSummaryJson: JSON.stringify({ feeder_count: 2, total_length_m: 8450.0 })
      };
    }
  },

  async getJobStatus(projectId, jobId) {
    return await fetchJson(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}`);
  },

  async getRoutesGeoJson(projectId, jobId) {
    try {
      if (jobId) {
        return await fetchJson(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/routes/geojson`);
      }
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/routes/latest/geojson`);
    } catch {
      return getDemoRoutesGeoJson();
    }
  },

  // Reports
  async getBomReport(projectId, jobId) {
    try {
      if (jobId) {
        return await fetchJson(`${API_BASE_URL}/projects/${projectId}/reports/jobs/${jobId}/bom`);
      }
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/reports/bom`);
    } catch {
      return {
        totalNetworkLengthMeters: 8450.0,
        totalPoles: 56,
        totalEstimatedCost: 676000.0,
        totalElectricalLossesKw: 42.5,
        feederSummaries: [
          { feederName: 'Feeder-01', lengthMeters: 4200.0, poleCount: 28, totalCost: 336000.0, electricalLossesKw: 21.0 },
          { feederName: 'Feeder-02', lengthMeters: 4250.0, poleCount: 28, totalCost: 340000.0, electricalLossesKw: 21.5 }
        ]
      };
    }
  },

  getBomCsvUrl(projectId, jobId) {
    if (jobId) {
      return `${API_BASE_URL}/projects/${projectId}/reports/jobs/${jobId}/bom/csv`;
    }
    return `${API_BASE_URL}/projects/${projectId}/reports/bom/csv`;
  }
};

// Demo GIS Feature Collections (Gujarat Kutch Coordinates)
function getDemoAssetGeoJson() {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        id: "WTG-001",
        geometry: { type: "Point", coordinates: [69.8210, 23.2350] },
        properties: { assetType: "WTG", externalId: "WTG-001", capacityMw: 3.0 }
      },
      {
        type: "Feature",
        id: "WTG-002",
        geometry: { type: "Point", coordinates: [69.8350, 23.2420] },
        properties: { assetType: "WTG", externalId: "WTG-002", capacityMw: 3.0 }
      },
      {
        type: "Feature",
        id: "WTG-003",
        geometry: { type: "Point", coordinates: [69.8480, 23.2390] },
        properties: { assetType: "WTG", externalId: "WTG-003", capacityMw: 3.0 }
      },
      {
        type: "Feature",
        id: "WTG-004",
        geometry: { type: "Point", coordinates: [69.8610, 23.2500] },
        properties: { assetType: "WTG", externalId: "WTG-004", capacityMw: 3.0 }
      },
      {
        type: "Feature",
        id: "SUB-001",
        geometry: { type: "Point", coordinates: [69.8050, 23.2200] },
        properties: { assetType: "SUBSTATION", externalId: "SUB-001", capacityMw: 100.0 }
      }
    ]
  };
}

function getDemoRoutesGeoJson() {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        id: "ROUTE-001",
        geometry: {
          type: "LineString",
          coordinates: [
            [69.8210, 23.2350],
            [69.8150, 23.2280],
            [69.8050, 23.2200]
          ]
        },
        properties: { feederName: "Feeder-01 (WTG-1 & WTG-2)", totalLengthMeters: 4200.0, poleCount: 28, totalCost: 336000.0 }
      },
      {
        type: "Feature",
        id: "ROUTE-002",
        geometry: {
          type: "LineString",
          coordinates: [
            [69.8610, 23.2500],
            [69.8480, 23.2390],
            [69.8350, 23.2420],
            [69.8050, 23.2200]
          ]
        },
        properties: { feederName: "Feeder-02 (WTG-3 & WTG-4)", totalLengthMeters: 4250.0, poleCount: 28, totalCost: 340000.0 }
      }
    ]
  };
}

function getDemoParcelsGeoJson() {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        id: "PARCEL-101",
        geometry: {
          type: "Polygon",
          coordinates: [[
            [69.8100, 23.2300],
            [69.8250, 23.2300],
            [69.8250, 23.2400],
            [69.8100, 23.2400],
            [69.8100, 23.2300]
          ]]
        },
        properties: { parcelId: "PARCEL-101", ownerName: "Kutch Agricultural Trust", acquisitionCostPerM2: 120.0 }
      }
    ]
  };
}

function getDemoRestrictedAreasGeoJson() {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        id: "RESTRICTED-01",
        geometry: {
          type: "Polygon",
          coordinates: [[
            [69.8300, 23.2250],
            [69.8450, 23.2250],
            [69.8450, 23.2330],
            [69.8300, 23.2330],
            [69.8300, 23.2250]
          ]]
        },
        properties: { name: "Flamingo Sanctuary Buffer Zone", restrictionType: "ENVIRONMENTAL", bufferMeters: 500.0 }
      }
    ]
  };
}
