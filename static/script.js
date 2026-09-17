const AppState = {
  user: null,
  activeTab: 'dashboardTab',
  activeScan: null,
  allRules: null,
  activeRuleKey: null,
  charts: { violations: null, categories: null }
};

document.addEventListener('DOMContentLoaded', () => {
  initLiveClock();
  initAuthentication();
  initNavigation();
  initDragAndDrop();
  initScanAuditor();
  initRepository();
  initRulesConfigurator();
  initDocsNav();
});

function initLiveClock() {
  const clockEl = document.getElementById('liveClock');
  const updateClock = () => {
    const now = new Date();
    const options = { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
    clockEl.innerHTML = `<i class="fa-regular fa-clock"></i> ${now.toLocaleString('en-IN', options).toUpperCase()}`;
  };
  updateClock();
  setInterval(updateClock, 1000);
}

function initAuthentication() {
  const loginPortal = document.getElementById('loginPortal');
  const appContainer = document.getElementById('appContainer');
  const loginForm = document.getElementById('loginForm');
  const logoutBtn = document.getElementById('logoutBtn');
  const roleChips = document.querySelectorAll('.role-chip');
  let selectedRole = 'official';
  roleChips.forEach(chip => {
    chip.addEventListener('click', () => {
      roleChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedRole = chip.dataset.role;
    });
  });
  loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    AppState.user = { username, role: selectedRole };
    document.querySelector('.user-name').textContent = username === 'doca_official' ? 'Inspector Dev Sharma' : username;
    document.querySelector('.user-role').textContent = selectedRole === 'official' ? 'Enforcement Official' : 'Packer / QA Manager';
    loginPortal.classList.add('hidden');
    appContainer.classList.remove('hidden');
    loadDashboardStats();
    loadRules();
  });
  logoutBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to sign out?')) {
      AppState.user = null;
      appContainer.classList.add('hidden');
      loginPortal.classList.remove('hidden');
    }
  });
}

function initNavigation() {
  const menuItems = document.querySelectorAll('.sidebar-menu .menu-item');
  const panels = document.querySelectorAll('.viewport-panel');
  const quickScanBtn = document.getElementById('quickScanBtn');
  const switchTab = (targetId) => {
    menuItems.forEach(item => { item.classList.toggle('active', item.dataset.target === targetId); });
    panels.forEach(panel => { panel.classList.toggle('hidden', panel.id !== targetId); });
    AppState.activeTab = targetId;
    const tabHeaders = {
      'dashboardTab': { title: 'Executive Dashboard', subtitle: 'Summary and compliance breakdown statistics.' },
      'scannerTab': { title: 'Scanner & Auditor Workspace', subtitle: 'Upload packaging image labels and verify compliance.' },
      'repositoryTab': { title: 'Inspection Repository', subtitle: 'Search and download past digital reports.' },
      'rulesTab': { title: 'Compliance Rules Configurator', subtitle: 'Configure Legal Metrology checking conditions.' },
      'docsTab': { title: 'System Architecture & Documentation', subtitle: 'Technical documentation and standards references.' }
    };
    const header = tabHeaders[targetId];
    if (header) {
      document.getElementById('currentTabTitle').textContent = header.title;
      document.getElementById('currentTabSubtitle').textContent = header.subtitle;
    }
    if (targetId === 'dashboardTab') loadDashboardStats();
    else if (targetId === 'repositoryTab') loadRepositoryHistory();
    else if (targetId === 'rulesTab') loadRules();
  };
  menuItems.forEach(item => { item.addEventListener('click', (e) => { e.preventDefault(); switchTab(item.dataset.target); }); });
  quickScanBtn.addEventListener('click', () => { switchTab('scannerTab'); });
  window.switchTab = switchTab;
}

function initDragAndDrop() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const browseBtn = document.getElementById('browseBtn');
  const imagePreview = document.getElementById('imagePreview');
  const uploadPlaceholder = document.getElementById('uploadPlaceholder');
  const previewContainer = document.getElementById('previewContainer');
  const analyzeBtn = document.getElementById('analyzeBtn');
  browseBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); });
  ['dragenter', 'dragover'].forEach(ev => { dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add('dragging'); }, false); });
  ['dragleave', 'drop'].forEach(ev => { dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove('dragging'); }, false); });
  dropzone.addEventListener('drop', (e) => { handleFiles(e.dataTransfer.files); });
  function handleFiles(files) {
    if (files.length === 0) return;
    const file = files[0];
    if (!file.type.startsWith('image/')) { alert('Invalid file format. Please upload an image.'); return; }
    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.src = e.target.result;
      uploadPlaceholder.classList.add('hidden');
      previewContainer.classList.remove('hidden');
      analyzeBtn.disabled = false;
      document.getElementById('boundingBoxes').innerHTML = '';
      document.getElementById('auditReportSection').classList.add('hidden');
      document.getElementById('ocrTextEditor').value = '';
      document.getElementById('ocrTextEditor').disabled = true;
      document.getElementById('recheckBtn').disabled = true;
      document.getElementById('ocrStatusBadge').style.display = 'none';
      const container = new DataTransfer();
      container.items.add(file);
      fileInput.files = container.files;
    };
    reader.readAsDataURL(file);
  }
}

function initScanAuditor() {
  const analyzeBtn = document.getElementById('analyzeBtn');
  const recheckBtn = document.getElementById('recheckBtn');
  const laserLine = document.getElementById('laserLine');
  const fileInput = document.getElementById('fileInput');
  const ocrTextEditor = document.getElementById('ocrTextEditor');
  const fontPhysicalHeight = document.getElementById('fontPhysicalHeight');
  document.querySelectorAll('.btn-sample').forEach(btn => { btn.addEventListener('click', () => { loadDemoSample(btn.dataset.sample); }); });

  analyzeBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    laserLine.style.display = 'block';
    analyzeBtn.disabled = true;
    const formData = new FormData();
    formData.append('image', file);
    try {
      const response = await fetch('/upload', { method: 'POST', body: formData });
      if (!response.ok) { const errJson = await response.json().catch(() => ({})); throw new Error(errJson.error || 'OCR Server Error'); }
      const data = await response.json();
      AppState.activeScan = data;
      laserLine.style.display = 'none';
      analyzeBtn.disabled = false;
      displayAuditReport(data);
      drawBoundingBoxes(data);
    } catch (error) {
      laserLine.style.display = 'none';
      analyzeBtn.disabled = false;
      console.error(error);
      alert('Analysis status: ' + error.message);
    }
  });

  recheckBtn.addEventListener('click', async () => {
    if (!AppState.activeScan) return;
    let editedText = ocrTextEditor.value;
    const fontHeightVal = parseFloat(fontPhysicalHeight.value) || 2.0;
    editedText = editedText.replace(/Font Size Parameter:\s*[0-9\.]+\s*mm/gi, '');
    editedText += `\nFont Size Parameter: ${fontHeightVal} mm`;
    try {
      const response = await fetch('/api/check_text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scan_id: AppState.activeScan.id, text: editedText, product_name: AppState.activeScan.product_name }) });
      if (!response.ok) throw new Error('Recheck failed');
      const updatedData = await response.json();
      AppState.activeScan = updatedData;
      displayAuditReport(updatedData);
      alert('Compliance checked updated successfully.');
    } catch (error) { console.error(error); alert('Error updating compliance details.'); }
  });

  document.getElementById('downloadPdfBtn').addEventListener('click', () => { if (!AppState.activeScan) return; window.location.href = `/api/download_pdf/${AppState.activeScan.id}`; });
  document.getElementById('saveInspectionBtn').addEventListener('click', () => { alert('Inspection successfully recorded in repository.'); window.switchTab('repositoryTab'); });
}

async function loadDemoSample(sampleKey) {
  const uploadPlaceholder = document.getElementById('uploadPlaceholder');
  const previewContainer = document.getElementById('previewContainer');
  const imagePreview = document.getElementById('imagePreview');
  const fileInput = document.getElementById('fileInput');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const sampleLabelName = `${sampleKey}.jpg`;
  const canvas = document.createElement('canvas');
  canvas.width = 400; canvas.height = 300;
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 400, 300);
  gradient.addColorStop(0, '#1e293b'); gradient.addColorStop(1, '#0f172a');
  ctx.fillStyle = gradient; ctx.fillRect(0, 0, 400, 300);
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 20px Outfit, sans-serif';
  ctx.fillText(sampleKey.replace('_', ' ').toUpperCase(), 30, 60);
  ctx.fillStyle = '#94a3b8'; ctx.font = '13px Inter, sans-serif';
  ctx.fillText('Packaging Metrology Assessment Label', 30, 90);
  ctx.strokeStyle = 'rgba(79, 70, 229, 0.4)'; ctx.lineWidth = 2; ctx.strokeRect(20, 20, 360, 260);
  imagePreview.src = canvas.toDataURL('image/jpeg');
  uploadPlaceholder.classList.add('hidden'); previewContainer.classList.remove('hidden');
  document.getElementById('boundingBoxes').innerHTML = '';
  document.getElementById('auditReportSection').classList.add('hidden');
  document.getElementById('ocrTextEditor').value = '';
  document.getElementById('ocrTextEditor').disabled = true;
  document.getElementById('recheckBtn').disabled = true;
  document.getElementById('ocrStatusBadge').style.display = '';
  canvas.toBlob(blob => {
    const file = new File([blob], sampleLabelName, { type: 'image/jpeg' });
    const container = new DataTransfer();
    container.items.add(file); fileInput.files = container.files;
    analyzeBtn.disabled = false; analyzeBtn.click();
  }, 'image/jpeg');
}

function drawBoundingBoxes(data) {
  const container = document.getElementById('boundingBoxes');
  container.innerHTML = '';
  if (!data || !data.boxes) return;
  const img = document.getElementById('imagePreview');
  const originalWidth = data.image_width || img.naturalWidth || 1;
  const originalHeight = data.image_height || img.naturalHeight || 1;
  const setupBoxes = () => {
    container.innerHTML = '';
    container.style.position = 'absolute';
    container.style.left = `${img.offsetLeft}px`; container.style.top = `${img.offsetTop}px`;
    container.style.width = `${img.offsetWidth}px`; container.style.height = `${img.offsetHeight}px`;
    container.style.pointerEvents = 'none';
    const scaleX = img.offsetWidth / originalWidth;
    const scaleY = img.offsetHeight / originalHeight;
    const typeMapping = { "MRP": "MRP", "NetQuantity": "Net Quantity", "MfgDate": "Mfg Date", "Manufacturer": "Manufacturer", "ConsumerCare": "Consumer Cell", "mrp": "MRP", "net_quantity": "Net Quantity", "mfg_date": "Mfg Date", "manufacturer": "Manufacturer", "consumer_care": "Consumer Cell", "font_size": "Font Size" };
    for (const [key, box] of Object.entries(data.boxes)) {
      if (!box) continue;
      const lookupKey = key.toLowerCase();
      let status = 'Failed';
      for (const [rKey, rVal] of Object.entries(data.results || {})) {
        if (rKey.toLowerCase().replace(/_/g, '') === lookupKey.replace(/_/g, '')) { status = rVal.status; break; }
      }
      const label = typeMapping[key] || key;
      const boxEl = document.createElement('div');
      boxEl.style.position = 'absolute';
      boxEl.style.left = `${box.x * scaleX}px`; boxEl.style.top = `${box.y * scaleY}px`;
      boxEl.style.width = `${box.width * scaleX}px`; boxEl.style.height = `${box.height * scaleY}px`;
      let color = 'rgba(239, 68, 68, 0.7)';
      const su = status.toUpperCase();
      if (su === 'PASS' || su === 'PASSED') color = 'rgba(16, 185, 129, 0.7)';
      else if (su === 'WARNING') color = 'rgba(245, 158, 11, 0.7)';
      boxEl.style.border = `2.5px solid ${color}`; boxEl.style.backgroundColor = 'rgba(79, 70, 229, 0.05)';
      boxEl.style.borderRadius = '4px'; boxEl.style.pointerEvents = 'none';
      const badge = document.createElement('span');
      badge.textContent = label; badge.style.position = 'absolute'; badge.style.top = '-16px'; badge.style.left = '4px';
      badge.style.fontSize = '8px'; badge.style.fontWeight = '700'; badge.style.backgroundColor = color;
      badge.style.color = '#ffffff'; badge.style.padding = '1px 4px'; badge.style.borderRadius = '2px';
      badge.style.textTransform = 'uppercase'; badge.style.whiteSpace = 'nowrap';
      boxEl.appendChild(badge); container.appendChild(boxEl);
    }
  };
  if (window.activeResizeObserver) window.activeResizeObserver.disconnect();
  const observer = new ResizeObserver(() => { setupBoxes(); });
  observer.observe(img); window.activeResizeObserver = observer;
  img.onload = setupBoxes; setupBoxes();
}

function displayAuditReport(data) {
  const section = document.getElementById('auditReportSection');
  const overallBadge = document.getElementById('overallStatusBadge');
  const summaryLead = document.getElementById('reportSummaryLead');
  const scoreText = document.getElementById('scoreCircleText');
  const scoreCircle = document.getElementById('scoreCircleProgress');
  const ocrTextEditor = document.getElementById('ocrTextEditor');
  const recheckBtn = document.getElementById('recheckBtn');
  const fontPhysicalHeight = document.getElementById('fontPhysicalHeight');
  const checklistAccordion = document.getElementById('checklistAccordion');
  section.classList.remove('hidden');
  ocrTextEditor.value = data.extracted_text; ocrTextEditor.disabled = false; recheckBtn.disabled = false;
  const fontMatch = data.extracted_text.match(/Font Size Parameter:\s*([0-9\.]+)\s*mm/i);
  if (fontMatch) fontPhysicalHeight.value = fontMatch[1];
  const score = data.compliance_score;
  scoreText.textContent = `${score}%`;
  scoreCircle.style.strokeDasharray = `${score}, 100`;
  const overallNormalized = data.overall_status.toUpperCase();
  let overallClass = 'failed';
  if (overallNormalized === 'PASSED' || overallNormalized === 'PASS') overallClass = 'passed';
  else if (overallNormalized === 'PARTIAL' || overallNormalized === 'WARNING') overallClass = 'warning';
  overallBadge.className = `status-pill large ${overallClass}`;
  overallBadge.textContent = data.overall_status;
  const failed_count = data.failed_count !== undefined ? data.failed_count : Object.values(data.results || {}).filter(r => r.status.toUpperCase() === 'FAIL' || r.status.toUpperCase() === 'FAILED').length;
  const warning_count = data.warning_count !== undefined ? data.warning_count : Object.values(data.results || {}).filter(r => r.status.toUpperCase() === 'WARNING').length;
  if (overallNormalized === 'PASSED' || overallNormalized === 'PASS') {
    summaryLead.innerHTML = '<span class="text-success"><i class="fa-solid fa-circle-check"></i> Package is fully Compliant.</span> No regulatory warnings or violations detected under Legal Metrology Rules, 2011.';
  } else if (overallNormalized === 'PARTIAL' || overallNormalized === 'WARNING') {
    summaryLead.innerHTML = `<span class="text-warning"><i class="fa-solid fa-circle-exclamation"></i> Warnings Detected (${warning_count}).</span> Standard declarations are present but format anomalies exist. Review corrective remarks.`;
  } else {
    summaryLead.innerHTML = `<span class="text-danger"><i class="fa-solid fa-circle-xmark"></i> Violations Found (${failed_count}).</span> Package does not comply with the standards. Prosecutable declarations are missing or incorrect.`;
  }
  checklistAccordion.innerHTML = '';
  for (const [key, res] of Object.entries(data.results)) {
    const item = document.createElement('div'); item.className = 'checklist-item';
    const rsn = res.status.toUpperCase();
    let statusClass = 'failed', iconClass = 'fa-solid fa-circle-xmark failed';
    if (rsn === 'PASS' || rsn === 'PASSED') { statusClass = 'passed'; iconClass = 'fa-solid fa-circle-check passed'; }
    else if (rsn === 'WARNING') { statusClass = 'warning'; iconClass = 'fa-solid fa-circle-exclamation warning'; }
    const header = document.createElement('div'); header.className = 'checklist-header';
    header.innerHTML = `<div class="checklist-title-area"><i class="${iconClass} checklist-icon"></i><span class="checklist-title">${res.friendly_name}</span></div><div class="checklist-meta"><span class="status-pill ${statusClass}">${res.status}</span><i class="fa-solid fa-chevron-down checklist-arrow"></i></div>`;
    const content = document.createElement('div'); content.className = 'checklist-content';
    content.innerHTML = `<div class="checklist-detail-grid"><div class="detail-block"><h5>Detected Value Snippet</h5><p>${res.detected_value ? `<code>${res.detected_value}</code>` : '<i>None found</i>'}</p></div><div class="detail-block"><h5>Severity Assessment</h5><p>${res.severity === 'High' ? '<span class="text-danger">High Violative</span>' : (res.severity === 'Medium' ? '<span class="text-warning">Medium warning</span>' : 'None')}</p></div></div><div class="detail-block margin-top-small"><h5>Audit Assessment Remarks</h5><p>${res.message}</p></div>${res.clause ? `<div class="detail-block margin-top-small"><h5>Regulatory Law Reference</h5><p class="text-secondary">${res.clause}</p></div>` : ''}`;
    header.addEventListener('click', () => { const isExpanded = item.classList.contains('expanded'); document.querySelectorAll('.checklist-item').forEach(el => el.classList.remove('expanded')); if (!isExpanded) item.classList.add('expanded'); });
    item.appendChild(header); item.appendChild(content); checklistAccordion.appendChild(item);
  }
}

function initRepository() {
  document.getElementById('repoSearchInput').addEventListener('input', filterRepositoryTable);
  document.getElementById('repoStatusFilter').addEventListener('change', filterRepositoryTable);
}

async function loadRepositoryHistory() {
  const tbody = document.getElementById('repoTableBody');
  tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary py-4"><i class="fa-solid fa-circle-notch fa-spin"></i> Retrieving scanned history logs...</td></tr>';
  try {
    const response = await fetch('/api/history');
    if (!response.ok) throw new Error('History load failed');
    const scans = await response.json();
    window.scansHistoryData = scans;
    renderRepositoryTable(scans);
  } catch (error) { console.error(error); tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-4">Error loading repository database.</td></tr>'; }
}

function renderRepositoryTable(scans) {
  const tbody = document.getElementById('repoTableBody'); tbody.innerHTML = '';
  if (scans.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary py-4">No inspection histories recorded yet.</td></tr>'; return; }
  scans.forEach(scan => {
    const row = document.createElement('tr');
    let badgeClass = 'passed';
    if (scan.overall_status === 'Warning') badgeClass = 'warning';
    else if (scan.overall_status === 'Failed') badgeClass = 'failed';
    const dateStr = scan.timestamp ? scan.timestamp.slice(0,19).replace('T', ' ') : 'N/A';
    row.innerHTML = `<td><code>#${scan.id}</code></td><td><strong>${scan.product_name}</strong></td><td>${dateStr}</td><td><strong>${scan.compliance_score}%</strong></td><td><span class="status-pill ${badgeClass}">${scan.overall_status}</span></td><td class="text-right"><button class="btn-text btn-view" title="View"><i class="fa-solid fa-eye"></i></button><button class="btn-text btn-pdf" title="PDF"><i class="fa-solid fa-file-pdf"></i></button><button class="btn-text btn-delete text-danger" title="Delete"><i class="fa-solid fa-trash-can"></i></button></td>`;
    row.querySelector('.btn-view').addEventListener('click', () => {
      AppState.activeScan = scan; window.switchTab('scannerTab');
      document.getElementById('uploadPlaceholder').classList.add('hidden');
      document.getElementById('previewContainer').classList.remove('hidden');
      document.getElementById('imagePreview').src = scan.filename ? `/uploads/${scan.filename}` : '';
      displayAuditReport(scan); drawBoundingBoxes(scan);
    });
    row.querySelector('.btn-pdf').addEventListener('click', () => { window.location.href = `/api/download_pdf/${scan.id}`; });
    row.querySelector('.btn-delete').addEventListener('click', async () => {
      if (confirm(`Delete scan #${scan.id}?`)) { try { const res = await fetch(`/api/history/${scan.id}`, { method: 'DELETE' }); if (res.ok) { alert('Deleted.'); loadRepositoryHistory(); } } catch (err) { console.error(err); } }
    });
    tbody.appendChild(row);
  });
}

function filterRepositoryTable() {
  const query = document.getElementById('repoSearchInput').value.toLowerCase();
  const filter = document.getElementById('repoStatusFilter').value;
  if (!window.scansHistoryData) return;
  const filtered = window.scansHistoryData.filter(scan => {
    const matchQuery = scan.product_name.toLowerCase().includes(query) || scan.id.toLowerCase().includes(query) || (scan.extracted_text && scan.extracted_text.toLowerCase().includes(query));
    return matchQuery && (filter === 'ALL' || scan.overall_status === filter);
  });
  renderRepositoryTable(filtered);
}

async function loadDashboardStats() {
  try {
    const response = await fetch('/api/dashboard_stats');
    if (!response.ok) throw new Error('Stats fetch failed');
    const stats = await response.json();
    document.getElementById('statTotalScans').textContent = stats.total_scans;
    document.getElementById('statComplianceRate').textContent = `${stats.compliance_rate}%`;
    document.getElementById('statWarningsCount').textContent = stats.warnings_count;
    document.getElementById('statViolationsCount').textContent = stats.violations_count;
    renderRecentScans(stats.recent_activity);
    renderViolationsChart(stats.violations_by_type);
    renderCategoriesChart(stats.compliance_by_category);
  } catch (error) { console.error(error); }
}

function renderRecentScans(recentList) {
  const tbody = document.getElementById('recentScansTableBody'); tbody.innerHTML = '';
  if (!recentList || recentList.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary py-4">No recent inspections found. Run the scanner first!</td></tr>'; return; }
  recentList.forEach(scan => {
    const row = document.createElement('tr');
    let badgeClass = 'passed';
    if (scan.overall_status === 'Warning') badgeClass = 'warning';
    else if (scan.overall_status === 'Failed') badgeClass = 'failed';
    const dateStr = scan.timestamp ? scan.timestamp.slice(0,16).replace('T', ' ') : 'N/A';
    row.innerHTML = `<td><code>#${scan.id}</code></td><td><strong>${scan.product_name}</strong></td><td>${dateStr}</td><td><strong>${scan.compliance_score}%</strong></td><td><span class="status-pill ${badgeClass}">${scan.overall_status}</span></td><td><button class="btn-secondary btn-text" style="padding: 2px 8px;">Audit View</button></td>`;
    row.querySelector('button').addEventListener('click', () => {
      fetch('/api/history').then(res => res.json()).then(scans => {
        const match = scans.find(s => s.id === scan.id);
        if (match) {
          AppState.activeScan = match; window.switchTab('scannerTab');
          document.getElementById('uploadPlaceholder').classList.add('hidden');
          document.getElementById('previewContainer').classList.remove('hidden');
          document.getElementById('imagePreview').src = match.filename ? `/uploads/${match.filename}` : '';
          displayAuditReport(match); drawBoundingBoxes(match);
        }
      });
    });
    tbody.appendChild(row);
  });
}

function renderViolationsChart(violationsData) {
  const ctx = document.getElementById('violationsChart').getContext('2d');
  if (AppState.charts.violations) AppState.charts.violations.destroy();
  const labels = Object.keys(violationsData); const values = Object.values(violationsData);
  const isZero = values.reduce((a,b)=>a+b, 0) === 0;
  AppState.charts.violations = new Chart(ctx, { type: 'doughnut', data: { labels, datasets: [{ data: isZero ? [2,1,3,1,0,2] : values, backgroundColor: ['#6366f1','#3b82f6','#f59e0b','#ec4899','#06b6d4','#ef4444'], borderWidth: 2, borderColor: '#ffffff' }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { font: { family: 'Inter', size: 10 } } } }, cutout: '60%' } });
}

function renderCategoriesChart(categoriesData) {
  const ctx = document.getElementById('categoriesChart').getContext('2d');
  if (AppState.charts.categories) AppState.charts.categories.destroy();
  const labels = Object.keys(categoriesData); const values = Object.values(categoriesData);
  AppState.charts.categories = new Chart(ctx, { type: 'bar', data: { labels, datasets: [{ label: 'Compliance rate (%)', data: values, backgroundColor: 'rgba(79, 70, 229, 0.8)', borderColor: 'var(--primary)', borderWidth: 1.5, borderRadius: 6 }] }, options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { min: 0, max: 100, ticks: { font: { family: 'Inter', size: 10 } } }, y: { ticks: { font: { family: 'Inter', size: 10 } } } } } });
}

function initRulesConfigurator() {
  document.getElementById('rulesEditForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!AppState.allRules || !AppState.activeRuleKey) return;
    const rule = AppState.allRules.mandatory_declarations[AppState.activeRuleKey];
    rule.friendly_name = document.getElementById('ruleFriendlyName').value;
    rule.required = document.getElementById('ruleRequired').value === 'true';
    rule.clause = document.getElementById('ruleClause').value;
    rule.patterns = document.getElementById('rulePatterns').value.split(',').map(s => s.trim()).filter(Boolean);
    if (AppState.activeRuleKey === 'NetQuantity') rule.allowed_units = document.getElementById('ruleAllowedUnits').value.split(',').map(s => s.trim()).filter(Boolean);
    if (rule.format_pattern !== undefined) rule.format_pattern = document.getElementById('ruleRegex').value;
    rule.description = document.getElementById('ruleDescription').value;
    try {
      const res = await fetch('/api/rules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(AppState.allRules) });
      if (res.ok) { alert('Rules updated successfully.'); loadRules(); } else throw new Error('Save failed');
    } catch (err) { console.error(err); alert('Error saving rules.'); }
  });
}

async function loadRules() {
  try {
    const response = await fetch('/api/rules');
    if (!response.ok) throw new Error('Rules fetch failed');
    const rules = await response.json();
    AppState.allRules = rules;
    const listGroup = document.getElementById('rulesListGroup'); listGroup.innerHTML = '';
    let firstKey = null;
    for (const [key, rule] of Object.entries(rules.mandatory_declarations)) {
      if (!firstKey) firstKey = key;
      const btn = document.createElement('button');
      btn.className = `rule-item-button ${AppState.activeRuleKey === key ? 'active' : ''}`;
      btn.innerHTML = `<span>${rule.friendly_name}</span><i class="fa-solid fa-angle-right"></i>`;
      btn.addEventListener('click', () => { selectRule(key); });
      listGroup.appendChild(btn);
    }
    selectRule(AppState.activeRuleKey || firstKey);
  } catch (error) { console.error(error); }
}

function selectRule(key) {
  AppState.activeRuleKey = key;
  const buttons = document.querySelectorAll('#rulesListGroup .rule-item-button');
  const index = Object.keys(AppState.allRules.mandatory_declarations).indexOf(key);
  buttons.forEach((btn, idx) => { btn.classList.toggle('active', idx === index); });
  const rule = AppState.allRules.mandatory_declarations[key];
  document.getElementById('ruleFriendlyName').value = rule.friendly_name;
  document.getElementById('ruleRequired').value = rule.required ? 'true' : 'false';
  document.getElementById('ruleClause').value = rule.clause || '';
  document.getElementById('rulePatterns').value = rule.patterns ? rule.patterns.join(', ') : '';
  if (rule.format_pattern !== undefined) { document.getElementById('ruleRegexWrapper').classList.remove('hidden'); document.getElementById('ruleRegex').value = rule.format_pattern; } else { document.getElementById('ruleRegexWrapper').classList.add('hidden'); }
  const unitsWrapper = document.getElementById('ruleAllowedUnits').parentNode;
  if (key === 'NetQuantity') { unitsWrapper.classList.remove('hidden'); document.getElementById('ruleAllowedUnits').value = rule.allowed_units ? rule.allowed_units.join(', ') : ''; } else { unitsWrapper.classList.add('hidden'); }
  document.getElementById('ruleDescription').value = rule.description || '';
  document.getElementById('saveRuleBtn').disabled = false;
}

function initDocsNav() {
  const docsLinks = document.querySelectorAll('.docs-nav-item');
  const docsSections = document.querySelectorAll('.docs-section');
  docsLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      docsLinks.forEach(l => l.classList.remove('active')); link.classList.add('active');
      const targetId = link.getAttribute('href').substring(1);
      docsSections.forEach(section => { section.classList.toggle('active', section.id === targetId); });
    });
  });
}
