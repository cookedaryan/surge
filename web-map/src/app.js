/* ==========================================================================
   SURGE GIS Web Application — Main Application Orchestration
   ========================================================================== */

import { api } from './api.js';
import { SurgeMapEngine } from './map.js';
import { classifyGeoJsonFeature, ASSET_TYPES, ASSET_TYPE_LABELS, LINE_TYPES, LINE_TYPE_LABELS } from './classify.js';

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

    // PDF Export Actions (Header & BOM Tab)
    ['btnDownloadPdf', 'btnDownloadPdfHeader'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener('click', () => {
          if (!this.currentProjectId) return alert('Please select a project first.');
          window.open(api.getPdfReportUrl(this.currentProjectId), '_blank');
        });
      }
    });

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
      { id: 'chkShowTowers', layer: 'towers' },
      { id: 'chkShowReferenceLines', layer: 'referenceLines' },
      { id: 'chkShowRoutes', layer: 'routes' },
      { id: 'chkShowParcels', layer: 'parcels' },
      { id: 'chkShowRestricted', layer: 'restricted' }
    ];
    layerChecks.forEach(item => {
      const checkbox = document.getElementById(item.id);
      if (!checkbox) return;
      checkbox.addEventListener('change', (e) => {
        this.mapEngine.setLayerVisibility(item.layer, e.target.checked);
      });
    });

    // Import Preview Modal
    const btnImportConfirm = document.getElementById('btnImportConfirm');
    if (btnImportConfirm) {
      btnImportConfirm.addEventListener('click', () => this.commitImportPreview());
    }
    ['btnImportCancel', 'btnCloseImportPreview'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener('click', () => this.closeImportPreview());
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
      
      const byType = (type) => (assetsGeoJson.features || [])
        .filter(f => (f.properties?.assetType || '').toUpperCase() === type);

      const wtgsList = byType('WTG');
      const subList = byType('SUBSTATION');
      const towerList = byType('EVACUATION_TOWER');
      const lineList = byType('REFERENCE_LINE');

      // Only turbines with an optimisable status are counted towards the network total; the rest
      // are rendered dimmed so the difference between "on the map" and "in the model" is visible.
      const optimisableCount = wtgsList.filter(f => f.properties?.optimisable !== false).length;

      const countWtgs = document.getElementById('countWtgs');
      countWtgs.textContent = optimisableCount === wtgsList.length
        ? wtgsList.length
        : `${optimisableCount} / ${wtgsList.length}`;
      countWtgs.title = optimisableCount === wtgsList.length
        ? ''
        : `${wtgsList.length - optimisableCount} turbine location(s) excluded by status`;

      document.getElementById('countSubstations').textContent = subList.length;
      const countTowers = document.getElementById('countTowers');
      if (countTowers) countTowers.textContent = towerList.length;

      this.mapEngine.renderWtgs({ type: 'FeatureCollection', features: wtgsList });
      this.mapEngine.renderSubstations({ type: 'FeatureCollection', features: subList });
      this.mapEngine.renderTowers({ type: 'FeatureCollection', features: towerList });
      this.mapEngine.renderReferenceLines({ type: 'FeatureCollection', features: lineList });

      const countLines = document.getElementById('countLines');
      if (countLines) countLines.textContent = lineList.length;

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

  // ==========================================================================
  // KMZ / KML import preview
  //
  // Survey exports mix turbines, evacuation towers, substations and geotechnical markers in one
  // file, with folder naming that varies between surveyors. The preview shows what each placemark
  // was detected as and why, and lets the user correct it before anything is written to the
  // database.
  // ==========================================================================

  openImportPreview(preview) {
    this.currentImport = preview;
    this.importOverrides = {};

    const modal = document.getElementById('modalImportPreview');
    if (!modal) {
      // No preview UI available (e.g. embedded usage) — fall back to committing as detected.
      this.commitImportPreview();
      return;
    }

    const counts = preview.countsByType || {};
    const unknownCount = counts.UNKNOWN || 0;

    document.getElementById('importPreviewFileName').textContent = preview.fileName || 'Uploaded file';

    const summary = document.getElementById('importPreviewSummary');
    summary.innerHTML = Object.entries(counts)
      .filter(([, count]) => count > 0)
      .map(([type, count]) => `
        <div class="import-chip import-chip-${type.toLowerCase()}">
          <strong>${count}</strong> ${ASSET_TYPE_LABELS[type] || type}
        </div>`)
      .join('');

    const notes = [];
    if (preview.duplicatesRemoved > 0) {
      notes.push(`${preview.duplicatesRemoved} duplicate placemark(s) removed — this file repeats its own folder tree.`);
    }
    const skipped = preview.skippedByGeometry || {};
    const skippedTotal = Object.values(skipped).reduce((sum, n) => sum + n, 0);
    if (skippedTotal > 0) {
      const detail = Object.entries(skipped).map(([type, n]) => `${n} ${type}`).join(', ');
      notes.push(`${skippedTotal} non-point feature(s) not imported as assets (${detail}).`);
    }
    if (unknownCount > 0) {
      notes.push(`${unknownCount} feature(s) could not be classified and will be skipped unless you assign a type.`);
    }
    document.getElementById('importPreviewNotes').innerHTML =
      notes.map(note => `<div class="import-note">${note}</div>`).join('');

    const GEOMETRY_GLYPH = { Point: '●', LineString: '╱', Polygon: '▭' };

    const rows = (preview.features || []).map(feature => {
      const isLine = feature.geometryType === 'LineString';
      // Lines pick from the line-type vocabulary, everything else from the asset-type vocabulary.
      const options = isLine
        ? Object.keys(LINE_TYPES).map(type => `
            <option value="${type}" ${type === feature.lineType ? 'selected' : ''}>
              ${LINE_TYPE_LABELS[type]}
            </option>`).join('')
        : Object.keys(ASSET_TYPES).map(type => `
            <option value="${type}" ${type === feature.classifiedAs ? 'selected' : ''}>
              ${ASSET_TYPE_LABELS[type]}
            </option>`).join('');

      const unresolved = feature.classifiedAs === 'UNKNOWN'
        || (isLine && feature.lineType === 'UNKNOWN');

      return `
      <tr data-external-id="${this.escapeHtml(feature.externalId)}"
          class="${unresolved ? 'import-row-unknown' : ''}">
        <td class="import-geom" title="${feature.geometryType}">${GEOMETRY_GLYPH[feature.geometryType] || '?'}</td>
        <td>${this.escapeHtml(feature.externalId) || '<em>unnamed</em>'}
          ${feature.vertexCount > 1 ? `<span class="import-verts">${feature.vertexCount} pts</span>` : ''}</td>
        <td class="import-folder">${this.escapeHtml(feature.kmlFolder || '—')}</td>
        <td>
          <select class="import-type-select" data-external-id="${this.escapeHtml(feature.externalId)}">
            ${options}
          </select>
        </td>
        <td class="import-status">${feature.status && feature.status !== 'UNKNOWN' ? feature.status.replace(/_/g, ' ') : '—'}</td>
        <td class="import-rule" title="${this.escapeHtml(feature.evidence || '')}">
          ${feature.matchedRule.replace(/_/g, ' ').toLowerCase()}
        </td>
      </tr>`;
    }).join('');

    document.getElementById('importPreviewRows').innerHTML = rows;

    modal.querySelectorAll('.import-type-select').forEach(select => {
      select.addEventListener('change', (e) => {
        this.importOverrides[e.target.dataset.externalId] = e.target.value;
      });
    });

    // "Apply to all in this folder" — the fastest way to correct a whole mis-detected folder.
    const applyFolder = document.getElementById('btnImportApplyFolder');
    if (applyFolder) {
      applyFolder.onclick = () => this.applyTypeToVisibleRows();
    }

    modal.classList.remove('hidden');
  }

  applyTypeToVisibleRows() {
    const bulkType = document.getElementById('importBulkType').value;
    if (!bulkType) return;
    document.querySelectorAll('#importPreviewRows tr').forEach(row => {
      const select = row.querySelector('.import-type-select');
      if (select) {
        select.value = bulkType;
        this.importOverrides[select.dataset.externalId] = bulkType;
      }
    });
  }

  closeImportPreview() {
    const modal = document.getElementById('modalImportPreview');
    if (modal) modal.classList.add('hidden');
    this.currentImport = null;
    this.importOverrides = {};
  }

  async commitImportPreview() {
    if (!this.currentImport) return;

    const capacityInput = document.getElementById('importDefaultCapacity');
    const defaultCapacityMw = capacityInput && capacityInput.value
      ? parseFloat(capacityInput.value)
      : null;

    try {
      const result = await api.commitAssetImport(this.currentProjectId, {
        importId: this.currentImport.importId,
        overrides: this.importOverrides || {},
        defaultCapacityMw,
        skipUnclassified: true
      });

      const parts = [];
      if (result.wtgsImported) parts.push(`${result.wtgsImported} turbines`);
      if (result.substationsImported) parts.push(`${result.substationsImported} substations`);
      if (result.towersImported) parts.push(`${result.towersImported} towers`);
      if (result.unclassified) parts.push(`${result.unclassified} skipped`);

      this.showToast(`Imported ${parts.join(', ') || 'nothing'}`);
      this.closeImportPreview();
      await this.refreshProjectData();
    } catch (err) {
      console.error('[Import Commit]', err);
      this.showToast(`Import failed: ${err.message || err}`);
    }
  }

  escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
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

    const kmzFiles = fileList.filter(f => f.name.toLowerCase().endsWith('.kmz') || f.name.toLowerCase().endsWith('.kml'));
    const geoJsonFiles = fileList.filter(f => !f.name.toLowerCase().endsWith('.kmz') && !f.name.toLowerCase().endsWith('.kml'));

    for (const file of kmzFiles) {
      console.log(`[SURGE] Processing KMZ/KML file: ${file.name} (${file.size} bytes)`);
      try {
        // Classify first, persist only after the user confirms. A survey KMZ mixes turbines,
        // towers, substations and geotechnical markers, and its folder naming varies by surveyor.
        const preview = await api.previewKmzAssets(this.currentProjectId, file);
        this.openImportPreview(preview);
      } catch (err) {
        console.warn(`[KMZ Import Warning] ${file.name}:`, err);
        this.showToast(`Import error: ${err.message || err}`);
      }
    }

    if (geoJsonFiles.length === 0) {
      const input = document.getElementById('fileInput');
      if (input) input.value = '';
      return;
    }

    // Clear the imported layer once before processing all files
    this.mapEngine.clearImported();

    let allWtgs = [];
    let allSubstations = [];
    let allTowers = [];
    let unclassified = [];
    let allParcels = [];
    let allRestricted = [];
    let allRoutes = [];
    let totalFeatures = 0;

    const selectedType = document.querySelector('input[name="assetImportType"]:checked')?.value || 'auto';

    for (const file of geoJsonFiles) {
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
            } else {
              // Auto-detect uses the shared rule chain, the same one the backend applies. It used
              // to end in "else -> WTG", which classified every unrecognised point as a turbine.
              const detected = classifyGeoJsonFeature(feat).assetType;
              feat.properties.assetType = detected;
              if (detected === ASSET_TYPES.SUBSTATION) {
                allSubstations.push(feat);
              } else if (detected === ASSET_TYPES.EVACUATION_TOWER) {
                allTowers.push(feat);
              } else if (detected === ASSET_TYPES.WTG) {
                allWtgs.push(feat);
              } else {
                unclassified.push(feat);
              }
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
            unclassified.push(feat);
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
    if (allTowers.length > 0) {
      this.mapEngine.renderTowers({ type: 'FeatureCollection', features: allTowers });
      const countTowers = document.getElementById('countTowers');
      if (countTowers) countTowers.textContent = allTowers.length;
    }
    if (unclassified.length > 0) {
      const sample = unclassified.slice(0, 3)
        .map(f => f.properties?.externalId || f.properties?.name || '?').join(', ');
      this.showToast(
        `${unclassified.length} feature(s) could not be classified (${sample}${unclassified.length > 3 ? ', …' : ''}). ` +
        `Pick an asset type above and re-import, or upload as KMZ to use the preview.`
      );
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
