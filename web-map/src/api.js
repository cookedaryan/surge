/* ==========================================================================
   SURGE GIS Web Application — API Client Integration Service
   ========================================================================== */

const API_BASE_URL = '/api/v1';

async function fetchJson(url, options = {}) {
  const token = localStorage.getItem('surge_jwt_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP Error ${response.status}`);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return await response.json();
  }

  return await response.text();
}

function emptyGeoJson() {
  return { type: 'FeatureCollection', features: [] };
}

export const api = {
  // Auth & Session
  async login(username, password) {
    const res = await fetchJson(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    if (res.token) localStorage.setItem('surge_jwt_token', res.token);
    return res;
  },

  async register(username, email, password) {
    const res = await fetchJson(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      body: JSON.stringify({ username, email, password, role: 'ROLE_ENGINEER' })
    });
    if (res.token) localStorage.setItem('surge_jwt_token', res.token);
    return res;
  },

  async getAuditLogs() {
    try {
      return await fetchJson(`${API_BASE_URL}/audit-logs`);
    } catch {
      return [];
    }
  },

  // Projects
  async listProjects() {
    try {
      const list = await fetchJson(`${API_BASE_URL}/projects`);
      if (Array.isArray(list)) return list;
      return [];
    } catch {
      return [];
    }
  },

  async createProject(name, description) {
    try {
      return await fetchJson(`${API_BASE_URL}/projects`, {
        method: 'POST',
        body: JSON.stringify({ name, description, crs: 'EPSG:4326' })
      });
    } catch (err) {
      console.warn('[Create Project API Fallback]', err);
      return {
        id: 'proj-' + Date.now(),
        name: name || 'Default Workstation Project',
        description: description || 'Grid Evacuation Workspace',
        crs: 'EPSG:4326',
        createdAt: new Date().toISOString()
      };
    }
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
      const res = await fetchJson(`${API_BASE_URL}/projects/${projectId}/assets/geojson`);
      if (res && Array.isArray(res.features)) return res;
    } catch (e) {
      console.warn('[Assets API Error]', e);
    }
    return emptyGeoJson();
  },

  async getParcelsGeoJson(projectId) {
    try {
      const res = await fetchJson(`${API_BASE_URL}/projects/${projectId}/parcels/geojson`);
      if (res && Array.isArray(res.features)) return res;
    } catch (e) {
      console.warn('[Parcels API Error]', e);
    }
    return emptyGeoJson();
  },

  async getRestrictedAreasGeoJson(projectId) {
    try {
      const res = await fetchJson(`${API_BASE_URL}/projects/${projectId}/restricted-areas/geojson`);
      if (res && Array.isArray(res.features)) return res;
    } catch (e) {
      console.warn('[Restricted API Error]', e);
    }
    return emptyGeoJson();
  },

  async getRoutesGeoJson(projectId, jobId) {
    try {
      if (jobId) {
        const res = await fetchJson(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/routes/geojson`);
        if (res && Array.isArray(res.features)) return res;
      }
    } catch (e) {
      console.warn('[Routes API Error]', e);
    }
    return emptyGeoJson();
  },

  // Optimization Jobs
  async runOptimization(projectId, params = {}) {
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
  },

  async getJobStatus(projectId, jobId) {
    return await fetchJson(`${API_BASE_URL}/projects/${projectId}/jobs/${jobId}`);
  },

  listenJobProgress(projectId, jobId, onProgress, onError, onComplete) {
    const url = `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/progress`;
    let eventSource;
    try {
      eventSource = new EventSource(url);

      eventSource.addEventListener('progress', (e) => {
        try {
          const data = JSON.parse(e.data);
          if (onProgress) onProgress(data);
          if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            eventSource.close();
            if (data.status === 'COMPLETED' && onComplete) onComplete(data);
            if (data.status === 'FAILED' && onError) onError(new Error(data.message || 'Job failed'));
          }
        } catch (err) {
          console.warn('[SSE Parse Error]', err);
        }
      });

      eventSource.onerror = (err) => {
        eventSource.close();
        if (onError) onError(err);
      };

      return () => eventSource.close();
    } catch (err) {
      if (onError) onError(err);
      return () => {};
    }
  },

  // Reports
  async getBomReport(projectId) {
    try {
      return await fetchJson(`${API_BASE_URL}/projects/${projectId}/reports/bom`);
    } catch {
      return {
        totalNetworkLengthMeters: 0,
        totalPoles: 0,
        totalEstimatedCost: 0,
        totalElectricalLossesKw: 0,
        feederSummaries: []
      };
    }
  },

  getPdfReportUrl(projectId) {
    return `${API_BASE_URL}/projects/${projectId}/reports/pdf`;
  },

  getBomCsvUrl(projectId, jobId) {
    if (jobId) {
      return `${API_BASE_URL}/projects/${projectId}/jobs/${jobId}/reports/bom/csv`;
    }
    return `${API_BASE_URL}/projects/${projectId}/reports/bom/csv`;
  },

  async getScenarioComparison(projectId) {
    return await fetchJson(`${API_BASE_URL}/projects/${projectId}/reports/scenarios/compare`);
  }
};
