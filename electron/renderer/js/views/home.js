import { api } from "../api.js";
import { router } from "../app.js";

let currentContainer = null;
let currentRequestId = 0;
let clickHandler = null;

function formatRelativeTime(timestamp) {
  if (!timestamp) return "无记录";
  const diff = Date.now() / 1000 - timestamp;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
  return `${Math.floor(diff / 86400)}天前`;
}

function extractUsers(result) {
  if (Array.isArray(result)) {
    return result;
  }

  if (Array.isArray(result?.users)) {
    return result.users;
  }

  return [];
}

function renderState(content) {
  if (!currentContainer) {
    return;
  }

  currentContainer.innerHTML = content;
}

function renderLoading() {
  renderState(`
    <div class="card">
      <h3 class="card-title">首页概览</h3>
      <p>加载中...</p>
    </div>
  `);
}

function renderError(message) {
  renderState(`
    <div class="card">
      <h3 class="card-title">首页概览</h3>
      <p>加载失败：${message}</p>
    </div>
  `);
}

function renderHome(users) {
  const totalUsers = users.length;
  const totalPosts = users.reduce((sum, user) => sum + (user.posts_count || 0), 0);
  const latestActivity = users.reduce((latest, user) => {
    if (!user.last_activity) {
      return latest;
    }

    return latest && latest > user.last_activity ? latest : user.last_activity;
  }, null);

  renderState(`
    <div style="display: flex; flex-wrap: wrap; gap: var(--space-lg); margin-bottom: var(--space-lg);">
      <div class="card stat-card" style="flex: 1 1 220px; min-width: 220px;">
        <h3 class="card-title">已爬取用户</h3>
        <p>${totalUsers}</p>
      </div>
      <div class="card stat-card" style="flex: 1 1 220px; min-width: 220px;">
        <h3 class="card-title">帖子总数</h3>
        <p>${totalPosts}</p>
      </div>
      <div class="card stat-card" style="flex: 1 1 220px; min-width: 220px;">
        <h3 class="card-title">最近活动</h3>
        <p>${formatRelativeTime(latestActivity)}</p>
      </div>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: var(--space-lg);">
      <div class="card" style="flex: 1 1 320px; min-width: 280px;">
        <h3 class="card-title">开始 APoU</h3>
        <p style="margin-bottom: var(--space-md);">快速获取用户发言列表</p>
        <button class="btn btn-primary" data-nav="apou">进入 APoU</button>
      </div>
      <div class="card" style="flex: 1 1 320px; min-width: 280px;">
        <h3 class="card-title">开始 DoPJ</h3>
        <p style="margin-bottom: var(--space-md);">获取帖子完整内容</p>
        <button class="btn btn-primary" data-nav="dopj">进入 DoPJ</button>
      </div>
    </div>
  `);
}

export async function mount(container) {
  currentContainer = container;
  currentRequestId += 1;
  const requestId = currentRequestId;

  clickHandler = (event) => {
    const button = event.target.closest("[data-nav]");
    if (!button || !router) {
      return;
    }

    const targetView = button.dataset.nav;
    if (targetView) {
      void router.navigate(targetView);
    }
  };

  currentContainer.addEventListener("click", clickHandler);
  renderLoading();

  try {
    const result = await api.users.list();
    if (requestId !== currentRequestId || currentContainer !== container) {
      return;
    }

    renderHome(extractUsers(result));
  } catch (error) {
    if (requestId !== currentRequestId || currentContainer !== container) {
      return;
    }

    renderError(error?.message || "无法加载首页统计");
  }
}

export function unmount() {
  if (currentContainer && clickHandler) {
    currentContainer.removeEventListener("click", clickHandler);
  }

  currentContainer = null;
  clickHandler = null;
}
