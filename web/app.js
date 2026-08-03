const state = {
  status: "all",
  track: "all",
  domain: "all",
  minScore: 35,
  query: "",
  items: [],
  scans: [],
  selectedId: null,
  loading: false,
  staticMode: false,
  sourceDirectory: {},
};

const statusLabels = {
  all: "Tout",
  nouveau: "Nouveau",
  "a-postuler": "A postuler",
  postule: "Postule",
  ignore: "Ignore",
};

const trackLabels = {
  "emploi-data": "Emploi data / M&E",
  consultance: "Consultance / appel",
};

const domainLabels = {
  "data-bi": "Data / BI / dashboards",
  "suivi-evaluation-etudes": "Suivi-evaluation / etudes",
  "developpement-app": "Developpement d'appli",
  communication: "Communication",
  autres: "Autres",
};

function byId(id) {
  return document.getElementById(id);
}

function statusClass(status) {
  return {
    nouveau: "fresh",
    "a-postuler": "apply",
    postule: "done",
    ignore: "muted",
  }[status] || "fresh";
}

async function loadData() {
  const params = new URLSearchParams({
    status: state.status,
    track: state.track,
    domain: state.domain,
    min_score: String(state.minScore),
  });
  if (state.query) params.set("q", state.query);
  const data = await fetchData(params);
  state.items = applyLocalFilters(data.items || []);
  state.scans = data.scans || [];
  state.sourceDirectory = data.source_directory || {};
  if (!state.selectedId && state.items[0]) state.selectedId = state.items[0].id;
  if (!state.items.some((item) => item.id === state.selectedId)) state.selectedId = state.items[0]?.id || null;
  renderAll();
}

async function fetchData(params) {
  if (!state.staticMode) {
    try {
      const response = await fetch(`/api/opportunities?${params.toString()}`);
      if (response.ok) return response.json();
    } catch (error) {
      state.staticMode = true;
    }
  }
  state.staticMode = true;
  const response = await fetch(`./data/opportunities.json?ts=${Date.now()}`);
  return response.json();
}

function applyLocalFilters(items) {
  const localStatuses = readLocalStatuses();
  return items
    .map((item) => ({ ...item, status: localStatuses[item.url] || item.status || "nouveau" }))
    .filter((item) => state.status === "all" || item.status === state.status)
    .filter((item) => state.track === "all" || item.track === state.track)
    .filter((item) => state.domain === "all" || item.domain === state.domain)
    .filter((item) => Number(item.score || 0) >= state.minScore)
    .filter((item) => {
      if (!state.query) return true;
      const text = [item.title, item.organization, item.description, item.location, item.domain, item.track]
        .join(" ")
        .toLowerCase();
      return text.includes(state.query.toLowerCase());
    });
}

async function runScan() {
  state.loading = true;
  renderLoading();
  try {
    if (state.staticMode) {
      alert("Sur GitHub Pages, le scan est automatise chaque matin par GitHub Actions. En local, lance .\\run.ps1 puis utilise ce bouton.");
      return;
    }
    const response = await fetch("/api/scan", { method: "POST" });
    const data = await response.json();
    state.items = data.items || [];
    state.selectedId = state.items[0]?.id || null;
    await loadData();
  } finally {
    state.loading = false;
    renderLoading();
  }
}

async function updateStatus(id, status) {
  const item = state.items.find((entry) => entry.id === id);
  if (state.staticMode && item) {
    const statuses = readLocalStatuses();
    statuses[item.url] = status;
    localStorage.setItem("gombo-statuses", JSON.stringify(statuses));
    await loadData();
    return;
  }
  await fetch(`/api/opportunities/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  await loadData();
}

function renderAll() {
  renderLoading();
  renderMetrics();
  renderList();
  renderDetail();
  renderScanMeta();
  renderSourceDirectory();
}

function renderLoading() {
  byId("loadingPill").classList.toggle("hidden", !state.loading);
  byId("scanBtn").disabled = state.loading;
  byId("scanBtn").textContent = state.loading ? "Scan..." : "Scanner maintenant";
}

function renderMetrics() {
  const items = state.items;
  const average = items.length ? Math.round(items.reduce((sum, item) => sum + Number(item.score || 0), 0) / items.length) : 0;
  const top = items.filter((item) => item.score >= 70).length;
  const emplois = items.filter((item) => item.track === "emploi-data").length;
  const consultances = items.filter((item) => item.track === "consultance").length;
  const metrics = [
    ["Opportunites", items.length, "filtrees"],
    ["Score moyen", average, "sur 100"],
    ["Tres proches", top, "score 70+"],
    ["Emplois", emplois, "data / M&E"],
    ["Consultances", consultances, "appels / missions"],
  ];
  byId("metrics").innerHTML = metrics
    .map(([label, value, note]) => `<div class="metric"><span>${label}</span><strong>${value}</strong><em>${note}</em></div>`)
    .join("");
}

function renderList() {
  const rows = state.items;
  byId("opportunityList").innerHTML = rows.length
    ? rows.map(renderRow).join("")
    : `<div class="empty-list"><strong>Aucune opportunite pour ce filtre.</strong><span>Lance un scan ou baisse le score minimum.</span></div>`;

  document.querySelectorAll(".opportunity-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedId = Number(row.dataset.id);
      renderAll();
    });
  });
}

function renderRow(item) {
  const selected = item.id === state.selectedId ? " selected" : "";
  return `<button class="opportunity-row${selected}" type="button" data-id="${item.id}">
    <span class="score">${item.score}</span>
    <span class="row-main">
      <strong>${escapeHtml(item.title)}</strong>
      <em>${escapeHtml(item.organization || "Organisation non precisee")} - ${escapeHtml(item.location || "Remote")}</em>
    </span>
    <span class="domain">${escapeHtml(domainLabels[item.domain] || item.domain || "Domaine")}</span>
    <span class="status ${statusClass(item.status)}">${statusLabels[item.status] || item.status}</span>
  </button>`;
}

function renderDetail() {
  const item = state.items.find((entry) => entry.id === state.selectedId);
  byId("detailEmpty").classList.toggle("hidden", Boolean(item));
  byId("detailContent").classList.toggle("hidden", !item);
  if (!item) return;

  byId("detailContent").innerHTML = `
    <div class="detail-top">
      <span class="score large">${item.score}</span>
      <div>
        <p class="overline">${escapeHtml(item.source || "Source")}</p>
        <h2>${escapeHtml(item.title)}</h2>
        <p>${escapeHtml(item.organization || "Organisation non precisee")}</p>
      </div>
    </div>

    <dl class="meta-grid">
      <div><dt>Lieu</dt><dd>${escapeHtml(item.location || "Remote")}</dd></div>
      <div><dt>Remote</dt><dd>${escapeHtml(item.remote_type || "remote")}</dd></div>
      <div><dt>Famille</dt><dd>${escapeHtml(trackLabels[item.track] || item.track || "Non classe")}</dd></div>
      <div><dt>Domaine</dt><dd>${escapeHtml(domainLabels[item.domain] || item.domain || "Non classe")}</dd></div>
      <div><dt>Type</dt><dd>${escapeHtml(item.opportunity_type || "job")}</dd></div>
      <div><dt>Deadline</dt><dd>${escapeHtml(formatDate(item.deadline) || "Non publiee")}</dd></div>
    </dl>

    <div class="keywords">
      ${(item.keywords || []).map((keyword) => `<span>${escapeHtml(keyword)}</span>`).join("") || "<span>Aucun mot-cle fort</span>"}
    </div>

    <p class="summary">${escapeHtml(item.summary || "Pas de resume disponible.")}</p>

    <div class="detail-actions">
      <a class="button primary" href="${escapeAttribute(item.url)}" target="_blank" rel="noreferrer">Ouvrir l'offre</a>
      <button type="button" data-next="a-postuler">A postuler</button>
      <button type="button" data-next="postule">Postule</button>
      <button type="button" data-next="ignore">Ignorer</button>
    </div>
  `;

  document.querySelectorAll("[data-next]").forEach((button) => {
    button.addEventListener("click", () => updateStatus(item.id, button.dataset.next));
  });
}

function renderScanMeta() {
  const scan = state.scans[0];
  if (!scan) {
    byId("scanMeta").textContent = "Aucun scan encore execute.";
    return;
  }
  const finished = scan.finished_at ? new Date(scan.finished_at).toLocaleString("fr-FR") : "en cours";
  const errors = scan.errors?.length ? ` - ${scan.errors.length} source(s) en erreur` : "";
  const mode = state.staticMode ? " - GitHub Pages" : "";
  byId("scanMeta").textContent = `Dernier scan : ${finished} - ${scan.found_count} trouvees${errors}${mode}`;
}

function renderSourceDirectory() {
  const target = byId("sourceDirectory");
  if (!target) return;
  const groups = Object.entries(state.sourceDirectory || {});
  if (!groups.length) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = groups
    .map(([group, links]) => `<div class="source-group">
      <strong>${escapeHtml(formatSourceGroup(group))}</strong>
      <div>${links.map((link) => `<a href="${escapeAttribute(link.url)}" target="_blank" rel="noreferrer">${escapeHtml(link.name)}</a>`).join("")}</div>
    </div>`)
    .join("");
}

function formatSourceGroup(group) {
  return {
    remote_job_boards: "Jobs remote monde",
    freelance_consultance: "Freelance / consultance",
    development_procurement: "Developpement international",
    africa_cote_ivoire: "Afrique / Cote d'Ivoire",
  }[group] || group.replaceAll("_", " ");
}

function readLocalStatuses() {
  try {
    return JSON.parse(localStorage.getItem("gombo-statuses") || "{}");
  } catch (error) {
    return {};
  }
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("fr-FR");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function bindEvents() {
  byId("scanBtn").addEventListener("click", runScan);
  byId("searchInput").addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    clearTimeout(window.__searchTimer);
    window.__searchTimer = setTimeout(loadData, 250);
  });
  byId("scoreInput").addEventListener("input", (event) => {
    state.minScore = Number(event.target.value);
    byId("scoreValue").textContent = state.minScore;
    clearTimeout(window.__scoreTimer);
    window.__scoreTimer = setTimeout(loadData, 150);
  });
  byId("domainSelect").addEventListener("change", (event) => {
    state.domain = event.target.value;
    loadData();
  });
  document.querySelectorAll("[data-status]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-status]").forEach((entry) => entry.classList.remove("active"));
      button.classList.add("active");
      state.status = button.dataset.status;
      loadData();
    });
  });
  document.querySelectorAll("[data-track]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-track]").forEach((entry) => entry.classList.remove("active"));
      button.classList.add("active");
      state.track = button.dataset.track;
      loadData();
    });
  });
}

bindEvents();
loadData();
