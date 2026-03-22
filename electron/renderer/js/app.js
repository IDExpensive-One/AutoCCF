import { api } from "./api.js";
import * as homeView from "./views/home.js";

const VIEW_TITLES = {
  home: "首页",
  apou: "APoU",
  dopj: "DoPJ",
  users: "用户",
  settings: "设置",
};

function createPlaceholderView(name) {
  const label = VIEW_TITLES[name] || name;

  return {
    mount(container) {
      container.innerHTML = `
        <div class="card">
          <h3>${label}</h3>
          <p>${label} 视图开发中...</p>
        </div>
      `;
    },
  };
}

export class Router {
  constructor() {
    this.views = {};
    this.currentView = null;
    this.container = document.getElementById("content");
  }

  register(name, viewModule) {
    this.views[name] = viewModule;
  }

  async navigate(name, params = {}) {
    if (this.currentView && this.views[this.currentView]?.unmount) {
      this.views[this.currentView].unmount();
    }

    document.querySelectorAll(".nav-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.view === name);
    });

    const headerEl = document.querySelector(".content-header h2");
    if (headerEl) {
      headerEl.textContent = VIEW_TITLES[name] || name;
    }

    this.container.innerHTML = "";
    this.currentView = name;

    if (this.views[name]?.mount) {
      await this.views[name].mount(this.container, params);
    }
  }
}

export let router = null;

export function initApp() {
  router = new Router();

  Object.keys(VIEW_TITLES).forEach((name) => {
    if (name === "home") {
      router.register(name, homeView);
      return;
    }

    router.register(name, createPlaceholderView(name));
  });

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (event) => {
      event.preventDefault();
      const viewName = item.dataset.view;
      if (viewName) {
        void router.navigate(viewName);
      }
    });
  });

  api.onPythonUnavailable(() => {
    const content = document.getElementById("content");
    content.innerHTML = `
      <div class="card" style="max-width: 500px; margin: var(--space-xl) auto; text-align: center;">
        <h3 style="color: var(--color-error); margin-bottom: var(--space-md);">Python 未找到</h3>
        <p style="margin-bottom: var(--space-md);">运行此应用需要 Python 3.10 或更高版本。</p>
        <a href="https://www.python.org/downloads/" class="btn btn-primary" target="_blank">下载 Python</a>
      </div>
    `;
  });

  void router.navigate("home");
  return router;
}

void initApp();
