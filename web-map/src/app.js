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

    // 3. Check Session Authentication
    const token = localStorage.getItem('surge_jwt_token');
    if (!token) {
      document.getElementById('authGatewayOverlay').classList.remove('hidden');
    } else {
      document.getElementById('authGatewayOverlay').classList.add('hidden');
      document.getElementById('btnLogout').classList.remove('hidden');
      this.updateUserBadge('Logged In', 'ROLE_ENGINEER');
      await this.loadProjects();
    }
  }

  updateUserBadge(username, role) {
    const badgeText = document.getElementById('userProfileText');
    const logoutBtn = document.getElementById('btnLogout');
    if (badgeText) {
      const cleanRole = (role || 'ENGINEER').replace('ROLE_', '');
      badgeText.textContent = `${username} (${cleanRole})`;
    }
    if (logoutBtn) {
      logoutBtn.classList.remove('hidden');
    }
  }

  bindEvents() {
    // Protected Gateway Login Button
    const btnGatewayLogin = document.getElementById('btnGatewayLogin');
    const authGatewayOverlay = document.getElementById('authGatewayOverlay');

    btnGatewayLogin.addEventListener('click', async () => {
      const u = document.getElementById('gatewayUsername').value.trim();
      const p = document.getElementById('gatewayPassword').value.trim();
      if (!u || !p) return alert('Please enter username and password.');

      try {
        const res = await api.login(u, p);
        authGatewayOverlay.classList.add('hidden');
        this.updateUserBadge(res.username, res.role);
        await this.loadProjects();
      } catch (err) {
        alert('Authentication failed: ' + err.message);
      }
    });

    // Header Logout Action
    document.getElementById('btnLogout').addEventListener('click', () => {
      localStorage.removeItem('surge_jwt_token');
      document.getElementById('userProfileText').textContent = 'Not Authenticated';
      document.getElementById('btnLogout').classList.add('hidden');
      authGatewayOverlay.classList.remove('hidden');
    });

    // Header PDF Export Action
    const btnDownloadPdf = document.getElementById('btnDownloadPdf');
    if (btnDownloadPdf) {
      btnDownloadPdf.addEventListener('click', () => {
        if (!this.currentProjectId) return alert('Please select a project first.');
        window.open(api.getPdfReportUrl(this.currentProjectId), '_blank');
      });
    }

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tabId = e.currentTarget.getAttribute('data-tab');
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        e.currentTarget.classList.add('active');
        document.getElementById(tabId).classList.add('active');
        if (tabId === 'tab-audit') {
          this.loadAuditLogs();
        }
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

      btnSaveProject.disabled = true;
      btnSaveProject.textContent = 'Creating...';
      try {
        const newProj = await api.createProject(name, desc);
        closeModal();
        document.getElementById('newProjectName').value = '';
        document.getElementById('newProjectDesc').value = '';
        // Add to dropdown without re-fetching full list (avoids auto-create race)
        const select = document.getElementById('projectSelect');
        const opt = document.createElement('option');
        opt.value = newProj.id;
        opt.textContent = newProj.name;
        select.appendChild(opt);
        this.projects.push(newProj);
        await this.selectProject(newProj.id);
      } catch (err) {
        alert('Failed to create project: ' + err.message);
      } finally {
        btnSaveProject.disabled = false;
        btnSaveProject.textContent = 'Create Project';
      }
    });

    // Scenario Comparison Modal
    const btnCompareScenarios = document.getElementById('btnCompareScenarios');
    const modalCompareScenarios = document.getElementById('modalCompareScenarios');
    const btnCloseScenarioModal = document.getElementById('btnCloseScenarioModal');
    const btnCloseScenarioModalBottom = document.getElementById('btnCloseScenarioModalBottom');

    btnCompareScenarios.addEventListener('click', () => {
      if (!this.currentProjectId) return alert('Please select a project first.');
      modalCompareScenarios.classList.remove('hidden');
      this.loadScenarioComparison();
    });

    const closeScenarioModal = () => modalCompareScenarios.classList.add('hidden');
    btnCloseScenarioModal.addEventListener('click', closeScenarioModal);
    btnCloseScenarioModalBottom.addEventListener('click', closeScenarioModal);

    // Auth Modal (optional — only present if btnOpenAuthModal exists in the DOM)
    const btnOpenAuthModal = document.getElementById('btnOpenAuthModal');
    const modalAuth = document.getElementById('modalAuth');
    const btnCloseAuthModal = document.getElementById('btnCloseAuthModal');
    const btnCancelAuthModal = document.getElementById('btnCancelAuthModal');
    const btnLoginSubmit = document.getElementById('btnLoginSubmit');

    if (btnOpenAuthModal && modalAuth) {
      btnOpenAuthModal.addEventListener('click', () => modalAuth.classList.remove('hidden'));
      const closeAuthModal = () => modalAuth.classList.add('hidden');
      if (btnCloseAuthModal) btnCloseAuthModal.addEventListener('click', closeAuthModal);
      if (btnCancelAuthModal) btnCancelAuthModal.addEventListener('click', closeAuthModal);
    }

    if (btnLoginSubmit) {
      btnLoginSubmit.addEventListener('click', async () => {
        const u = document.getElementById('authUsername').value.trim();
        const p = document.getElementById('authPassword').value.trim();
        if (!u || !p) return alert('Enter username and password.');

        try {
          const res = await api.login(u, p);
          if (modalAuth) modalAuth.classList.add('hidden');
          document.getElementById('userProfileText').textContent = `${res.username} (${(res.role || 'ROLE_ENGINEER').replace('ROLE_', '')})`;
          this.loadAuditLogs();
        } catch (err) {
          alert('Authentication failed: ' + err.message);
        }
      });
    }

    // Refresh Audit Logs
    document.getElementById('btnRefreshAuditLogs').addEventListener('click', () => {
      this.loadAuditLogs();
    });

    // GeoJSON Drag & Drop & Multi-File Upload
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');

    dropzone.addEventListener('click', (e) => {
      if (e.target !== fileInput) {
        fileInput.click();
      }
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      if (e.dataTransfer.files && e.dataTransfer.files.length) {
        this.handleFileUpload(e.dataTransfer.files);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length) {
        this.handleFileUpload(e.target.files);
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

    // Polygon Opacity Sliders
    const sliderParcelOpacity = document.getElementById('sliderParcelOpacity');
    const valParcelOpacity = document.getElementById('valParcelOpacity');
    sliderParcelOpacity.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value).toFixed(2);
      valParcelOpacity.textContent = val;
      this.mapEngine.setLayerOpacity('parcels', val);
    });

    const sliderRestrictedOpacity = document.getElementById('sliderRestrictedOpacity');
    const valRestrictedOpacity = document.getElementById('valRestrictedOpacity');
    sliderRestrictedOpacity.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value).toFixed(2);
      valRestrictedOpacity.textContent = val;
      this.mapEngine.setLayerOpacity('restricted', val);
    });

    // Interactive Route Edit Mode Toggle
    const chkEnableRouteEdit = document.getElementById('chkEnableRouteEdit');
    chkEnableRouteEdit.addEventListener('change', (e) => {
      this.mapEngine.enableRouteEditing(e.target.checked, (newLengthMeters, newPoles, newCost) => {
        const lengthKm = (newLengthMeters / 1000).toFixed(2);
        document.getElementById('bomTotalLength').textContent = `${lengthKm} km`;
        document.getElementById('bomTotalPoles').textContent = newPoles;
        document.getElementById('bomTotalCost').textContent = `$${newCost.toLocaleString()}`;
      });
    });

    // Elevation Profile Drawer Close Button
    document.getElementById('btnCloseElevationDrawer').addEventListener('click', () => {
      document.getElementById('elevationDrawer').classList.add('hidden');
    });

    // Export CSV Button
    document.getElementById('btnDownloadCsv').addEventListener('click', () => {
      if (!this.currentProjectId) return alert('Select a project first.');
      const url = api.getBomCsvUrl(this.currentProjectId, this.currentJobId);
      window.open(url, '_blank');
    });

    // Export Executive PDF Report Button
    document.getElementById('btnDownloadPdf').addEventListener('click', () => {
      if (!this.currentProjectId) return alert('Select a project first.');
      const url = api.getPdfReportUrl(this.currentProjectId);
      window.open(url, '_blank');
    });
  }

  async loadProjects() {
    try {
      this.projects = await api.listProjects();
      if (!this.projects || this.projects.length === 0) {
        const defaultProj = await api.createProject('Default Workstation Project', 'Default Grid Evacuation Workspace');
        this.projects = [defaultProj];
      }

      const select = document.getElementById('projectSelect');
      select.innerHTML = '';

      this.projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
      });

      if (this.projects.length > 0) {
        await this.selectProject(this.projects[0].id);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
      this.currentProjectId = 'proj-default';
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

      // Render Elevation Profile in Drawer
      document.getElementById('elevationDrawer').classList.remove('hidden');
      this.mapEngine.renderElevationProfile('elevationSvg', routesGeoJson);

      // Refresh Route Edit handles if mode is enabled
      const chkEnableRouteEdit = document.getElementById('chkEnableRouteEdit');
      if (chkEnableRouteEdit && chkEnableRouteEdit.checked) {
        this.mapEngine.enableRouteEditing(true, (newLengthMeters, newPoles, newCost) => {
          const lengthKm = (newLengthMeters / 1000).toFixed(2);
          document.getElementById('bomTotalLength').textContent = `${lengthKm} km`;
          document.getElementById('bomTotalPoles').textContent = newPoles;
          document.getElementById('bomTotalCost').textContent = `$${newCost.toLocaleString()}`;
        });
      }

      // 5. Update BOM Report Dashboard
      await this.updateBomReport();

      // 6. Fit Map View to all features
      this.mapEngine.fitAllBounds();
    } catch (err) {
      console.error('Error refreshing project data:', err);
    }
  }

  readFileText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(e);
      reader.readAsText(file);
    });
  }

  async handleFileUpload(files) {
    if (!files || files.length === 0) return;
    if (!this.currentProjectId) {
      this.currentProjectId = 'proj-default';
    }
    const fileList = Array.from(files);

    // Clear the imported layer once before processing all files
    this.mapEngine.clearImported();

    let allWtgs = [];
    let allSubstations = [];
    let allParcels = [];
    let allRestricted = [];
    let allRoutes = [];
    let totalFeatures = 0;

    const selectedType = document.querySelector('input[name="assetImportType"]:checked')?.value || 'auto';

    for (const file of fileList) {
      console.log(`[SURGE] Processing file: ${file.name} (${file.size} bytes)`);
      try {
        const text = await this.readFileText(file);
        const geoJson = JSON.parse(text);
        const features = geoJson.features || (geoJson.type === 'Feature' ? [geoJson] : []);
        totalFeatures += features.length;
        console.log(`[SURGE] Parsed ${features.length} features from ${file.name}, type=${geoJson.type}`);

        // Render each file's GeoJSON onto the additive imported layer
        this.mapEngine.renderImportedGeoJson(geoJson);
        console.log(`[SURGE] renderImportedGeoJson called for ${file.name}`);

        for (const feat of features) {
          if (!feat.properties) feat.properties = {};

          if (selectedType === 'wtg') {
            feat.properties.assetType = 'WTG';
          } else if (selectedType === 'substation') {
            feat.properties.assetType = 'SUBSTATION';
          } else if (selectedType === 'parcel') {
            feat.properties.assetType = 'PARCEL';
          } else if (selectedType === 'restricted') {
            feat.properties.assetType = 'RESTRICTED';
          }

          const geomType = feat.geometry?.type || '';
          const props = feat.properties || {};
          const assetType = (props.assetType || '').toUpperCase();

          if (geomType === 'Point' || geomType === 'MultiPoint') {
            if (selectedType === 'wtg') {
              allWtgs.push(feat);
            } else if (selectedType === 'substation') {
              allSubstations.push(feat);
            } else if (assetType.includes('SUB') || props.capacityMw > 50 || (props.externalId || '').includes('SUB')) {
              allSubstations.push(feat);
            } else {
              allWtgs.push(feat);
            }
          } else if (geomType === 'LineString' || geomType === 'MultiLineString') {
            allRoutes.push(feat);
          } else if (geomType === 'Polygon' || geomType === 'MultiPolygon') {
            if (selectedType === 'restricted' || (selectedType === 'auto' && (props.restrictionType || props.bufferMeters || (props.externalId || '').includes('RESTR')))) {
              allRestricted.push(feat);
            } else {
              allParcels.push(feat);
            }
          } else {
            allWtgs.push(feat);
          }
        }

        // Asynchronous non-blocking backend import (never delays or blocks local map rendering)
        if (this.currentProjectId && !this.currentProjectId.startsWith('proj-default')) {
          const payload = JSON.stringify(geoJson);
          const isParcel = selectedType === 'parcel' || (selectedType === 'auto' && features.some(f => f.geometry?.type?.includes('Polygon') && !f.properties?.restrictionType));
          const isRestricted = selectedType === 'restricted' || (selectedType === 'auto' && features.some(f => f.geometry?.type?.includes('Polygon') && f.properties?.restrictionType));

          if (isParcel) {
            api.importParcelsGeoJson(this.currentProjectId, payload).catch(err => console.warn('[Backend Import Fallback]', err));
          } else if (isRestricted) {
            api.importRestrictedAreasGeoJson(this.currentProjectId, payload).catch(err => console.warn('[Backend Import Fallback]', err));
          } else {
            api.importGeoJsonAssets(this.currentProjectId, payload).catch(err => console.warn('[Backend Import Fallback]', err));
          }
        }
      } catch (err) {
        console.error(`Failed to parse file ${file.name}:`, err);
      }
    }

    // Render features live on Leaflet map layers immediately
    if (allWtgs.length > 0) {
      this.mapEngine.renderWtgs({ type: 'FeatureCollection', features: allWtgs });
      document.getElementById('countWtgs').textContent = allWtgs.length;
    }
    if (allSubstations.length > 0) {
      this.mapEngine.renderSubstations({ type: 'FeatureCollection', features: allSubstations });
      document.getElementById('countSubstations').textContent = allSubstations.length;
    }
    if (allParcels.length > 0) {
      this.mapEngine.renderParcels({ type: 'FeatureCollection', features: allParcels });
      document.getElementById('countParcels').textContent = allParcels.length;
    }
    if (allRestricted.length > 0) {
      this.mapEngine.renderRestrictedAreas({ type: 'FeatureCollection', features: allRestricted });
      document.getElementById('countRestricted').textContent = allRestricted.length;
    }
    if (allRoutes.length > 0) {
      const routesGeoJson = { type: 'FeatureCollection', features: allRoutes };
      this.mapEngine.renderRoutes(routesGeoJson);
      this.mapEngine.renderElevationProfile('elevationSvg', routesGeoJson);
    }

    // Force Leaflet to recalculate map container size (fixes invisible layers after DOM resize)
    this.mapEngine.invalidateSize();

    // Auto zoom to fit all imported spatial features
    this.mapEngine.fitAllBounds();

    // Show a brief toast so the user knows files loaded
    this.showToast(`Loaded ${totalFeatures} feature${totalFeatures !== 1 ? 's' : ''} from ${fileList.length} file${fileList.length !== 1 ? 's' : ''}`);

    // Reset file input value so re-selecting the same file fires change event cleanly
    const input = document.getElementById('fileInput');
    if (input) input.value = '';
  }

  showToast(message) {
    let toast = document.getElementById('surgeToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'surgeToast';
      toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);background:rgba(16,185,129,0.95);color:#fff;padding:10px 20px;border-radius:8px;font-size:0.85rem;font-weight:600;z-index:9999;opacity:0;transition:all 0.3s ease;pointer-events:none;box-shadow:0 4px 20px rgba(16,185,129,0.4);';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(-50%) translateY(20px)';
    }, 3000);
  }

  async runOptimization() {
    if (!this.currentProjectId) return alert('Please select a project first.');

    const jobBox = document.getElementById('jobStatusBox');
    const progressBar = document.getElementById('jobProgressBar');
    const statusMsg = document.getElementById('jobStatusMessage');

    jobBox.classList.remove('hidden');
    progressBar.style.backgroundColor = '';
    progressBar.style.width = '10%';
    statusMsg.textContent = 'Initializing optimization job request...';

    const params = {
      scenario: document.getElementById('optimScenario').value,
      feederCapacityMw: parseFloat(document.getElementById('feederCapacity').value),
      maxSpanMeters: parseFloat(document.getElementById('maxSpan').value),
      voltageKv: parseFloat(document.getElementById('voltageKv').value)
    };

    try {
      const job = await api.runOptimization(this.currentProjectId, params);
      this.currentJobId = job.id;

      // Subscribe to real-time SSE progress stream
      if (job.id && !job.id.startsWith('job-demo')) {
        api.listenJobProgress(
          this.currentProjectId,
          job.id,
          (progressData) => {
            if (progressData.progressPercent !== undefined) {
              progressBar.style.width = `${progressData.progressPercent}%`;
            }
            if (progressData.message) {
              statusMsg.textContent = progressData.message;
            }
          },
          (err) => {
            console.warn('[SSE Progress Stream Error]', err);
          },
          async () => {
            progressBar.style.width = '100%';
            statusMsg.textContent = 'Optimization completed cleanly!';
            await this.refreshProjectData();
            setTimeout(() => jobBox.classList.add('hidden'), 2500);
          }
        );
      } else {
        // Fallback progress for demo job execution
        progressBar.style.width = '70%';
        statusMsg.textContent = 'Calculating A* cost surface & feeder topology...';

        setTimeout(async () => {
          progressBar.style.width = '100%';
          statusMsg.textContent = 'Optimization completed cleanly!';

          await this.refreshProjectData();

          setTimeout(() => jobBox.classList.add('hidden'), 2000);
        }, 1200);
      }

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

  async loadScenarioComparison() {
    const container = document.getElementById('scenarioGridContainer');
    container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading Scenario Analytics...</div>';

    try {
      const data = await api.getScenarioComparison(this.currentProjectId);
      const scenarios = data.scenarios || [];

      if (scenarios.length === 0) {
        container.innerHTML = '<div class="text-muted">No scenario comparison data available.</div>';
        return;
      }

      const badgeColors = {
        'Minimum Cost': 'badge-green',
        'Minimum Land Impact': 'badge-purple',
        'Minimum Environmental Impact': 'badge-yellow',
        'Balanced': 'badge-blue'
      };

      const scenarioMapColors = {
        'Minimum Cost': '#10B981',
        'Minimum Land Impact': '#8B5CF6',
        'Minimum Environmental Impact': '#06B6D4',
        'Balanced': '#F59E0B'
      };

      container.innerHTML = '';
      scenarios.forEach(sc => {
        const card = document.createElement('div');
        card.className = 'scenario-card';

        const badgeClass = badgeColors[sc.scenarioName] || 'badge-blue';
        const capexTag = sc.capexDeltaPct < 0 ? `<span class="delta-tag delta-good">${sc.capexDeltaPct}%</span>` : (sc.capexDeltaPct > 0 ? `<span class="delta-tag delta-warn">+${sc.capexDeltaPct}%</span>` : '');
        const lossTag = sc.lossesDeltaPct < 0 ? `<span class="delta-tag delta-good">${sc.lossesDeltaPct}%</span>` : (sc.lossesDeltaPct > 0 ? `<span class="delta-tag delta-warn">+${sc.lossesDeltaPct}%</span>` : '');

        card.innerHTML = `
          <div class="scenario-card-header">
            <span>${sc.scenarioName}</span>
            <span class="scenario-badge ${badgeClass}">${sc.scenarioName.split(' ')[0]}</span>
          </div>
          <div class="scenario-metric-item">
            <span class="metric-label"><i class="fa-solid fa-dollar-sign"></i> CAPEX:</span>
            <span class="metric-value">$${(sc.totalEstimatedCost || 0).toLocaleString()} ${capexTag}</span>
          </div>
          <div class="scenario-metric-item">
            <span class="metric-label"><i class="fa-solid fa-bolt"></i> Losses:</span>
            <span class="metric-value">${(sc.totalElectricalLossesKw || 0).toFixed(1)} kW ${lossTag}</span>
          </div>
          <div class="scenario-metric-item">
            <span class="metric-label"><i class="fa-solid fa-vector-square"></i> ROW Cost:</span>
            <span class="metric-value">$${(sc.landRowCompensationCost || 0).toLocaleString()}</span>
          </div>
          <div class="scenario-metric-item">
            <span class="metric-label"><i class="fa-solid fa-route"></i> Length / Poles:</span>
            <span class="metric-value">${(sc.totalNetworkLengthMeters / 1000).toFixed(2)} km / ${sc.totalPoles}</span>
          </div>
          <button class="btn btn-secondary btn-sm mt-3 btn-block btn-apply-scenario" data-scenario="${sc.scenarioName}">
            <i class="fa-solid fa-eye"></i> Overlay Map Route
          </button>
        `;

        card.querySelector('.btn-apply-scenario').addEventListener('click', async (e) => {
          const scName = e.currentTarget.getAttribute('data-scenario');
          const color = scenarioMapColors[scName] || '#10B981';
          const routesGeoJson = await api.getRoutesGeoJson(this.currentProjectId);
          this.mapEngine.renderRoutes(routesGeoJson, color);
          document.getElementById('modalCompareScenarios').classList.add('hidden');
        });

        container.appendChild(card);
      });
    } catch (err) {
      container.innerHTML = `<div class="text-red">Failed to load scenario comparison: ${err.message}</div>`;
    }
  }

  async loadAuditLogs() {
    const list = document.getElementById('auditLogList');
    if (!list) return;

    try {
      const logs = await api.getAuditLogs();
      if (!logs || logs.length === 0) {
        list.innerHTML = '<div class="text-muted">No audit logs recorded yet.</div>';
        return;
      }

      list.innerHTML = '';
      logs.forEach(log => {
        const item = document.createElement('div');
        item.className = 'audit-item';
        const dateStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '';
        item.innerHTML = `
          <div class="audit-item-header">
            <span class="audit-user"><i class="fa-solid fa-user-gear"></i> ${log.username || 'anonymous'}</span>
            <span class="audit-action">${log.action}</span>
          </div>
          <div class="audit-details">${log.details || log.resourceType}</div>
          <div class="audit-time">${dateStr}</div>
        `;
        list.appendChild(item);
      });
    } catch (err) {
      list.innerHTML = `<div class="text-red">Failed to load audit logs: ${err.message}</div>`;
    }
  }
}

// Instantiate App when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.surgeApp = new SurgeApp();
});
