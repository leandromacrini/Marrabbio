const els = {
  sessionId: document.getElementById("session-id"),
  sessionDay: document.getElementById("session-day"),
  songsStarted: document.getElementById("songs-started"),
  errors: document.getElementById("errors"),
  fallbacks: document.getElementById("fallbacks"),
  topDay: document.getElementById("top-day"),
  topAll: document.getElementById("top-all"),
  calendarGrid: document.getElementById("calendar-grid"),
  monthPrev: document.getElementById("month-prev"),
  monthNext: document.getElementById("month-next"),
  monthLabel: document.getElementById("month-label"),
  modal: document.getElementById("day-modal"),
  modalTitle: document.getElementById("modal-title"),
  modalClose: document.getElementById("modal-close"),
  mSessions: document.getElementById("m-sessions"),
  mSongs: document.getElementById("m-songs"),
  mErrors: document.getElementById("m-errors"),
  mFallbacks: document.getElementById("m-fallbacks"),
  mTopDay: document.getElementById("m-top-day"),
  mFiles: document.getElementById("m-files"),
  mRaw: document.getElementById("m-raw"),
};

let refreshMs = 2000;
let currentStartupDay = null;
const calendarCursor = new Date();
calendarCursor.setDate(1);

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status} on ${path}`);
  return res.json();
}

function setText(el, value) {
  if (!el) return;
  el.textContent = value;
}

function renderLive(data) {
  const counters = data.counters || {};
  currentStartupDay = data.startup_day || currentStartupDay;
  setText(els.sessionDay, data.startup_day || "-");
  setText(els.sessionId, `Log file: ${data.session_id || "-"}`);
  setText(els.songsStarted, counters.song_started_total || 0);
  setText(els.errors, counters.error_total || 0);
  setText(els.fallbacks, counters.song_fallback_total || 0);
}

function renderTopList(el, items) {
  el.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "Nessun dato";
    el.appendChild(li);
    return;
  }
  items.forEach((row, idx) => {
    const li = document.createElement("li");
    const title = row.title && row.title.trim() ? row.title : "Titolo sconosciuto";
    const label = row.count === 1 ? "volta" : "volte";
    li.textContent = `${row.count} ${label} - #${row.code} - ${title}`;
    el.appendChild(li);
  });
}

function dayCard(row) {
  const node = document.createElement("button");
  node.type = "button";
  node.className = "day-card";
  node.dataset.day = row.day;
  node.innerHTML = `
    <p class="day-date">${row.day}</p>
    <p class="day-line">Sessioni: ${row.sessions || 0}</p>
    <p class="day-line">Canzoni: ${row.song_started_total || 0}</p>
    <p class="day-line">Errori: ${row.error_total || 0}</p>
  `;
  node.addEventListener("click", () => openDay(row.day));
  return node;
}

function renderCalendar(days) {
  els.calendarGrid.innerHTML = "";
  if (!days || days.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "Nessun dato disponibile.";
    els.calendarGrid.appendChild(empty);
    return;
  }
  days.forEach((row) => els.calendarGrid.appendChild(dayCard(row)));
}

function renderMonthLabel() {
  const label = calendarCursor.toLocaleDateString("it-IT", {
    month: "long",
    year: "numeric",
  });
  setText(els.monthLabel, label);
}

async function openDay(day) {
  try {
    const [data, topDay] = await Promise.all([
      api(`/api/day/${day}`),
      api(`/api/top/day/${day}`),
    ]);
    const summary = data.summary || {};
    setText(els.modalTitle, `Dettaglio ${data.day}`);
    setText(els.mSessions, (data.sessions || []).length);
    setText(els.mSongs, summary.song_started_total || 0);
    setText(els.mErrors, summary.error_total || 0);
    setText(els.mFallbacks, summary.song_fallback_total || 0);
    renderTopList(els.mTopDay, topDay.items || []);

    els.mFiles.innerHTML = "";
    (data.sessions || []).forEach((name) => {
      const li = document.createElement("li");
      li.textContent = name;
      els.mFiles.appendChild(li);
    });
    els.mRaw.textContent = JSON.stringify(summary, null, 2);
    els.modal.showModal();
  } catch (err) {
    console.error(err);
  }
}

async function tickLive() {
  try {
    const data = await api("/api/live");
    renderLive(data);
  } catch (err) {
    console.error(err);
  }
}

async function loadCalendar() {
  try {
    const y = calendarCursor.getFullYear();
    const m = calendarCursor.getMonth() + 1;
    const data = await api(`/api/calendar?year=${y}&month=${m}`);
    renderCalendar(data.days || []);
  } catch (err) {
    console.error(err);
  }
}

async function loadTopSongs() {
  try {
    const all = await api("/api/top/all");
    renderTopList(els.topAll, all.items || []);
  } catch (err) {
    console.error(err);
  }

  if (!currentStartupDay) return;

  try {
    const day = await api(`/api/top/day/${currentStartupDay}`);
    renderTopList(els.topDay, day.items || []);
  } catch (err) {
    console.error(err);
  }
}

async function initConfig() {
  try {
    const cfg = await api("/api/config");
    if (cfg.refresh_seconds && Number.isFinite(cfg.refresh_seconds)) {
      refreshMs = Math.max(1000, cfg.refresh_seconds * 1000);
    }
  } catch (_err) {
    // Keep defaults.
  }
}

function setupModal() {
  els.modalClose.addEventListener("click", () => els.modal.close());
  els.modal.addEventListener("click", (ev) => {
    const rect = els.modal.getBoundingClientRect();
    const inside =
      ev.clientX >= rect.left &&
      ev.clientX <= rect.right &&
      ev.clientY >= rect.top &&
      ev.clientY <= rect.bottom;
    if (!inside) els.modal.close();
  });
}

function setupMonthControls() {
  renderMonthLabel();
  els.monthPrev.addEventListener("click", async () => {
    calendarCursor.setMonth(calendarCursor.getMonth() - 1);
    renderMonthLabel();
    await loadCalendar();
  });
  els.monthNext.addEventListener("click", async () => {
    calendarCursor.setMonth(calendarCursor.getMonth() + 1);
    renderMonthLabel();
    await loadCalendar();
  });
}

async function boot() {
  setupModal();
  setupMonthControls();
  await initConfig();
  await tickLive();
  await loadCalendar();
  await loadTopSongs();
  setInterval(tickLive, refreshMs);
  setInterval(loadCalendar, Math.max(5000, refreshMs * 2));
  setInterval(loadTopSongs, Math.max(5000, refreshMs * 2));
}

boot();
