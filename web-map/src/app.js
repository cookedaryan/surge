/* ==========================================================================
   SURGE GIS Web Application — Main Application Orchestration
   ========================================================================== */

import { api } from './api.js';
import { SurgeMapEngine } from './map.js';

class SurgeApp {
  constructor() {
    this.mapEngine = null;
    this.currentProjectId = null;
    this.currentJobId = null;
    this.projects = [];

    this.init();
  }

  async init() {
    // 1. Initialize Map
    this.mapEngine = new SurgeMapEngine('map');

    // 2. Setup Event Listeners
    this.bindEvents();

    // 3. Load Projects List
    await this.loadProjects();
  }

  bindEvents() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tabId = e.currentTarget.getAttribute('data-tab');
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        e.currentTarget.classList.add('active');
        document.getElementById(tabId).classList.add('active');
      });
    });

    // Project selection dropdown
    const projectSelect = document.getElementById('projectSelect');
    projectSelect.addEventListener('change', (e) => {
      this.selectProject(e.target.value);
    });

    // New Project Modal
    const btnNewProject = document.getElementById('btnNewProject');
    const modalNewProject = document.getElementById('modalNewProject');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const btnCancelModal = document.getElementById('btnCancelModal');
    const btnSaveProject = document.getElementById('btnSaveProject');

    btnNewProject.addEventListener('click', () => modalNewProject.classList.remove('hidden'));
    const closeModal = () => modalNewProject.classList.add('hidden');
    btnCloseModal.addEventListener('click', closeModal);
    btnCancelModal.addEventListener('click', closeModal);

    btnSaveProject.addEventListener('click', async () => {
      const name = document.getElementById('newProjectName').value.trim();
      const desc = document.getElementById('newProjectDesc').value.trim();
      if (!name) return alert('Please enter a project name.');

      try {
        const newProj = await api.createProject(name, desc);
        closeModal();
        await this.loadProjects();
        this.selectProject(newProj.id);
      } catch (err) {
        alert('Failed to create project: ' + err.message);
      }
    });

    // GeoJSON Drag & Drop Upload
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) {
        this.handleFileUpload(e.dataTransfer.files[0]);
      }
    });
    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length) {
        this.handleFileUpload(e.target.files[0]);
      }
    });

    // Optimization Parameter Sliders
    const sliders = [
      { id: 'feederCapacity', badge: 'valFeederCapacity', decimals: 1 },
      { id: 'maxSpan', badge: 'valMaxSpan', decimals: 0 },
      { id: 'voltageKv', badge: 'valVoltageKv', decimals: 1 }
    ];
    sliders.forEach(s => {
      const el = document.getElementById(s.id);
      const badge = document.getElementById(s.badge);
      el.addEventListener('input', () => {
        badge.textContent = parseFloat(el.value).toFixed(s.decimals);
      });
    });

    // Run Optimization Action
    document.getElementById('btnRunOptimization').addEventListener('click', () => {
      this.runOptimization();
    });

    // Layer Checkboxes
    const layerChecks = [
      { id: 'chkShowWtgs', layer: 'wtgs' },
      { id: 'chkShowSubstations', layer: 'substations' },
      { id: 'chkShowRoutes', layer: 'routes' },
      { id: 'chkShowParcels', layer: 'parcels' },
      { id: 'chkShowRestricted', layer: 'restricted' }
    ];
    layerChecks.forEach(item => {
      document.getElementById(item.id).addEventListener('change', (e) => {
        this.mapEngine.setLayerVisibility(item.layer, e.target.checked);
      });
    });

    // Export CSV Button
    document.getElementById('btnDownloadCsv').addEventListener('click', () => {
      if (!this.currentProjectId) return alert('Select a project first.');
      const url = api.getBomCsvUrl(this.currentProjectId, this.currentJobId);
      window.open(url, '_blank');
    });
  }

  async loadProjects() {
    try {
      this.projects = await api.listProjects();
      const select = document.getElementById('projectSelect');
      select.innerHTML = '';

      this.projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
      });

      if (this.projects.length > 0) {
        this.selectProject(this.projects[0].id);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  }

  async selectProject(projectId) {
    if (!projectId) return;
    this.currentProjectId = projectId;
    document.getElementById('projectSelect').value = projectId;

    await this.refreshProjectData();
  }

  async refreshProjectData() {
    if (!this.currentProjectId) return;

    try {
      // 1. Fetch Assets (WTGs & Substations)
      const assetsGeoJson = await api.getProjectAssetsGeoJson(this.currentProjectId);
      
      const wtgsList = (assetsGeoJson.features || []).filter(f => (f.properties?.assetType || '').toUpperCase() === 'WTG');
      const subList = (assetsGeoJson.features || []).filter(f => (f.properties?.assetType || '').toUpperCase() === 'SUBSTATION');

      document.getElementById('countWtgs').textContent = wtgsList.length;
      document.getElementById('countSubstations').textContent = subList.length;

      this.mapEngine.renderWtgs({ type: 'FeatureCollection', features: wtgsList });
      this.mapEngine.renderSubstations({ type: 'FeatureCollection', features: subList });

      // 2. Fetch Parcels
      const parcelsGeoJson = await api.getParcelsGeoJson(this.currentProjectId);
      document.getElementById('countParcels').textContent = (parcelsGeoJson.features || []).length;
      this.mapEngine.renderParcels(parcelsGeoJson);

      // 3. Fetch Restricted Areas
      const restrictedGeoJson = await api.getRestrictedAreasGeoJson(this.currentProjectId);
      document.getElementById('countRestricted').textContent = (restrictedGeoJson.features || []).length;
      this.mapEngine.renderRestrictedAreas(restrictedGeoJson);

      // 4. Fetch Feeder Routes
      const routesGeoJson = await api.getRoutesGeoJson(this.currentProjectId, this.currentJobId);
      this.mapEngine.renderRoutes(routesGeoJson);

      // 5. Update BOM Report Dashboard
      await this.updateBomReport();

      // 6. Fit Map View to all features
      this.mapEngine.fitAllBounds();
    } catch (err) {
      console.error('Error refreshing project data:', err);
    }
  }

  async handleFileUpload(file) {
    if (!this.currentProjectId) return alert('Please select or create a project first.');

    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const content = e.target.result;
        const selectedType = document.querySelector('input[name="assetImportType"]:checked').value;

        if (selectedType === 'parcel') {
          await api.importParcelsGeoJson(this.currentProjectId, content);
        } else if (selectedType === 'restricted') {
          await api.importRestrictedAreasGeoJson(this.currentProjectId, content);
        } else {
          await api.importGeoJsonAssets(this.currentProjectId, content);
        }

        alert('GeoJSON assets imported successfully!');
        await this.refreshProjectData();
      } catch (err) {
        alert('Failed to import GeoJSON: ' + err.message);
      }
    };
    reader.readAsText(file);
  }

  async runOptimization() {
    if (!this.currentProjectId) return alert('Please select a project first.');

    const jobBox = document.getElementById('jobStatusBox');
    const progressBar = document.getElementById('jobProgressBar');
    const statusMsg = document.getElementById('jobStatusMessage');

    jobBox.classList.remove('hidden');
    progressBar.style.width = '30%';
    statusMsg.textContent = 'Dispatching request to Python FastAPI Engine...';

    const params = {
      scenario: document.getElementById('optimScenario').value,
      feederCapacityMw: parseFloat(document.getElementById('feederCapacity').value),
      maxSpanMeters: parseFloat(document.getElementById('maxSpan').value),
      voltageKv: parseFloat(document.getElementById('voltageKv').value)
    };

    try {
      const job = await api.runOptimization(this.currentProjectId, params);
      this.currentJobId = job.id;

      progressBar.style.width = '70%';
      statusMsg.textContent = 'Calculating A* cost surface & feeder topology...';

      setTimeout(async () => {
        progressBar.style.width = '100%';
        statusMsg.textContent = 'Optimization completed cleanly!';

        await this.refreshProjectData();

        setTimeout(() => jobBox.classList.add('hidden'), 2000);
      }, 1200);

    } catch (err) {
      progressBar.style.width = '100%';
      progressBar.style.backgroundColor = 'var(--accent-red)';
      statusMsg.textContent = 'Optimization failed: ' + err.message;
    }
  }

  async updateBomReport() {
    try {
      const bom = await api.getBomReport(this.currentProjectId, this.currentJobId);

      const lengthKm = bom.totalNetworkLengthMeters ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
      document.getElementById('bomTotalLength').textContent = `${lengthKm} km`;
      document.getElementById('bomTotalPoles').textContent = bom.totalPoles || 0;

      const cost = bom.totalEstimatedCost ? bom.totalEstimatedCost.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : '$0.00';
      document.getElementById('bomTotalCost').textContent = cost;

      const losses = bom.totalElectricalLossesKw ? bom.totalElectricalLossesKw.toFixed(2) : '0.00';
      document.getElementById('bomTotalLosses').textContent = `${losses} kW`;
    } catch (err) {
      console.warn('Failed to update BOM report UI:', err);
    }
  }
}

// Instantiate App when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.surgeApp = new SurgeApp();
});
