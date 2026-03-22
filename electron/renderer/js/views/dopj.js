import { api } from "../api.js";

let currentContainer = null;
let currentElements = null;
let currentRunId = 0;
let selectedPath = "";
let formSubmitHandler = null;
let selectChangeHandler = null;

function cleanupListeners() {
  api.removeAllListeners("bridge:progress");
  api.removeAllListeners("bridge:log");
}

function maskBduss(bduss) {
  const normalized = String(bduss || "").trim();
  return normalized ? `${normalized.slice(0, 6)}...` : "未配置";
}

function renderStatusBadge(type, message) {
  if (!currentElements?.status) {
    return;
  }

  if (!message) {
    currentElements.status.innerHTML = "";
    return;
  }

  const badgeClassMap = {
    success: "badge badge-success",
    error: "badge badge-error",
    warning: "badge badge-warning",
  };

  const badgeClass = badgeClassMap[type] || badgeClassMap.warning;
  currentElements.status.innerHTML = `<span class="${badgeClass}">${message}</span>`;
}

function appendLog(message, level = "info") {
  if (!currentElements?.logViewer) {
    return;
  }

  const line = document.createElement("div");
  line.textContent = `[${String(level || "info").toUpperCase()}] ${message}`;
  currentElements.logViewer.append(line);
  currentElements.logViewer.scrollTop = currentElements.logViewer.scrollHeight;
}

function updateProgress(progress = {}) {
  if (!currentElements?.progressFill || !currentElements?.progressText) {
    return;
  }

  const success = Number(progress.success) || 0;
  const failed = Number(progress.failed) || 0;
  const skipped = Number(progress.skipped) || 0;
  const total = Number(progress.total) || 0;
  const completed = success + failed + skipped;
  const percentage = total > 0 ? Math.min(100, Math.max(0, (completed / total) * 100)) : 0;

  currentElements.progressFill.style.width = `${percentage}%`;
  currentElements.progressText.textContent = `成功 ${success} / 失败 ${failed} / 跳过 ${skipped} / 总计 ${total}`;
}

function renderOutputs(outputs) {
  if (!currentElements?.userSelect) {
    return;
  }

  const normalizedOutputs = Array.isArray(outputs) ? outputs : [];
  const options = ['<option value="">请选择 APoU 输出</option>'];

  normalizedOutputs.forEach((output) => {
    const username = output?.username || "未命名用户";
    const path = output?.path || "";
    const postsCount = Number(output?.posts_count) || 0;
    const selected = path && path === selectedPath ? ' selected' : "";
    options.push(
      `<option value="${path}"${selected}>${username} (${postsCount} 条帖子)</option>`,
    );
  });

  currentElements.userSelect.innerHTML = options.join("");
  currentElements.userSelect.disabled = normalizedOutputs.length === 0;

  if (!selectedPath && normalizedOutputs.length > 0) {
    selectedPath = normalizedOutputs[0].path || "";
    currentElements.userSelect.value = selectedPath;
  }
}

function renderAccounts(accounts) {
  if (!currentElements?.accountBody) {
    return;
  }

  const normalizedAccounts = Array.isArray(accounts) ? accounts : [];

  if (normalizedAccounts.length === 0) {
    currentElements.accountBody.innerHTML = `
      <tr>
        <td colspan="2">暂无已配置账户</td>
      </tr>
    `;
    return;
  }

  currentElements.accountBody.innerHTML = normalizedAccounts.map((account) => {
    const name = account?.name || "未命名账户";
    const bdussPreview = maskBduss(account?.bduss);

    return `
      <tr>
        <td>
          <div>${name}</div>
          <div style="margin-top: var(--space-xs); color: var(--color-text-secondary);">${bdussPreview}</div>
        </td>
        <td><span class="badge badge-success">就绪</span></td>
      </tr>
    `;
  }).join("");
}

function renderView(container) {
  container.innerHTML = `
    <div class="card" style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">开始 DoPJ 爬取</h3>
      <form data-dopj-form style="display: grid; gap: var(--space-md);">
        <div class="form-group">
          <label for="dopj-user-select">选择 APoU 输出</label>
          <select id="dopj-user-select" class="select" data-user-select>
            <option value="">加载中...</option>
          </select>
        </div>
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-md);">
          <button class="btn btn-primary" type="submit" data-start-crawl>开始爬取</button>
          <div data-status></div>
        </div>
      </form>
    </div>

    <div class="card" style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">账户状态</h3>
      <table class="table">
        <thead>
          <tr>
            <th>账户名</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody data-account-body>
          <tr>
            <td colspan="2">加载中...</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" data-progress-card hidden style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">爬取进度</h3>
      <div class="progress-bar" style="margin-bottom: var(--space-md);">
        <div class="progress-bar-fill" data-progress-fill style="width: 0%;"></div>
      </div>
      <p data-progress-text>成功 0 / 失败 0 / 跳过 0 / 总计 0</p>
    </div>

    <div class="card" data-log-card hidden>
      <h3 class="card-title">运行日志</h3>
      <div class="log-viewer" data-log-viewer></div>
    </div>
  `;

  currentElements = {
    form: container.querySelector("[data-dopj-form]"),
    userSelect: container.querySelector("[data-user-select]"),
    startButton: container.querySelector("[data-start-crawl]"),
    status: container.querySelector("[data-status]"),
    accountBody: container.querySelector("[data-account-body]"),
    progressCard: container.querySelector("[data-progress-card]"),
    progressFill: container.querySelector("[data-progress-fill]"),
    progressText: container.querySelector("[data-progress-text]"),
    logCard: container.querySelector("[data-log-card]"),
    logViewer: container.querySelector("[data-log-viewer]"),
  };
}

async function loadOutputs() {
  try {
    const result = await api.apou.outputs();
    if (!currentElements) {
      return;
    }

    renderOutputs(result?.outputs);
    if (!Array.isArray(result?.outputs) || result.outputs.length === 0) {
      renderStatusBadge("warning", "暂无可用的 APoU 输出");
    }
  } catch (error) {
    if (!currentElements?.userSelect) {
      return;
    }

    currentElements.userSelect.innerHTML = '<option value="">加载失败</option>';
    currentElements.userSelect.disabled = true;
    renderStatusBadge("error", error?.message || "无法加载 APoU 输出");
  }
}

async function loadAccounts() {
  try {
    const result = await api.config.load();
    if (!currentElements) {
      return;
    }

    renderAccounts(result?.config?.accounts);
  } catch (error) {
    if (!currentElements?.accountBody) {
      return;
    }

    currentElements.accountBody.innerHTML = `
      <tr>
        <td colspan="2">${error?.message || "无法加载账户配置"}</td>
      </tr>
    `;
  }
}

async function handleSubmit(event) {
  event.preventDefault();

  if (!currentElements?.startButton || !currentElements?.userSelect) {
    return;
  }

  if (!selectedPath) {
    renderStatusBadge("warning", "请先选择 APoU 输出");
    currentElements.userSelect.focus();
    return;
  }

  currentRunId += 1;
  const runId = currentRunId;

  cleanupListeners();
  renderStatusBadge("", "");
  currentElements.startButton.disabled = true;
  currentElements.progressCard.hidden = false;
  currentElements.logCard.hidden = false;
  currentElements.logViewer.textContent = "";
  updateProgress({ success: 0, failed: 0, skipped: 0, total: 0 });
  appendLog("DoPJ 爬虫已启动", "info");

  api.onProgress((data) => {
    if (runId !== currentRunId || !currentContainer || !currentElements) {
      return;
    }

    updateProgress(data);
    if (data?.message) {
      appendLog(data.message, "info");
    }
  });

  api.onLog((data) => {
    if (runId !== currentRunId || !currentContainer || !currentElements) {
      return;
    }

    appendLog(data?.message || "收到新的日志", data?.level);
  });

  try {
    const result = await api.dopj.crawl(selectedPath);
    if (runId !== currentRunId || !currentContainer || !currentElements) {
      return;
    }

    const success = result?.success !== false;
    const message = result?.message || (success ? "爬取完成" : "爬取失败");
    renderStatusBadge(success ? "success" : "error", message);
    appendLog(message, success ? "success" : "error");
  } catch (error) {
    if (runId !== currentRunId || !currentContainer || !currentElements) {
      return;
    }

    const message = error?.message || "DoPJ 爬取失败";
    renderStatusBadge("error", message);
    appendLog(message, "error");
  } finally {
    cleanupListeners();
    if (runId === currentRunId && currentElements?.startButton) {
      currentElements.startButton.disabled = false;
    }
  }
}

export async function mount(container, params = {}) {
  void params;
  currentContainer = container;
  selectedPath = "";
  renderView(container);

  formSubmitHandler = (event) => {
    void handleSubmit(event);
  };
  selectChangeHandler = (event) => {
    selectedPath = event.target.value;
  };

  currentElements.form.addEventListener("submit", formSubmitHandler);
  currentElements.userSelect.addEventListener("change", selectChangeHandler);

  await Promise.all([loadOutputs(), loadAccounts()]);
}

export function unmount() {
  currentRunId += 1;

  if (currentElements?.form && formSubmitHandler) {
    currentElements.form.removeEventListener("submit", formSubmitHandler);
  }

  if (currentElements?.userSelect && selectChangeHandler) {
    currentElements.userSelect.removeEventListener("change", selectChangeHandler);
  }

  cleanupListeners();
  currentContainer = null;
  currentElements = null;
  selectedPath = "";
  formSubmitHandler = null;
  selectChangeHandler = null;
}
