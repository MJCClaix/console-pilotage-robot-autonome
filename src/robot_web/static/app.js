"use strict";

(() => {
  // ---------------------------------------------------------------- Utilitaires
  const $ = (selector) => document.querySelector(selector);

  const AXES = [
    { kind: "forward", title: "Avancer / Reculer", hint: "négatif = reculer" },
    { kind: "translate", title: "Translation", hint: "déplacement latéral" },
    { kind: "rotate", title: "Rotation", hint: "sur place" },
  ];

  const STEP_NAMES = {
    forward: (step) => (step.intensity < 0 ? "Reculer" : "Avancer"),
    translate: () => "Translation",
    rotate: () => "Rotation",
    sleep: () => "Pause",
  };

  const state = {
    mode: "text",
    steps: [],
    chip: "forward",
    lastRunId: null,
    status: null,
    history: [],
    historyIndex: 0,
  };

  const el = {
    target: $("#target"),
    runstate: $("#runstate"),
    stateText: $("#state-text"),
    stateDetail: $("#state-detail"),
    progress: $("#progress-bar"),
    stop: $("#stop-btn"),
    axes: $("#axes"),
    settingsForm: $("#settings-form"),
    setHost: $("#set-host"),
    setPort: $("#set-port"),
    setTimeout: $("#set-timeout"),
    modeSwitch: $("#mode-switch"),
    select: $("#script-select"),
    name: $("#script-name"),
    save: $("#save-btn"),
    remove: $("#delete-btn"),
    importBtn: $("#import-btn"),
    exportBtn: $("#export-btn"),
    importFile: $("#import-file"),
    run: $("#run-btn"),
    textPane: $("#text-pane"),
    gutter: $("#gutter"),
    text: $("#script-text"),
    listPane: $("#list-pane"),
    hint: $("#hint"),
    chips: $("#type-chips"),
    addIntensityLabel: $("#add-intensity-label"),
    addIntensity: $("#add-intensity"),
    addDuration: $("#add-duration"),
    add: $("#add-btn"),
    steps: $("#steps"),
    stepsEmpty: $("#steps-empty"),
    log: $("#log"),
    terminalForm: $("#terminal-form"),
    terminalInput: $("#terminal-input"),
    clear: $("#clear-btn"),
    toasts: $("#toasts"),
  };

  async function api(path, { method = "GET", body } = {}) {
    let response;
    try {
      response = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new Error("Serveur injoignable");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `Erreur ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function toast(message, kind = "info") {
    const node = document.createElement("div");
    node.className = `toast ${kind}`;
    node.textContent = message;
    el.toasts.append(node);
    setTimeout(() => {
      node.classList.add("leaving");
      setTimeout(() => node.remove(), 260);
    }, 4200);
  }

  /** Exécute une action en affichant l'erreur éventuelle dans une notification. */
  async function guarded(action) {
    try {
      return await action();
    } catch (error) {
      toast(error.message, error.status === 409 ? "warn" : "error");
      return undefined;
    }
  }

  const num = (value) => String(Number(value));

  // ------------------------------------------------------ Commande manuelle
  function buildAxes() {
    for (const axis of AXES) {
      const wrap = document.createElement("div");
      wrap.className = "axis";
      wrap.innerHTML = `
        <div class="axis-head"><strong></strong><small></small></div>
        <div class="axis-row">
          <input type="range" min="-255" max="255" step="1" value="0" aria-label="Intensité">
          <input type="number" min="-255" max="255" step="1" value="0" aria-label="Intensité (valeur)">
        </div>
        <div class="axis-send">
          <label>Durée (s)<input type="number" min="0" step="0.1" value="1"></label>
          <button class="btn primary" type="button">Envoyer</button>
        </div>`;
      wrap.querySelector("strong").textContent = axis.title;
      wrap.querySelector("small").textContent = axis.hint;

      const [slider, intensity] = wrap.querySelectorAll(".axis-row input");
      const duration = wrap.querySelector(".axis-send input");
      slider.addEventListener("input", () => (intensity.value = slider.value));
      intensity.addEventListener("input", () => (slider.value = intensity.value));
      wrap.querySelector("button").addEventListener("click", () =>
        guarded(async () => {
          await api("/api/send", {
            method: "POST",
            body: { axis: axis.kind, intensity: Number(intensity.value), duration: Number(duration.value) },
          });
          refreshStatus();
        })
      );
      el.axes.append(wrap);
    }
  }

  // ----------------------------------------------------------------- Réglages
  function showSettings(settings) {
    el.setHost.value = settings.host;
    el.setPort.value = settings.port;
    el.setTimeout.value = settings.timeout;
    el.target.textContent = `${settings.host}:${settings.port}`;
  }

  const loadSettings = () => guarded(async () => showSettings(await api("/api/settings")));

  el.settingsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    guarded(async () => {
      const saved = await api("/api/settings", {
        method: "PUT",
        body: {
          host: el.setHost.value.trim(),
          port: Number(el.setPort.value),
          timeout: Number(el.setTimeout.value),
        },
      });
      showSettings(saved);
      toast("Réglages enregistrés", "success");
    });
  });

  // ------------------------------------------------------------ Éditeur : liste
  const stepToLine = (step) =>
    step.kind === "sleep" ? `sleep(${num(step.duration)})` : `${step.kind}(${step.intensity}, ${num(step.duration)})`;

  const fromServer = (item) =>
    item.type === "sleep"
      ? { kind: "sleep", duration: item.duration }
      : { kind: item.axis, intensity: item.intensity, duration: item.duration };

  function renderSteps() {
    el.steps.replaceChildren();
    el.stepsEmpty.hidden = state.steps.length > 0;
    state.steps.forEach((step, index) => {
      const item = document.createElement("li");
      item.className = "step";
      item.dataset.index = String(index);

      const number = document.createElement("span");
      number.className = "num";
      number.textContent = String(index + 1).padStart(2, "0");

      const name = document.createElement("span");
      name.className = "name";
      name.textContent = STEP_NAMES[step.kind](step);
      const detail = document.createElement("small");
      detail.textContent =
        step.kind === "sleep" ? `${num(step.duration)} s` : `${step.intensity > 0 ? "+" : ""}${step.intensity} · ${num(step.duration)} s`;
      name.append(detail);

      const code = document.createElement("span");
      code.className = "code";
      code.textContent = stepToLine(step);

      const tools = document.createElement("span");
      tools.className = "tools";
      tools.append(
        iconButton("↑", "Monter", () => moveStep(index, -1), index === 0),
        iconButton("↓", "Descendre", () => moveStep(index, 1), index === state.steps.length - 1),
        iconButton("✕", "Supprimer la ligne", () => removeStep(index), false, "remove")
      );

      item.append(number, name, code, tools);
      el.steps.append(item);
    });
    highlightCurrentStep();
  }

  function iconButton(label, title, onClick, disabled, extraClass = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `icon-btn ${extraClass}`.trim();
    button.textContent = label;
    button.title = title;
    button.setAttribute("aria-label", title);
    button.disabled = disabled;
    button.addEventListener("click", onClick);
    return button;
  }

  function moveStep(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= state.steps.length) return;
    [state.steps[index], state.steps[target]] = [state.steps[target], state.steps[index]];
    renderSteps();
  }

  function removeStep(index) {
    state.steps.splice(index, 1);
    renderSteps();
  }

  function highlightCurrentStep() {
    const status = state.status;
    const active = status && status.running && status.label === "script" && state.mode === "list";
    el.steps.querySelectorAll(".step").forEach((item, index) => {
      item.classList.toggle("current", Boolean(active) && index === status.step - 1);
      item.classList.toggle("done", Boolean(active) && index < status.step - 1);
    });
  }

  el.chips.addEventListener("click", (event) => {
    const chip = event.target.closest(".chip");
    if (!chip) return;
    state.chip = chip.dataset.type;
    el.chips.querySelectorAll(".chip").forEach((node) => node.classList.toggle("active", node === chip));
    el.addIntensityLabel.hidden = state.chip === "sleep";
  });

  el.add.addEventListener("click", () => {
    const duration = Number(el.addDuration.value);
    if (!Number.isFinite(duration) || duration < 0) return toast("Durée invalide (nombre positif attendu)", "error");
    if (state.chip === "sleep") {
      state.steps.push({ kind: "sleep", duration });
    } else {
      const intensity = Number(el.addIntensity.value);
      if (!Number.isInteger(intensity) || Math.abs(intensity) > 255) {
        return toast("Intensité invalide (entier de -255 à 255)", "error");
      }
      state.steps.push({ kind: state.chip, intensity, duration });
    }
    renderSteps();
    el.steps.scrollTop = el.steps.scrollHeight;
  });

  // ----------------------------------------------------------- Éditeur : texte
  function updateGutter() {
    const lines = el.text.value.split("\n").length;
    el.gutter.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
    el.gutter.scrollTop = el.text.scrollTop;
  }
  el.text.addEventListener("input", updateGutter);
  el.text.addEventListener("scroll", () => (el.gutter.scrollTop = el.text.scrollTop));

  // ------------------------------------------------------------- Bascule texte/liste
  const currentContent = () => (state.mode === "list" ? state.steps.map(stepToLine).join("\n") : el.text.value);

  function applyMode(mode) {
    state.mode = mode;
    el.modeSwitch.dataset.mode = mode;
    el.modeSwitch.querySelectorAll("button").forEach((button) =>
      button.setAttribute("aria-pressed", String(button.dataset.mode === mode))
    );
    el.textPane.hidden = mode !== "text";
    el.listPane.hidden = mode !== "list";
    el.hint.hidden = mode !== "text";
    highlightCurrentStep();
  }

  async function parseIntoSteps(text) {
    const data = await api("/api/script/parse", { method: "POST", body: { content: text } });
    state.steps = data.instructions.map(fromServer);
    renderSteps();
  }

  async function setMode(mode) {
    if (mode === state.mode) return;
    if (mode === "list") {
      const text = el.text.value;
      const ok = await guarded(async () => {
        await parseIntoSteps(text);
        return true;
      });
      if (!ok) return;
      if (text.includes("#")) toast("Les commentaires ne sont pas conservés en mode liste", "warn");
    } else {
      el.text.value = state.steps.map(stepToLine).join("\n");
      updateGutter();
    }
    applyMode(mode);
  }

  el.modeSwitch.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-mode]");
    if (button) setMode(button.dataset.mode);
  });

  // ------------------------------------------------------------ Scripts enregistrés
  async function refreshScriptList(selected = "") {
    const { names } = await api("/api/scripts");
    el.select.replaceChildren(new Option("— nouveau script —", ""));
    names.forEach((name) => el.select.append(new Option(name, name)));
    el.select.value = names.includes(selected) ? selected : "";
  }

  el.select.addEventListener("change", () =>
    guarded(async () => {
      const name = el.select.value;
      if (!name) {
        el.name.value = "";
        return;
      }
      const { content } = await api(`/api/scripts/${encodeURIComponent(name)}`);
      el.name.value = name;
      el.text.value = content;
      updateGutter();
      if (state.mode === "list") await parseIntoSteps(content);
    })
  );

  el.save.addEventListener("click", () =>
    guarded(async () => {
      const name = el.name.value.trim();
      if (!name) return toast("Donne un nom au script avant de l'enregistrer", "warn");
      await api(`/api/scripts/${encodeURIComponent(name)}`, { method: "PUT", body: { content: currentContent() } });
      await refreshScriptList(name);
      toast(`Script « ${name} » enregistré`, "success");
    })
  );

  el.remove.addEventListener("click", () =>
    guarded(async () => {
      const name = el.select.value;
      if (!name) return toast("Sélectionne un script enregistré à supprimer", "warn");
      if (!confirm(`Supprimer définitivement le script « ${name} » ?`)) return;
      await api(`/api/scripts/${encodeURIComponent(name)}`, { method: "DELETE" });
      el.name.value = "";
      await refreshScriptList();
      toast(`Script « ${name} » supprimé`, "success");
    })
  );

  // ------------------------------------------------------------ Import / export .rbs
  el.exportBtn.addEventListener("click", () => {
    const name = el.name.value.trim() || "script";
    const url = URL.createObjectURL(new Blob([currentContent()], { type: "text/plain;charset=utf-8" }));
    const link = Object.assign(document.createElement("a"), { href: url, download: `${name}.rbs` });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  });

  el.importBtn.addEventListener("click", () => el.importFile.click());

  el.importFile.addEventListener("change", () =>
    guarded(async () => {
      const file = el.importFile.files[0];
      el.importFile.value = "";
      if (!file) return;
      const content = await file.text();
      // Vérifie la syntaxe avant de remplacer l'éditeur.
      await api("/api/script/parse", { method: "POST", body: { content } });
      const base = file.name.replace(/\.rbs$/i, "");
      el.text.value = content;
      el.name.value = /^[A-Za-z0-9_-]{1,64}$/.test(base) ? base : "";
      el.select.value = "";
      updateGutter();
      if (state.mode === "list") await parseIntoSteps(content);
      toast(`Fichier « ${file.name} » importé (pensez à enregistrer)`, "success");
    })
  );

  el.run.addEventListener("click", () =>
    guarded(async () => {
      const { total } = await api("/api/script/run", { method: "POST", body: { content: currentContent() } });
      toast(`Script lancé (${total} instruction${total > 1 ? "s" : ""})`, "success");
      refreshStatus();
    })
  );

  // -------------------------------------------------------------- État / arrêt
  const OUTCOMES = {
    completed: ["Exécution terminée", "success"],
    stopped: ["Exécution interrompue", "warn"],
    error: ["Exécution en erreur", "error"],
  };

  function renderStatus(status) {
    const running = status.running;
    el.runstate.dataset.state = running ? "running" : "idle";
    if (running) {
      el.stateText.textContent = status.label === "script" ? "Script en cours" : "Commande en cours";
      el.stateDetail.textContent = `Instruction ${Math.max(status.step, 1)} sur ${status.total}`;
      el.progress.style.width = `${(Math.max(status.step - 1, 0) / Math.max(status.total, 1)) * 100}%`;
    } else {
      el.stateText.textContent = "Au repos";
      el.stateDetail.textContent = status.outcome ? OUTCOMES[status.outcome][0] : "Aucune exécution en cours";
      el.progress.style.width = status.outcome === "completed" ? "100%" : "0";
    }
    el.stop.disabled = !running;
  }

  function notifyOutcome(status) {
    if (status.running || !status.outcome) return;
    const [message, kind] = OUTCOMES[status.outcome];
    toast(status.error ? `${message} : ${status.error}` : message, kind);
  }

  async function refreshStatus() {
    let status;
    try {
      status = await api("/api/status");
    } catch {
      el.stateText.textContent = "Serveur injoignable";
      return;
    }
    renderStatus(status);
    if (state.lastRunId !== null && status.run_id !== state.lastRunId) notifyOutcome(status);
    state.lastRunId = status.run_id;
    state.status = status;
    highlightCurrentStep();
  }

  async function stop() {
    await guarded(async () => {
      const { stopped } = await api("/api/stop", { method: "POST", body: {} });
      if (!stopped) toast("Rien à arrêter", "info");
      refreshStatus();
    });
  }

  el.stop.addEventListener("click", stop);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.status && state.status.running) stop();
  });

  // ----------------------------------------------------------------- Terminal
  function logLine(text, className) {
    const node = document.createElement("div");
    node.className = className;
    node.textContent = text;
    el.log.append(node);
    el.log.scrollTop = el.log.scrollHeight;
  }

  el.clear.addEventListener("click", () => el.log.replaceChildren());

  el.terminalForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const line = el.terminalInput.value.trim();
    if (!line) return;
    el.terminalInput.value = "";
    state.history.push(line);
    state.historyIndex = state.history.length;
    if (line === "clear") return el.log.replaceChildren();

    logLine(`› ${line}`, "cmd");
    el.terminalInput.disabled = true; // comme un vrai terminal : la commande occupe l'invite
    try {
      const { output, exit_code } = await api("/api/terminal", { method: "POST", body: { line } });
      if (output) logLine(output, `out${exit_code ? " err" : ""}`);
    } catch (error) {
      logLine(error.message, "out err");
    } finally {
      el.terminalInput.disabled = false;
      el.terminalInput.focus();
      refreshStatus();
      loadSettings();
    }
  });

  el.terminalInput.addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.key.toLowerCase() === "c" && !window.getSelection().toString()) {
      event.preventDefault();
      if (state.status && state.status.running) stop(); // Ctrl-C interrompt la commande en cours
      return;
    }
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();
    const next = state.historyIndex + (event.key === "ArrowUp" ? -1 : 1);
    if (next < 0 || next > state.history.length) return;
    state.historyIndex = next;
    el.terminalInput.value = state.history[next] ?? "";
  });

  // ------------------------------------------------------------------ Démarrage
  buildAxes();
  applyMode("text");
  renderSteps();
  updateGutter();
  logLine("Terminal : lance la CLI. Exemples : send --forward 150 2 · file scripts/demo.rbs · settings · -h · clear (Ctrl-C ou Arrêt pour interrompre)", "out info");
  guarded(async () => {
    await refreshScriptList();
    await loadSettings();
    await refreshStatus();
  });
  setInterval(refreshStatus, 450);
})();
