import { api } from "../api.js";
import { router } from "../app.js";

let currentContainer = null;
let currentElements = null;
let currentUsers = [];
let currentLoadId = 0;
let searchHandler = null;
let actionHandlers = [];

function clearActionHandlers() {
  actionHandlers.forEach(({ element, handler }) => {
    element.removeEventListener("click", handler);
  });
  actionHandlers = [];
}

function renderRows(users) {
  if (!currentElements?.tableBody) {
    return;
  }

  clearActionHandlers();

  const normalizedUsers = Array.isArray(users) ? users : [];
  if (normalizedUsers.length === 0) {
    currentElements.tableBody.innerHTML = `
      <tr>
        <td colspan="4">暂无匹配用户</td>
      </tr>
    `;
    return;
  }

  currentElements.tableBody.innerHTML = normalizedUsers.map((user) => {
    const username = user?.name || "未命名用户";
    const postsCount = Number(user?.posts_count) || 0;
    const status = postsCount > 0
      ? '<span class="badge badge-success">已完成</span>'
      : '<span class="badge">暂无帖子</span>';

    return `
      <tr>
        <td>${username}</td>
        <td>${postsCount}</td>
        <td>${status}</td>
        <td>
          <button class="btn btn-secondary" type="button" data-user-action="${username}">查看详情</button>
        </td>
      </tr>
    `;
  }).join("");

  normalizedUsers.forEach((user) => {
    const username = user?.name || "";
    const button = currentContainer?.querySelector(`[data-user-action="${username}"]`);
    if (!button) {
      return;
    }

    const handler = () => {
      void router.navigate("user-detail", { username });
    };

    button.addEventListener("click", handler);
    actionHandlers.push({ element: button, handler });
  });
}

function applyFilter() {
  const keyword = String(currentElements?.searchInput?.value || "").trim().toLowerCase();
  const filteredUsers = currentUsers.filter((user) => String(user?.name || "").toLowerCase().includes(keyword));
  renderRows(filteredUsers);
}

function showLoading(message) {
  if (!currentElements?.loading || !currentElements?.error) {
    return;
  }

  currentElements.loading.hidden = false;
  currentElements.loading.textContent = message;
  currentElements.error.hidden = true;
  currentElements.error.textContent = "";
}

function showError(message) {
  if (!currentElements?.loading || !currentElements?.error || !currentElements?.tableBody) {
    return;
  }

  currentElements.loading.hidden = true;
  currentElements.error.hidden = false;
  currentElements.error.textContent = message;
  currentElements.tableBody.innerHTML = `
    <tr>
      <td colspan="4">加载失败</td>
    </tr>
  `;
}

function renderView(container) {
  container.innerHTML = `
    <div class="card">
      <h3 class="card-title">用户列表</h3>
      <div class="form-group" style="margin-bottom: var(--space-md);">
        <input class="input" type="text" placeholder="搜索用户..." data-users-search autocomplete="off">
      </div>
      <p data-users-loading>加载中...</p>
      <p data-users-error hidden></p>
      <table class="table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>帖子数</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody data-users-body>
          <tr>
            <td colspan="4">加载中...</td>
          </tr>
        </tbody>
      </table>
    </div>
  `;

  currentElements = {
    searchInput: container.querySelector("[data-users-search]"),
    loading: container.querySelector("[data-users-loading]"),
    error: container.querySelector("[data-users-error]"),
    tableBody: container.querySelector("[data-users-body]"),
  };
}

async function loadUsers(loadId) {
  showLoading("加载中...");

  try {
    const result = await api.users.list();
    if (loadId !== currentLoadId || !currentElements) {
      return;
    }

    if (result?.success === false) {
      showError(result?.message || "无法加载用户列表");
      return;
    }

    currentUsers = Array.isArray(result?.users) ? result.users : [];
    currentElements.loading.hidden = true;
    applyFilter();
  } catch (error) {
    if (loadId !== currentLoadId || !currentElements) {
      return;
    }

    showError(error?.message || "无法加载用户列表");
  }
}

export async function mount(container, params = {}) {
  void params;
  currentLoadId += 1;
  currentContainer = container;
  currentUsers = [];
  renderView(container);

  searchHandler = () => {
    applyFilter();
  };

  currentElements.searchInput.addEventListener("input", searchHandler);
  await loadUsers(currentLoadId);
}

export function unmount() {
  currentLoadId += 1;

  if (currentElements?.searchInput && searchHandler) {
    currentElements.searchInput.removeEventListener("input", searchHandler);
  }

  clearActionHandlers();
  currentContainer = null;
  currentElements = null;
  currentUsers = [];
  searchHandler = null;
}
