const state = {
  projectId: "project_blue_pen",
  lineage: { nodes: [], edges: [], impacts: [] },
  skills: [],
  workflows: [],
  selectedArtifactId: null,
  workflowRun: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed: ${response.status}`);
  return payload;
}

function toast(message) {
  const node = $("toast");
  node.textContent = message;
  node.classList.remove("hidden");
  window.setTimeout(() => node.classList.add("hidden"), 3200);
}

function currentVersion(node) {
  return node.current_version || {};
}

function renderMetrics() {
  const counts = state.lineage.nodes.reduce((acc, node) => {
    const status = currentVersion(node).status || "unknown";
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});
  const metrics = [
    [state.lineage.nodes.length, "Canonical artifacts"],
    [state.lineage.edges.length, "Lineage edges"],
    [state.skills.length, "Repository skills"],
    [state.lineage.impacts.filter((item) => item.resolution_status === "unresolved").length, "Open impact records"],
  ];
  $("metrics").innerHTML = metrics.map(([value, label]) => `
    <article class="metric"><strong>${value}</strong><span>${label}</span></article>
  `).join("");
}

function renderArtifacts() {
  $("artifactList").innerHTML = state.lineage.nodes.map((node) => {
    const version = currentVersion(node);
    return `
      <article class="artifact-card ${state.selectedArtifactId === node.id ? "selected" : ""}" data-id="${node.id}">
        <h3>${escapeHtml(node.title)}</h3>
        <p>${escapeHtml(node.artifact_type)} · v${version.version_number}</p>
        <div class="meta-row">
          <span class="status-pill ${version.status}">${version.status}</span>
          <span>${version.content_hash?.slice(7, 15) || "—"}</span>
        </div>
      </article>`;
  }).join("");
  document.querySelectorAll(".artifact-card").forEach((card) => {
    card.addEventListener("click", () => selectArtifact(card.dataset.id));
  });
}

function stageFor(type) {
  const stages = {
    creative_constitution: 0,
    evidence_item: 0,
    character: 1,
    relationship: 1,
    beat_graph: 1,
    scene_contract: 2,
    screenplay_scene: 3,
    screenplay_patch: 3,
    audio_bible: 3,
    shot_contract: 4,
    critic_finding: 4,
  };
  return stages[type] ?? 5;
}

function renderGraph() {
  const svg = $("lineageGraph");
  const grouped = new Map();
  state.lineage.nodes.forEach((node) => {
    const stage = stageFor(node.artifact_type);
    if (!grouped.has(stage)) grouped.set(stage, []);
    grouped.get(stage).push(node);
  });
  const positions = new Map();
  let maxRows = 1;
  [...grouped.entries()].forEach(([stage, nodes]) => {
    maxRows = Math.max(maxRows, nodes.length);
    nodes.forEach((node, index) => positions.set(node.id, { x: 30 + stage * 190, y: 35 + index * 92 }));
  });
  const width = 30 + 6 * 190;
  const height = Math.max(490, 70 + maxRows * 92);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const lines = state.lineage.edges.map((edge) => {
    const a = positions.get(edge.parent_artifact_id);
    const b = positions.get(edge.child_artifact_id);
    if (!a || !b) return "";
    return `<path d="M ${a.x + 150} ${a.y + 27} C ${a.x + 172} ${a.y + 27}, ${b.x - 22} ${b.y + 27}, ${b.x} ${b.y + 27}" stroke="#44506a" stroke-width="1.5" fill="none"><title>${escapeHtml(edge.edge_type)}</title></path>`;
  }).join("");

  const nodes = state.lineage.nodes.map((node) => {
    const pos = positions.get(node.id);
    const version = currentVersion(node);
    const palette = {
      locked: ["#173057", "#9fc5ff"],
      approved: ["#173b33", "#74d3ae"],
      proposed: ["#47391e", "#f2c879"],
      draft: ["#262b35", "#d6dbe5"],
    }[version.status] || ["#262b35", "#d6dbe5"];
    const selected = state.selectedArtifactId === node.id;
    return `
      <g class="graph-node" data-id="${node.id}" tabindex="0" role="button">
        <rect x="${pos.x}" y="${pos.y}" width="150" height="55" rx="11" fill="${palette[0]}" stroke="${selected ? "#ffffff" : palette[1]}" stroke-width="${selected ? 2.4 : 1.2}" />
        <text x="${pos.x + 10}" y="${pos.y + 21}" fill="#f5f7fb" font-size="11" font-weight="700">${escapeXml(shorten(node.title, 20))}</text>
        <text x="${pos.x + 10}" y="${pos.y + 39}" fill="${palette[1]}" font-size="9">${escapeXml(node.artifact_type)} · v${version.version_number}</text>
      </g>`;
  }).join("");
  svg.innerHTML = lines + nodes;
  svg.querySelectorAll(".graph-node").forEach((node) => {
    node.addEventListener("click", () => selectArtifact(node.dataset.id));
    node.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectArtifact(node.dataset.id);
    });
  });
}

function renderInspector() {
  const node = state.lineage.nodes.find((item) => item.id === state.selectedArtifactId);
  if (!node) {
    $("inspectorTitle").textContent = "Select an artifact";
    $("inspectorJson").textContent = "Click a node or artifact card.";
    $("inspectorStatus").classList.add("hidden");
    $("approveVersionButton").disabled = true;
    $("lockVersionButton").disabled = true;
    return;
  }
  const version = currentVersion(node);
  $("inspectorTitle").textContent = node.title;
  $("inspectorJson").textContent = JSON.stringify(node, null, 2);
  const status = $("inspectorStatus");
  status.textContent = version.status;
  status.className = `status-pill ${version.status}`;
  $("approveVersionButton").disabled = !["draft", "proposed"].includes(version.status);
  $("lockVersionButton").disabled = version.status !== "approved";
}

function renderSkills() {
  $("skillsList").innerHTML = state.skills.map((skill) => `
    <article class="skill-card">
      <h3>${escapeHtml(skill.name)} <span class="muted">v${escapeHtml(skill.version)}</span></h3>
      <p>${escapeHtml(skill.description)}</p>
      <div class="meta-row"><span>${skill.file_count} files</span><span>${skill.digest.slice(7, 17)}</span></div>
    </article>`).join("") || `<div class="empty">No skills found.</div>`;
}

function renderImpacts() {
  const open = state.lineage.impacts.filter((item) => item.resolution_status === "unresolved");
  $("impactList").innerHTML = open.length ? open.map((impact) => `
    <article class="impact-card">
      <strong>${escapeHtml(impact.affected_title)}</strong>
      <p>${escapeHtml(impact.classification)} · ${escapeHtml(impact.reason)}</p>
    </article>`).join("") : `<div class="empty">No open impacts. Revise the Scene Contract to see graph-reachability impact records.</div>`;
}

function renderAll() {
  renderMetrics();
  renderArtifacts();
  renderGraph();
  renderInspector();
  renderSkills();
  renderImpacts();
}

function selectArtifact(id) {
  state.selectedArtifactId = id;
  renderAll();
}

async function load() {
  const [lineage, skills, workflows] = await Promise.all([
    api(`/api/projects/${state.projectId}/lineage`),
    api("/api/skills"),
    api("/api/workflows"),
  ]);
  state.lineage = lineage;
  state.skills = skills;
  state.workflows = workflows;
  if (!state.selectedArtifactId && lineage.nodes.length) state.selectedArtifactId = lineage.nodes[0].id;
  if (!lineage.nodes.find((item) => item.id === state.selectedArtifactId)) state.selectedArtifactId = lineage.nodes[0]?.id || null;
  renderAll();
}

async function reviseScene() {
  await api("/api/demo/revise-scene-contract", { method: "POST" });
  toast("Created a new Scene Contract version and impact records for descendants.");
  await load();
  const scene = state.lineage.nodes.find((node) => node.artifact_type === "scene_contract");
  if (scene) selectArtifact(scene.id);
}

async function approveSelected() {
  const node = state.lineage.nodes.find((item) => item.id === state.selectedArtifactId);
  if (!node) return;
  await api(`/api/versions/${currentVersion(node).id}/approve`, {
    method: "POST",
    body: JSON.stringify({ rationale: "Approved through the human prototype interface." }),
  });
  toast("Version approved by a human action.");
  await load();
}

async function lockSelected() {
  const node = state.lineage.nodes.find((item) => item.id === state.selectedArtifactId);
  if (!node) return;
  await api(`/api/versions/${currentVersion(node).id}/lock`, {
    method: "POST",
    body: JSON.stringify({ rationale: "Locked as the current canonical prototype version." }),
  });
  toast("Approved version locked; payload remains immutable.");
  await load();
}

async function runWorkflow() {
  const sceneContract = state.lineage.nodes.find((node) => node.artifact_type === "scene_contract");
  const screenplay = state.lineage.nodes.find((node) => node.artifact_type === "screenplay_scene");
  if (!sceneContract || !screenplay) throw new Error("Seed artifacts are missing.");
  const result = await api("/api/workflows/prototype-subtext-review/run", {
    method: "POST",
    body: JSON.stringify({
      project_id: state.projectId,
      inputs: {
        scene_contract_version_id: currentVersion(sceneContract).id,
        screenplay_scene_version_id: currentVersion(screenplay).id,
      },
    }),
  });
  state.workflowRun = result;
  $("workflowOutput").textContent = JSON.stringify(result, null, 2);
  $("approveWorkflowButton").disabled = result.status !== "waiting_for_human";
  toast("Agent proposed a patch. The workflow is waiting for human approval.");
  await load();
  const patch = state.lineage.nodes.find((node) => node.current_version?.id === result.output_version_id);
  if (patch) selectArtifact(patch.id);
}

async function approveWorkflow() {
  if (!state.workflowRun) return;
  const result = await api(`/api/workflow-runs/${state.workflowRun.id}/approve`, {
    method: "POST",
    body: JSON.stringify({ rationale: "The proposed subtext patch preserves the locked Scene Contract." }),
  });
  state.workflowRun = result;
  $("workflowOutput").textContent = JSON.stringify(result, null, 2);
  $("approveWorkflowButton").disabled = true;
  toast("Human approval recorded. The agent never held approval authority.");
  await load();
}

async function resetDemo() {
  await api("/api/demo/reset", { method: "POST" });
  state.selectedArtifactId = null;
  state.workflowRun = null;
  $("workflowOutput").textContent = "No workflow run yet.";
  $("approveWorkflowButton").disabled = true;
  toast("Prototype reset to the deterministic Blue Pen seed.");
  await load();
}

function shorten(value, max) {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}
function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}
function escapeXml(value) { return escapeHtml(value); }

$("refreshButton").addEventListener("click", () => load().catch((error) => toast(error.message)));
$("resetButton").addEventListener("click", () => resetDemo().catch((error) => toast(error.message)));
$("reviseSceneButton").addEventListener("click", () => reviseScene().catch((error) => toast(error.message)));
$("approveVersionButton").addEventListener("click", () => approveSelected().catch((error) => toast(error.message)));
$("lockVersionButton").addEventListener("click", () => lockSelected().catch((error) => toast(error.message)));
$("runWorkflowButton").addEventListener("click", () => runWorkflow().catch((error) => toast(error.message)));
$("approveWorkflowButton").addEventListener("click", () => approveWorkflow().catch((error) => toast(error.message)));

load().catch((error) => toast(error.message));
