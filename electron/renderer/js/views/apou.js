import { api } from "../api.js";

let currentContainer = null;
let submitHandler = null;
let activeRunId = 0;
let loadingTimer = null;
let currentElements = null;

function cleanupListeners() {
  api.removeAllListeners("bridge:progress");
  api.removeAllListeners("bridge:log");
}

function stopLoadingIndicator() {
  if (loadingTimer) {
    clearInterval(loadingTimer);
    loadingTimer = null;
  }
}

function startLoadingIndicator() {
  stopLoadingIndicator();

  if (!currentElements?.loadingText) {
    return;
  }

  const frames = ["加载中", "加载中.", "加载中..", "加载中..."];
  let index = 0;
  currentElements.loadingText.textContent = frames[index];

  loadingTimer = setInterval(() => {
    if (!currentElements?.loadingText) {
      stopLoadingIndicator();
      return;
    }

    index = (index + 1) % frames.length;
    currentElements.loadingText.textContent = frames[index];
  }, 400);
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

async function getExistingPostsCount(username) {
  try {
    const result = await api.apou.outputs();
    const outputs = Array.isArray(result?.outputs) ? result.outputs : [];
    const found = outputs.find((item) => item?.username === username);
    return Number(found?.posts_count) || 0;
  } catch {
    return 0;
  }
}

function renderView(container) {
  container.innerHTML = `
    <div class="card" style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">开始 APoU 抓取</h3>
      <form data-apou-form style="display: grid; gap: var(--space-md);">
        <div class="form-group">
          <label for="apou-username">贴吧用户名</label>
          <input id="apou-username" class="input" name="username" type="text" placeholder="输入要抓取的用户名" autocomplete="off">
        </div>
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-md);">
          <button class="btn btn-primary" type="submit" data-start-crawl>开始抓取</button>
          <div data-status></div>
        </div>
      </form>
    </div>

    <div class="card" data-progress-card hidden style="margin-bottom: var(--space-lg);">
      <h3 class="card-title">抓取状态</h3>
      <p data-loading-text data-loading-indicator style="margin-bottom: var(--space-sm); color: var(--color-text-secondary);">加载中...</p>
      <p data-progress-text>已爬取 0 条帖子</p>
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
    loadingText: container.querySelector("[data-loading-text]"),
    progressText: container.querySelector("[data-progress-text]"),
    pageText: container.querySelector("[data-page-text]"),
    logCard: container.querySelector("[data-log-card]"),
    logViewer: container.querySelector("[data-log-viewer]"),
  };
}

function resolveTotalCount({
  progressData,
  fallbackBase,
  fallbackAccumulated,
}) {
  const reportedTotal = Number(progressData?.posts_count);
  if (Number.isFinite(reportedTotal) && reportedTotal >= 0) {
    return {
      total: reportedTotal,
      accumulated: fallbackAccumulated,
    };
  }

  const delta = Number(progressData?.delta_posts_count);
  const safeDelta = Number.isFinite(delta) && delta >= 0 ? delta : (Number(progressData?.posts_count) || 0);
  const nextAccumulated = fallbackAccumulated + safeDelta;
  return {
    total: fallbackBase + nextAccumulated,
    accumulated: nextAccumulated,
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
  const basePostsCount = await getExistingPostsCount(username);
  let latestPostsCount = basePostsCount;
  let accumulatedDelta = 0;

  if (runId !== activeRunId || !currentContainer || !currentElements) {
    return;
  }

  cleanupListeners();
  setStatusBadge("", "");
  currentElements.startButton.disabled = true;
  currentElements.progressCard.hidden = false;
  currentElements.logCard.hidden = false;
  currentElements.logViewer.textContent = "";
  currentElements.loadingText.textContent = "加载中...";
  currentElements.progressText.textContent = `已爬取 ${basePostsCount} 条帖子`;
  currentElements.pageText.textContent = "正在启动 APoU 爬虫...";
  startLoadingIndicator();

  api.onProgress((data) => {
    if (runId !== activeRunId || !currentContainer || !currentElements) {
      return;
    }

    const resolved = resolveTotalCount({
      progressData: data,
      fallbackBase: basePostsCount,
      fallbackAccumulated: accumulatedDelta,
    });
    latestPostsCount = resolved.total;
    accumulatedDelta = resolved.accumulated;

    const page = Number(data?.page) || 0;
    currentElements.progressText.textContent = `已爬取 ${latestPostsCount} 条帖子`;
    currentElements.pageText.textContent = page > 0 ? `正在处理第 ${page} 步` : "正在处理中...";
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

    const finalPostsCount = Number(result?.posts_count);
    if (Number.isFinite(finalPostsCount) && finalPostsCount >= 0) {
      latestPostsCount = finalPostsCount;
    }

    const resultNewCount = Number(result?.new_posts_count);
    const newPostsCount = Number.isFinite(resultNewCount) && resultNewCount >= 0
      ? resultNewCount
      : Math.max(0, latestPostsCount - basePostsCount);

    currentElements.loadingText.textContent = "已完成";
    currentElements.progressText.textContent = `已爬取 ${latestPostsCount} 条帖子`;
    currentElements.pageText.textContent = "爬取完成";
    setStatusBadge("success", `爬取完成，累计 ${latestPostsCount} 条（本次新增 ${newPostsCount} 条）`);
    appendLog(`APoU 爬取完成，累计 ${latestPostsCount} 条，本次新增 ${newPostsCount} 条`, "success");
  } catch (error) {
    if (runId !== activeRunId || !currentContainer || !currentElements) {
      return;
    }

    const message = error?.message || "APoU 抓取失败";
    currentElements.loadingText.textContent = "加载失败";
    currentElements.pageText.textContent = "抓取失败";
    setStatusBadge("error", message);
    appendLog(message, "error");
  } finally {
    cleanupListeners();
    stopLoadingIndicator();

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
  stopLoadingIndicator();
  currentContainer = null;
  currentElements = null;
  submitHandler = null;
}
