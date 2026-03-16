const tasks = [
  { task: "S1 EP01 Dialogue ASR", agent: "ASR Agent", status: "running", eta: "2m" },
  { task: "S2 EP01 Speaker + Role", agent: "Role Agent", status: "queued", eta: "6m" },
  { task: "S3 EP01 Emotion Fusion", agent: "Emotion Agent", status: "queued", eta: "9m" },
  { task: "S4 EP01 Scene Sampling", agent: "Scene Agent", status: "blocked", eta: "--" },
  { task: "S1 EP02 Dialogue ASR", agent: "ASR Agent", status: "running", eta: "4m" },
  { task: "QA EP03 Emotion Scale", agent: "QA Agent", status: "running", eta: "3m" },
  { task: "S7 EP12 Hook Continuity", agent: "Hook Agent", status: "blocked", eta: "--" },
  { task: "S5 EP05 Script Generation", agent: "Script Agent", status: "queued", eta: "12m" },
  { task: "Shared Memory Sync", agent: "Memory Agent", status: "done", eta: "done" },
];

const agents = [
  { name: "Manager Agent", load: 82, note: "Scheduling 38 tasks" },
  { name: "QA Agent", load: 68, note: "3 alerts pending" },
  { name: "Emotion Agent", load: 74, note: "Calibrating EP08" },
  { name: "Hook Agent", load: 53, note: "Continuity scan EP12-EP15" },
  { name: "Scene Agent", load: 31, note: "Frame sampler idle" },
];

const hooks = [
  { title: "EP12 · Reversal hook", meta: "Score 0.46 · risk: language-dependent" },
  { title: "EP13 · Threat hook", meta: "Score 0.82 · stable handoff" },
  { title: "EP14 · Suspense hook", meta: "Score 0.77 · OK" },
];

const episodes = [
  {
    id: "EP01",
    title: "The Contract",
    status: "S1/S2 locked",
    qa: "Pass",
    peaks: ["00:01:58 anger 7", "00:03:20 relief 6"],
    hook: "Threat hook · score 0.84",
    artifacts: ["SRT ready", "Roles ready", "Script draft", "Hooks pending"],
  },
  {
    id: "EP02",
    title: "Hidden Ledger",
    status: "S1 running",
    qa: "Watch",
    peaks: ["00:02:40 shock 8"],
    hook: "Suspense hook · score 0.71",
    artifacts: ["SRT running", "Roles queued", "Script queued"],
  },
  {
    id: "EP08",
    title: "Boardroom Clash",
    status: "S3 review",
    qa: "Alert",
    peaks: ["00:01:12 sarcasm 6", "00:04:05 rage 9"],
    hook: "Reversal hook · score 0.52",
    artifacts: ["Emotion drift flagged", "Hook analysis queued"],
  },
  {
    id: "EP12",
    title: "Cold Evidence",
    status: "S6/S7 queued",
    qa: "Watch",
    peaks: ["00:02:22 fear 7"],
    hook: "Continuity break risk",
    artifacts: ["Script ready", "Emotion ready", "Hook review"],
  },
];

const taskTable = document.getElementById("taskTable");
const filterButtons = document.querySelectorAll(".filter-btn");
const agentList = document.getElementById("agentList");
const hookList = document.getElementById("hookList");
const episodeSelect = document.getElementById("episodeSelect");
const episodePanel = document.getElementById("episodePanel");

const renderTasks = (filter) => {
  taskTable.innerHTML = "";
  const filtered = tasks.filter((task) =>
    filter === "all" ? true : task.status === filter
  );

  filtered.forEach((task) => {
    const row = document.createElement("div");
    row.className = "table-row";
    row.innerHTML = `
      <span>${task.task}</span>
      <span>${task.agent}</span>
      <span class="status status--${task.status}">${task.status}</span>
      <span>${task.eta}</span>
    `;
    taskTable.appendChild(row);
  });
};

const renderAgents = () => {
  agentList.innerHTML = "";
  agents.forEach((agent) => {
    const card = document.createElement("div");
    card.className = "agent";
    card.innerHTML = `
      <div class="agent-header">
        <span>${agent.name}</span>
        <span>${agent.load}%</span>
      </div>
      <div class="progress">
        <div class="progress-bar progress-bar--blue" style="width: ${agent.load}%"></div>
      </div>
      <div class="agent-meta">${agent.note}</div>
    `;
    agentList.appendChild(card);
  });
};

const renderHooks = () => {
  hookList.innerHTML = "";
  hooks.forEach((hook) => {
    const item = document.createElement("div");
    item.className = "hook-item";
    item.innerHTML = `
      <div class="hook-title">${hook.title}</div>
      <div class="hook-meta">${hook.meta}</div>
    `;
    hookList.appendChild(item);
  });
};

const renderEpisodeSelect = () => {
  episodeSelect.innerHTML = "";
  episodes.forEach((episode) => {
    const option = document.createElement("option");
    option.value = episode.id;
    option.textContent = `${episode.id} · ${episode.title}`;
    episodeSelect.appendChild(option);
  });
};

const renderEpisodePanel = (episodeId) => {
  const episode = episodes.find((item) => item.id === episodeId) || episodes[0];
  if (!episode) return;

  episodePanel.innerHTML = `
    <div class="episode-card">
      <div class="episode-title">${episode.id} · ${episode.title}</div>
      <div class="episode-meta">Status: ${episode.status} · QA: ${episode.qa}</div>
      <div class="badge-row">
        ${episode.artifacts.map((item) => `<span class="badge">${item}</span>`).join("")}
      </div>
    </div>
    <div class="episode-card">
      <div class="episode-title">Emotion Peaks</div>
      <div class="episode-meta">${episode.peaks.join(" · ")}</div>
    </div>
    <div class="episode-card">
      <div class="episode-title">Hook Summary</div>
      <div class="episode-meta">${episode.hook}</div>
    </div>
  `;
};

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    filterButtons.forEach((btn) => btn.classList.remove("filter-btn--active"));
    button.classList.add("filter-btn--active");
    renderTasks(button.dataset.filter);
  });
});

if (episodeSelect) {
  episodeSelect.addEventListener("change", (event) => {
    renderEpisodePanel(event.target.value);
  });
}

renderTasks("all");
renderAgents();
renderHooks();
renderEpisodeSelect();
renderEpisodePanel(episodes[0]?.id);
