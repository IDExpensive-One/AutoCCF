import { api } from "../api.js";
import { router } from "../app.js";

let currentContainer = null;
let currentElements = null;
let currentLoadId = 0;
let activeTab = "posts";
let backHandler = null;
let tabHandlers = [];

function clearTabHandlers() {
  tabHandlers.forEach(({ element, handler }) => {
    element.removeEventListener("click", handler);
  });
  tabHandlers = [];
}

function renderPosts(posts) {
  const normalizedPosts = Array.isArray(posts) ? posts : [];
  if (!normalizedPosts.length) {
    return `
      <table class="table">
        <tbody>
          <tr><td colspan="3">暂无帖子数据</td></tr>
        </tbody>
      </table>
    `;
  }

  return `
    <table class="table">
      <thead>
        <tr>
          <th>标题</th>
          <th>贴吧</th>
          <th>链接</th>
        </tr>
      </thead>
      <tbody>
        ${normalizedPosts.map((post) => `
          <tr>
            <td>${post?.title || "-"}</td>
            <td>${post?.forum || "-"}</td>
            <td><a href="${post?.href || "#"}" target="_blank" rel="noreferrer">打开链接</a></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderThreads(threads) {
  const normalizedThreads = Array.isArray(threads) ? threads : [];
  if (!normalizedThreads.length) {
    return `
      <table class="table">
        <tbody>
          <tr><td colspan="3">暂无主题数据</td></tr>
        </tbody>
      </table>
    `;
  }

  return `
    <table class="table">
      <thead>
        <tr>
          <th>TID</th>
          <th>标题</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        ${normalizedThreads.map((thread) => `
          <tr>
            <td>${thread?.tid || "-"}</td>
            <td>${thread?.title || "-"}</td>
            <td>${thread?.status || "-"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderFiles(files) {
  const normalizedFiles = Array.isArray(files) ? files : [];
  if (!normalizedFiles.length) {
    return `
      <table class="table">
        <tbody>
          <tr><td colspan="3">暂无文件数据</td></tr>
        </tbody>
      </table>
    `;
  }

  return `
    <table class="table">
      <thead>
        <tr>
          <th>名称</th>
          <th>类型</th>
          <th>大小</th>
        </tr>
      </thead>
      <tbody>
        ${normalizedFiles.map((file) => `
          <tr>
            <td>${file?.is_dir ? `[目录] ${file?.name || "-"}` : file?.name || "-"}</td>
            <td>${file?.is_dir ? "目录" : "文件"}</td>
            <td>${file?.size_text || "-"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function updateTabVisibility() {
  if (!currentElements) {
    return;
  }

  const tabs = [
    { name: "posts", button: currentElements.postsTab, panel: currentElements.postsPanel },
    { name: "threads", button: currentElements.threadsTab, panel: currentElements.threadsPanel },
    { name: "files", button: currentElements.filesTab, panel: currentElements.filesPanel },
  ];

  tabs.forEach(({ name, button, panel }) => {
    const isActive = activeTab === name;
    button.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });
}

function showError(message) {
  if (!currentElements) {
    return;
  }

  currentElements.loading.hidden = true;
  currentElements.error.hidden = false;
  currentElements.error.textContent = message;
  currentElements.header.hidden = true;
}

function renderView(container) {
  container.innerHTML = `
    <div style="display: grid; gap: var(--space-lg);">
      <div>
        <button class="btn btn-secondary" type="button" data-user-detail-back>返回用户列表</button>
      </div>
      <p data-user-detail-loading>加载中...</p>
      <p data-user-detail-error hidden></p>
      <div data-user-detail-header hidden>
        <div class="card" style="margin-bottom: var(--space-lg);">
          <h3 class="card-title" data-user-detail-username></h3>
          <p data-user-detail-meta></p>
        </div>
        <div class="tab-bar" style="margin-bottom: var(--space-md);">
          <button class="tab-item active" type="button" data-tab="posts">帖子列表</button>
          <button class="tab-item" type="button" data-tab="threads">主题列表</button>
          <button class="tab-item" type="button" data-tab="files">文件浏览</button>
        </div>
        <div data-user-detail-posts></div>
        <div data-user-detail-threads hidden></div>
        <div data-user-detail-files hidden></div>
      </div>
    </div>
  `;

  currentElements = {
    backButton: container.querySelector("[data-user-detail-back]"),
    loading: container.querySelector("[data-user-detail-loading]"),
    error: container.querySelector("[data-user-detail-error]"),
    header: container.querySelector("[data-user-detail-header]"),
    username: container.querySelector("[data-user-detail-username]"),
    meta: container.querySelector("[data-user-detail-meta]"),
    postsTab: container.querySelector('[data-tab="posts"]'),
    threadsTab: container.querySelector('[data-tab="threads"]'),
    filesTab: container.querySelector('[data-tab="files"]'),
    postsPanel: container.querySelector("[data-user-detail-posts]"),
    threadsPanel: container.querySelector("[data-user-detail-threads]"),
    filesPanel: container.querySelector("[data-user-detail-files]"),
  };
}

async function loadDetail(username, loadId) {
  try {
    const result = await api.users.detail(username);
    if (loadId !== currentLoadId || !currentElements) {
      return;
    }

    if (result?.success === false) {
      showError(result?.message || "无法加载用户详情");
      return;
    }

    const posts = Array.isArray(result?.posts) ? result.posts : [];
    currentElements.loading.hidden = true;
    currentElements.error.hidden = true;
    currentElements.header.hidden = false;
    currentElements.username.textContent = result?.username || username;
    currentElements.meta.textContent = `帖子数 ${posts.length} | 目录 ${result?.user_dir || "-"}`;
    currentElements.postsPanel.innerHTML = renderPosts(result?.posts);
    currentElements.threadsPanel.innerHTML = renderThreads(result?.threads);
    currentElements.filesPanel.innerHTML = renderFiles(result?.files);
    updateTabVisibility();
  } catch (error) {
    if (loadId !== currentLoadId || !currentElements) {
      return;
    }

    showError(error?.message || "无法加载用户详情");
  }
}

function bindEvents() {
  backHandler = () => {
    void router.navigate("users");
  };
  currentElements.backButton.addEventListener("click", backHandler);

  [
    { name: "posts", element: currentElements.postsTab },
    { name: "threads", element: currentElements.threadsTab },
    { name: "files", element: currentElements.filesTab },
  ].forEach(({ name, element }) => {
    const handler = () => {
      activeTab = name;
      updateTabVisibility();
    };

    element.addEventListener("click", handler);
    tabHandlers.push({ element, handler });
  });
}

export async function mount(container, params = {}) {
  currentLoadId += 1;
  activeTab = "posts";
  currentContainer = container;
  renderView(container);
  bindEvents();

  if (!params?.username) {
    showError("缺少用户名参数");
    return;
  }

  await loadDetail(params.username, currentLoadId);
}

export function unmount() {
  currentLoadId += 1;

  if (currentElements?.backButton && backHandler) {
    currentElements.backButton.removeEventListener("click", backHandler);
  }

  clearTabHandlers();
  currentContainer = null;
  currentElements = null;
  activeTab = "posts";
  backHandler = null;
}
