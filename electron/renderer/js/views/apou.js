import { api } from "../api.js";

let currentContainer = null;
let submitHandler = null;
let activeRunId = 0;
let indeterminateTimer = null;
let currentElements = null;

function cleanupListeners() {
  api.removeAllListeners("bridge:progress");
  api.removeAllListeners("bridge:log");
}

function stopIndeterminateAnimation() {
  if (indeterminateTimer) {
    clearInterval(indeterminateTimer);
    indeterminateTimer = null;
  }

  if (currentElements?.progressFill) {
    currentElements.progressFill.style.width = "40%";
  }
}

function startIndeterminateAnimation() {
  stopIndeterminateAnimation();

  if (!currentElements?.progressFill) {
    return;
  }

  const widths = ["28%", "52%", "74%", "43%"];
  let index = 0;
  currentElements.progressFill.style.width = widths[index];

  indeterminateTimer = setInterval(() => {
    if (!currentElements?.progressFill) {
      stopIndeterminateAnimation();
      return;
    }

    index = (index + 1) % widths.length;
    currentElements.progressFill.style.width = widths[index];
  }, 450);
}

function setStatusBadge(type, message) {
  if (!currentElements?.status) {
    return;
  }

  if (!message) {
    currentElements.status.innerHTML = "";
    return;
  }

  const badgeClass = type === "error" ? "badge badge-error" : "badge badge-success";
  currentElements.status.innerHTML = `<span class="${badgeClass}">${message}</span>`;
}

function appendLog(message, level = "info") {
  if (!currentElements?.logViewer) {
    return;
  }

  const line = document.createElement("div");
  const normalizedLevel = String(level || "info").toUpperCase();
  line.textContent = `[${normalizedLevel}] ${message}`;
  currentElements.logViewer.append(line);
  currentElements.logViewer.scrollTop = currentElements.logViewer.scrollHeight;
}

function renderView(container) {
  container.innerHTML = `
    <div class="card" style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">开始 APoU 爬取</h3>
      <form data-apou-form style="display: grid; gap: var(--space-md);">
        <div class="form-group">
          <label for="apou-username">贴吧用户名</label>
          <input id="apou-username" class="input" name="username" type="text" placeholder="输入要爬取的用户名" autocomplete="off">
        </div>
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-md);">
          <button class="btn btn-primary" type="submit" data-start-crawl>开始爬取</button>
          <div data-status></div>
        </div>
      </form>
    </div>

    <div class="card" data-progress-card hidden style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">爬取进度</h3>
      <div class="progress-bar" style="margin-bottom: var(--space-md);">
        <div class="progress-bar-fill" data-progress-fill style="width: 40%;"></div>
      </div>
      <p data-progress-text>等待开始...</p>
      <p data-page-text style="margin-top: var(--space-sm); color: var(--color-text-secondary);">准备中...</p>
    </div>

    <div class="card" data-log-card hidden>
      <h3 class="card-title">运行日志</h3>
      <div class="log-viewer" data-log-viewer></div>
    </div>
  `;

  currentElements = {
    form: container.querySelector("[data-apou-form]"),
    usernameInput: container.querySelector("#apou-username"),
    startButton: container.querySelector("[data-start-crawl]"),
    status: container.querySelector("[data-status]"),
    progressCard: container.querySelector("[data-progress-card]"),
    progressFill: container.querySelector("[data-progress-fill]"),
    progressText: container.querySelector("[data-progress-text]"),
    pageText: container.querySelector("[data-page-text]"),
    logCard: container.querySelector("[data-log-card]"),
    logViewer: container.querySelector("[data-log-viewer]"),
  };
}

async function handleSubmit(event) {
  event.preventDefault();

  if (!currentElements?.usernameInput || !currentElements?.startButton) {
    return;
  }

  const username = currentElements.usernameInput.value.trim();
  if (!username) {
    setStatusBadge("error", "请输入贴吧用户名");
    currentElements.usernameInput.focus();
    return;
  }

  activeRunId += 1;
  const runId = activeRunId;
  let latestPostsCount = 0;

  cleanupListeners();
  setStatusBadge("", "");
  currentElements.startButton.disabled = true;
  currentElements.progressCard.hidden = false;
  currentElements.logCard.hidden = false;
  currentElements.logViewer.textContent = "";
  currentElements.progressText.textContent = "已爬取 0 条帖子";
  currentElements.pageText.textContent = "正在启动 APoU 爬虫...";
  startIndeterminateAnimation();

  api.onProgress((data) => {
    if (runId !== activeRunId || !currentContainer || !currentElements) {
      return;
    }

    latestPostsCount = Number(data?.posts_count) || 0;
    const page = Number(data?.page) || 0;
    currentElements.progressText.textContent = `已爬取 ${latestPostsCount} 条帖子`;
    currentElements.pageText.textContent = page > 0 ? `正在处理第 ${page} 页` : "正在处理中...";
  });

  api.onLog((data) => {
    if (runId !== activeRunId || !currentContainer || !currentElements) {
      return;
    }

    appendLog(data?.message || "收到新的日志", data?.level);
  });

  try {
    const result = await api.apou.crawl(username);
    if (runId !== activeRunId || !currentContainer || !currentElements) {
      return;
    }

    const finalPostsCount = Number(result?.posts_count) || latestPostsCount;
    currentElements.progressText.textContent = `已爬取 ${finalPostsCount} 条帖子`;
    currentElements.pageText.textContent = "爬取完成";
    setStatusBadge("success", `爬取完成，共获取 ${finalPostsCount} 条帖子`);
    appendLog(`APoU 爬取完成，共获取 ${finalPostsCount} 条帖子`, "success");
  } catch (error) {
    if (runId !== activeRunId || !currentContainer || !currentElements) {
      return;
    }

    const message = error?.message || "APoU 爬取失败";
    currentElements.pageText.textContent = "爬取失败";
    setStatusBadge("error", message);
    appendLog(message, "error");
  } finally {
    cleanupListeners();
    stopIndeterminateAnimation();

    if (runId === activeRunId && currentElements?.startButton) {
      currentElements.startButton.disabled = false;
    }
  }
}

export function mount(container, params = {}) {
  void params;
  currentContainer = container;
  renderView(container);

  submitHandler = (event) => {
    void handleSubmit(event);
  };

  currentElements.form.addEventListener("submit", submitHandler);
}

export function unmount() {
  activeRunId += 1;

  if (currentElements?.form && submitHandler) {
    currentElements.form.removeEventListener("submit", submitHandler);
  }

  cleanupListeners();
  stopIndeterminateAnimation();
  currentContainer = null;
  currentElements = null;
  submitHandler = null;
}
