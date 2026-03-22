import { api } from "../api.js";

let currentContainer = null;
let currentElements = null;
let currentRequestId = 0;
let currentConfig = createDefaultConfig();
let lastLoadedConfig = createDefaultConfig();
let draftAccount = null;
let statusState = { type: "", message: "" };
let isLoading = false;
let isSaving = false;
let clickHandler = null;
let inputHandler = null;

function createDefaultConfig() {
  return {
    database_dir: "./database",
    output_dir: "./database",
    accounts: [],
    apou: {
      page_delay: 2.0,
      max_retries: 3,
    },
    dopj: {
      threads: 3,
      max_retries: 3,
      min_interval: 2.0,
      max_fails: 5,
    },
  };
}

function cloneConfig(config) {
  return JSON.parse(JSON.stringify(config));
}

function normalizeConfig(rawConfig = {}) {
  const defaults = createDefaultConfig();
  const databaseDir = String(rawConfig.database_dir || rawConfig.output_dir || defaults.database_dir);
  const accounts = Array.isArray(rawConfig.accounts)
    ? rawConfig.accounts.map((account, index) => ({
        name: String(account?.name || `账户${index + 1}`),
        bduss: String(account?.bduss || ""),
      }))
    : [];

  return {
    database_dir: databaseDir,
    output_dir: databaseDir,
    accounts,
    apou: {
      page_delay: Number(rawConfig.apou?.page_delay ?? defaults.apou.page_delay),
      max_retries: Number(rawConfig.apou?.max_retries ?? defaults.apou.max_retries),
    },
    dopj: {
      threads: Number(rawConfig.dopj?.threads ?? defaults.dopj.threads),
      max_retries: Number(rawConfig.dopj?.max_retries ?? defaults.dopj.max_retries),
      min_interval: Number(rawConfig.dopj?.min_interval ?? defaults.dopj.min_interval),
      max_fails: Number(rawConfig.dopj?.max_fails ?? defaults.dopj.max_fails),
    },
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function previewBduss(bduss) {
  const normalized = String(bduss || "").trim();
  return normalized ? `${normalized.slice(0, 6)}...` : "未填写";
}

function renderStatusBadge() {
  if (!statusState.message) {
    return "";
  }

  const badgeClass = statusState.type === "success" ? "badge badge-success" : "badge badge-error";
  return `<span class="${badgeClass}">${escapeHtml(statusState.message)}</span>`;
}

function renderAccountRows() {
  const rows = [];

  currentConfig.accounts.forEach((account, index) => {
    const isEditing = draftAccount?.mode === "edit" && draftAccount.index === index;

    if (isEditing) {
      rows.push(`
        <tr>
          <td>
            <input
              class="input"
              type="text"
              data-account-name-input
              value="${escapeHtml(draftAccount.name)}"
              placeholder="账户名称"
              autocomplete="off"
            >
          </td>
          <td>
            <input
              class="input"
              type="text"
              data-account-bduss-input
              value="${escapeHtml(draftAccount.bduss)}"
              placeholder="输入 BDUSS"
              autocomplete="off"
            >
          </td>
          <td>
            <button class="btn btn-primary btn-sm" type="button" data-account-confirm>确认</button>
            <button class="btn btn-secondary btn-sm" type="button" data-account-cancel>取消</button>
          </td>
        </tr>
      `);
      return;
    }

    rows.push(`
      <tr>
        <td>${escapeHtml(account.name)}</td>
        <td>${escapeHtml(previewBduss(account.bduss))}</td>
        <td>
          <button class="btn btn-secondary btn-sm" type="button" data-account-edit="${index}">编辑</button>
          <button class="btn btn-danger btn-sm" type="button" data-account-delete="${index}">删除</button>
        </td>
      </tr>
    `);
  });

  if (currentConfig.accounts.length === 0) {
    rows.push(`
      <tr>
        <td colspan="3">暂无账户，请先添加。</td>
      </tr>
    `);
  }

  if (draftAccount?.mode === "add") {
    rows.push(`
      <tr>
        <td>
          <input
            class="input"
            type="text"
            data-account-name-input
            value="${escapeHtml(draftAccount.name)}"
            placeholder="账户名称"
            autocomplete="off"
          >
        </td>
        <td>
          <input
            class="input"
            type="text"
            data-account-bduss-input
            value="${escapeHtml(draftAccount.bduss)}"
            placeholder="输入 BDUSS"
            autocomplete="off"
          >
        </td>
        <td>
          <button class="btn btn-primary btn-sm" type="button" data-account-confirm>确认</button>
          <button class="btn btn-secondary btn-sm" type="button" data-account-cancel>取消</button>
        </td>
      </tr>
    `);
  }

  return rows.join("");
}

function syncCurrentElements(container) {
  currentElements = {
    databaseDirInput: container.querySelector("[data-database-dir]"),
    apouPageDelayValue: container.querySelector("[data-apou-page-delay-value]"),
    apouMaxRetriesValue: container.querySelector("[data-apou-max-retries-value]"),
    dopjThreadsValue: container.querySelector("[data-dopj-threads-value]"),
    dopjMaxRetriesValue: container.querySelector("[data-dopj-max-retries-value]"),
    dopjMinIntervalValue: container.querySelector("[data-dopj-min-interval-value]"),
    dopjMaxFailsValue: container.querySelector("[data-dopj-max-fails-value]"),
    accountNameInput: container.querySelector("[data-account-name-input]"),
    accountBdussInput: container.querySelector("[data-account-bduss-input]"),
    saveButton: container.querySelector("[data-save-settings]"),
    resetButton: container.querySelector("[data-reset-settings]"),
    selectDirectoryButton: container.querySelector("[data-select-directory]"),
    status: container.querySelector("[data-status]"),
  };
}

function renderView(container) {
  container.innerHTML = `
    <div style="display: grid; gap: var(--space-lg);">
      <div class="card">
        <h3 class="card-title">数据库目录</h3>
        <div class="form-group">
          <label for="settings-database-dir">当前目录</label>
          <input id="settings-database-dir" class="input" type="text" data-database-dir value="${escapeHtml(currentConfig.database_dir)}" readonly>
        </div>
        <button class="btn btn-secondary" type="button" data-select-directory ${isLoading || isSaving ? "disabled" : ""}>选择目录</button>
      </div>

      <div class="card">
        <h3 class="card-title">账户管理</h3>
        <table class="table">
          <thead>
            <tr>
              <th>名称</th>
              <th>BDUSS 预览</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody data-account-body>
            ${renderAccountRows()}
          </tbody>
        </table>
        <button class="btn btn-secondary" type="button" data-account-add ${draftAccount ? "disabled" : ""}>添加账户</button>
      </div>

      <div class="card">
        <h3 class="card-title">APoU 配置</h3>
        <div class="form-group">
          <label for="settings-apou-page-delay">page_delay: <span data-apou-page-delay-value>${escapeHtml(currentConfig.apou.page_delay.toFixed(1))}</span></label>
          <input id="settings-apou-page-delay" class="slider" type="range" min="0.5" max="10" step="0.5" value="${escapeHtml(currentConfig.apou.page_delay)}" data-apou-page-delay ${isLoading || isSaving ? "disabled" : ""}>
        </div>
        <div class="form-group">
          <label for="settings-apou-max-retries">max_retries: <span data-apou-max-retries-value>${escapeHtml(String(currentConfig.apou.max_retries))}</span></label>
          <input id="settings-apou-max-retries" class="slider" type="range" min="1" max="10" step="1" value="${escapeHtml(currentConfig.apou.max_retries)}" data-apou-max-retries ${isLoading || isSaving ? "disabled" : ""}>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">DoPJ 配置</h3>
        <div class="form-group">
          <label for="settings-dopj-threads">threads: <span data-dopj-threads-value>${escapeHtml(String(currentConfig.dopj.threads))}</span></label>
          <input id="settings-dopj-threads" class="slider" type="range" min="1" max="10" step="1" value="${escapeHtml(currentConfig.dopj.threads)}" data-dopj-threads ${isLoading || isSaving ? "disabled" : ""}>
        </div>
        <div class="form-group">
          <label for="settings-dopj-max-retries">max_retries: <span data-dopj-max-retries-value>${escapeHtml(String(currentConfig.dopj.max_retries))}</span></label>
          <input id="settings-dopj-max-retries" class="slider" type="range" min="1" max="10" step="1" value="${escapeHtml(currentConfig.dopj.max_retries)}" data-dopj-max-retries ${isLoading || isSaving ? "disabled" : ""}>
        </div>
        <div class="form-group">
          <label for="settings-dopj-min-interval">min_interval: <span data-dopj-min-interval-value>${escapeHtml(currentConfig.dopj.min_interval.toFixed(1))}</span></label>
          <input id="settings-dopj-min-interval" class="slider" type="range" min="0.5" max="10" step="0.5" value="${escapeHtml(currentConfig.dopj.min_interval)}" data-dopj-min-interval ${isLoading || isSaving ? "disabled" : ""}>
        </div>
        <div class="form-group">
          <label for="settings-dopj-max-fails">max_fails: <span data-dopj-max-fails-value>${escapeHtml(String(currentConfig.dopj.max_fails))}</span></label>
          <input id="settings-dopj-max-fails" class="slider" type="range" min="1" max="20" step="1" value="${escapeHtml(currentConfig.dopj.max_fails)}" data-dopj-max-fails ${isLoading || isSaving ? "disabled" : ""}>
        </div>
      </div>

      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-md);">
        <button class="btn btn-primary" type="button" data-save-settings ${isLoading || isSaving ? "disabled" : ""}>保存设置</button>
        <button class="btn btn-secondary" type="button" data-reset-settings ${isLoading || isSaving ? "disabled" : ""}>重置</button>
        <div data-status>${renderStatusBadge()}</div>
      </div>
    </div>
  `;

  syncCurrentElements(container);
}

function rerender() {
  if (!currentContainer) {
    return;
  }

  renderView(currentContainer);
}

function setStatus(type, message) {
  statusState = {
    type,
    message,
  };

  if (currentElements?.status) {
    currentElements.status.innerHTML = renderStatusBadge();
  }
}

function updateSliderLabel(key, value) {
  if (!currentElements) {
    return;
  }

  const elementMap = {
    apouPageDelay: currentElements.apouPageDelayValue,
    apouMaxRetries: currentElements.apouMaxRetriesValue,
    dopjThreads: currentElements.dopjThreadsValue,
    dopjMaxRetries: currentElements.dopjMaxRetriesValue,
    dopjMinInterval: currentElements.dopjMinIntervalValue,
    dopjMaxFails: currentElements.dopjMaxFailsValue,
  };

  if (elementMap[key]) {
    elementMap[key].textContent = value;
  }
}

function getSavePayload() {
  return {
    database_dir: currentConfig.database_dir,
    output_dir: currentConfig.database_dir,
    accounts: currentConfig.accounts.map((account) => ({
      name: account.name,
      bduss: account.bduss,
    })),
    apou: {
      page_delay: currentConfig.apou.page_delay,
      max_retries: currentConfig.apou.max_retries,
    },
    dopj: {
      threads: currentConfig.dopj.threads,
      max_retries: currentConfig.dopj.max_retries,
      min_interval: currentConfig.dopj.min_interval,
      max_fails: currentConfig.dopj.max_fails,
    },
  };
}

function beginDraft(mode, index = null) {
  if (mode === "edit" && index !== null) {
    const account = currentConfig.accounts[index];
    if (!account) {
      return;
    }

    draftAccount = {
      mode,
      index,
      name: account.name,
      bduss: account.bduss,
    };
    rerender();
    return;
  }

  draftAccount = {
    mode,
    index: null,
    name: "",
    bduss: "",
  };
  rerender();
}

function cancelDraft() {
  draftAccount = null;
  rerender();
}

function confirmDraft() {
  if (!draftAccount) {
    return;
  }

  const name = draftAccount.name.trim();
  const bduss = draftAccount.bduss.trim();
  if (!name || !bduss) {
    setStatus("error", "账户名称和 BDUSS 不能为空");
    return;
  }

  const nextAccount = { name, bduss };

  if (draftAccount.mode === "edit" && draftAccount.index !== null) {
    currentConfig.accounts[draftAccount.index] = nextAccount;
    setStatus("", "");
    draftAccount = null;
    rerender();
    return;
  }

  currentConfig.accounts.push(nextAccount);
  setStatus("", "");
  draftAccount = null;
  rerender();
}

async function loadConfig() {
  const requestId = ++currentRequestId;
  isLoading = true;
  draftAccount = null;
  setStatus("", "");
  rerender();

  try {
    const result = await api.config.load();
    if (requestId !== currentRequestId || !currentContainer) {
      return;
    }

    const normalized = normalizeConfig(result?.config);
    currentConfig = normalized;
    lastLoadedConfig = cloneConfig(normalized);
    setStatus("", "");
  } catch (error) {
    if (requestId !== currentRequestId || !currentContainer) {
      return;
    }

    setStatus("error", error?.message || "无法加载设置");
  } finally {
    if (requestId !== currentRequestId || !currentContainer) {
      return;
    }

    isLoading = false;
    rerender();
  }
}

async function saveConfig() {
  if (isLoading || isSaving) {
    return;
  }

  if (draftAccount) {
    setStatus("error", "请先完成当前账户编辑");
    return;
  }

  const requestId = ++currentRequestId;
  isSaving = true;
  setStatus("", "");
  rerender();

  try {
    await api.config.save(getSavePayload());
    if (requestId !== currentRequestId || !currentContainer) {
      return;
    }

    lastLoadedConfig = cloneConfig(currentConfig);
    setStatus("success", "设置已保存");
  } catch (error) {
    if (requestId !== currentRequestId || !currentContainer) {
      return;
    }

    setStatus("error", error?.message || "保存设置失败");
  } finally {
    if (requestId !== currentRequestId || !currentContainer) {
      return;
    }

    isSaving = false;
    rerender();
  }
}

async function handleSelectDirectory() {
  if (isLoading || isSaving) {
    return;
  }

  try {
    const selectedDirectory = await window.api.selectDirectory();
    if (!selectedDirectory || !currentContainer) {
      return;
    }

    currentConfig.database_dir = selectedDirectory;
    currentConfig.output_dir = selectedDirectory;

    if (currentElements?.databaseDirInput) {
      currentElements.databaseDirInput.value = selectedDirectory;
    }
  } catch (error) {
    if (!currentContainer) {
      return;
    }

    setStatus("error", error?.message || "无法选择目录");
  }
}

function handleDeleteAccount(index) {
  const numericIndex = Number(index);
  if (Number.isNaN(numericIndex)) {
    return;
  }

  currentConfig.accounts.splice(numericIndex, 1);
  if (draftAccount?.mode === "edit" && draftAccount.index === numericIndex) {
    draftAccount = null;
  }
  setStatus("", "");
  rerender();
}

function handleContainerClick(event) {
  const target = event.target.closest("button");
  if (!target || isLoading) {
    return;
  }

  if (target.hasAttribute("data-select-directory")) {
    void handleSelectDirectory();
    return;
  }

  if (target.hasAttribute("data-account-add")) {
    beginDraft("add");
    return;
  }

  if (target.hasAttribute("data-account-confirm")) {
    confirmDraft();
    return;
  }

  if (target.hasAttribute("data-account-cancel")) {
    cancelDraft();
    return;
  }

  if (target.hasAttribute("data-account-edit")) {
    beginDraft("edit", Number(target.dataset.accountEdit));
    return;
  }

  if (target.hasAttribute("data-account-delete")) {
    handleDeleteAccount(target.dataset.accountDelete);
    return;
  }

  if (target.hasAttribute("data-save-settings")) {
    void saveConfig();
    return;
  }

  if (target.hasAttribute("data-reset-settings")) {
    currentConfig = cloneConfig(lastLoadedConfig);
    draftAccount = null;
    setStatus("", "");
    void loadConfig();
  }
}

function handleContainerInput(event) {
  const target = event.target;

  if (target.matches("[data-account-name-input]")) {
    if (draftAccount) {
      draftAccount.name = target.value;
    }
    return;
  }

  if (target.matches("[data-account-bduss-input]")) {
    if (draftAccount) {
      draftAccount.bduss = target.value;
    }
    return;
  }

  if (target.matches("[data-apou-page-delay]")) {
    currentConfig.apou.page_delay = Number(target.value);
    updateSliderLabel("apouPageDelay", currentConfig.apou.page_delay.toFixed(1));
    return;
  }

  if (target.matches("[data-apou-max-retries]")) {
    currentConfig.apou.max_retries = Number(target.value);
    updateSliderLabel("apouMaxRetries", String(currentConfig.apou.max_retries));
    return;
  }

  if (target.matches("[data-dopj-threads]")) {
    currentConfig.dopj.threads = Number(target.value);
    updateSliderLabel("dopjThreads", String(currentConfig.dopj.threads));
    return;
  }

  if (target.matches("[data-dopj-max-retries]")) {
    currentConfig.dopj.max_retries = Number(target.value);
    updateSliderLabel("dopjMaxRetries", String(currentConfig.dopj.max_retries));
    return;
  }

  if (target.matches("[data-dopj-min-interval]")) {
    currentConfig.dopj.min_interval = Number(target.value);
    updateSliderLabel("dopjMinInterval", currentConfig.dopj.min_interval.toFixed(1));
    return;
  }

  if (target.matches("[data-dopj-max-fails]")) {
    currentConfig.dopj.max_fails = Number(target.value);
    updateSliderLabel("dopjMaxFails", String(currentConfig.dopj.max_fails));
  }
}

export async function mount(container, params = {}) {
  void params;
  currentContainer = container;
  currentConfig = createDefaultConfig();
  lastLoadedConfig = createDefaultConfig();
  draftAccount = null;
  statusState = { type: "", message: "" };
  isLoading = false;
  isSaving = false;

  renderView(container);

  clickHandler = (event) => {
    handleContainerClick(event);
  };
  inputHandler = (event) => {
    handleContainerInput(event);
  };

  currentContainer.addEventListener("click", clickHandler);
  currentContainer.addEventListener("input", inputHandler);

  await loadConfig();
}

export function unmount() {
  currentRequestId += 1;

  if (currentContainer && clickHandler) {
    currentContainer.removeEventListener("click", clickHandler);
  }

  if (currentContainer && inputHandler) {
    currentContainer.removeEventListener("input", inputHandler);
  }

  currentContainer = null;
  currentElements = null;
  draftAccount = null;
  clickHandler = null;
  inputHandler = null;
  isLoading = false;
  isSaving = false;
}
