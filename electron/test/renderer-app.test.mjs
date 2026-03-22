import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL } from "node:url";

class FakeClassList {
  constructor(initial = []) {
    this.classes = new Set(initial);
  }

  toggle(name, force) {
    if (force) {
      this.classes.add(name);
      return true;
    }

    this.classes.delete(name);
    return false;
  }

  contains(name) {
    return this.classes.has(name);
  }
}

class FakeNavItem {
  constructor(view, active = false) {
    this.dataset = { view };
    this.classList = new FakeClassList(active ? ["nav-item", "active"] : ["nav-item"]);
    this.listeners = new Map();
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  click() {
    const listener = this.listeners.get("click");
    if (listener) {
      listener({ preventDefault() {} });
    }
  }
}

class FakeElement {
  constructor() {
    this._innerHTML = "";
    this.textContent = "";
    this.listeners = new Map();
    this.children = new Map();
  }

  set innerHTML(value) {
    this._innerHTML = value;
    this.children.clear();

    if (value.includes("data-apou-form")) {
      this.children.set("[data-apou-form]", new FakeInteractiveElement());
      this.children.set("#apou-username", new FakeInteractiveElement());
      this.children.set("[data-start-crawl]", new FakeInteractiveElement());
      this.children.set("[data-status]", new FakeInteractiveElement());
      this.children.set("[data-progress-card]", new FakeInteractiveElement());
      this.children.set("[data-progress-fill]", new FakeInteractiveElement());
      this.children.set("[data-progress-text]", new FakeInteractiveElement());
      this.children.set("[data-page-text]", new FakeInteractiveElement());
      this.children.set("[data-log-card]", new FakeInteractiveElement());
      this.children.set("[data-log-viewer]", new FakeInteractiveElement());
    }

    if (value.includes("data-dopj-form")) {
      this.children.set("[data-dopj-form]", new FakeInteractiveElement());
      this.children.set("[data-user-select]", new FakeInteractiveElement());
      this.children.set("[data-start-crawl]", new FakeInteractiveElement());
      this.children.set("[data-status]", new FakeInteractiveElement());
      this.children.set("[data-account-body]", new FakeInteractiveElement());
      this.children.set("[data-progress-card]", new FakeInteractiveElement());
      this.children.set("[data-progress-fill]", new FakeInteractiveElement());
      this.children.set("[data-progress-text]", new FakeInteractiveElement());
      this.children.set("[data-log-card]", new FakeInteractiveElement());
      this.children.set("[data-log-viewer]", new FakeInteractiveElement());
    }

    if (value.includes('data-nav="apou"')) {
      this.children.set('[data-nav="apou"]', new FakeActionElement("apou"));
    }

    if (value.includes('data-nav="dopj"')) {
      this.children.set('[data-nav="dopj"]', new FakeActionElement("dopj"));
    }
  }

  get innerHTML() {
    return this._innerHTML;
  }

  querySelector(selector) {
    return this.children.get(selector) || null;
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  removeEventListener(type, listener) {
    const current = this.listeners.get(type);
    if (current === listener) {
      this.listeners.delete(type);
    }
  }

  dispatchClick(target) {
    const listener = this.listeners.get("click");
    if (listener) {
      listener({ target, preventDefault() {} });
    }
  }
}

class FakeActionElement {
  constructor(targetView) {
    this.dataset = { nav: targetView };
  }

  closest() {
    return this;
  }
}

class FakeInteractiveElement {
  constructor() {
    this.listeners = new Map();
    this.style = {};
    this.hidden = false;
    this.disabled = false;
    this.value = "";
    this.textContent = "";
    this.innerHTML = "";
    this.scrollTop = 0;
    this.scrollHeight = 0;
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  removeEventListener(type, listener) {
    const current = this.listeners.get(type);
    if (current === listener) {
      this.listeners.delete(type);
    }
  }

  append(child) {
    this.textContent = child?.textContent || "";
    this.scrollHeight += 1;
    this.scrollTop = this.scrollHeight;
  }

  focus() {}
}

function createEnvironment(options = {}) {
  const content = new FakeElement();
  const header = new FakeElement();
  const navItems = [
    new FakeNavItem("home", true),
    new FakeNavItem("apou"),
    new FakeNavItem("dopj"),
    new FakeNavItem("users"),
    new FakeNavItem("settings"),
  ];

  const pythonUnavailableListeners = [];
  const invokeCalls = [];

  globalThis.document = {
    getElementById(id) {
      if (id === "content") {
        return content;
      }
      return null;
    },
    querySelector(selector) {
      if (selector === ".content-header h2") {
        return header;
      }
      return null;
    },
    querySelectorAll(selector) {
      if (selector === ".nav-item") {
        return navItems;
      }
      return [];
    },
  };

  globalThis.window = {
    api: {
      invoke(action, payload) {
        invokeCalls.push({ action, payload });
        if (action === "users:list") {
          if (options.usersListError) {
            return Promise.reject(new Error(options.usersListError));
          }

          return Promise.resolve({
            success: true,
            users: [
              { name: "alice", posts_count: 3, last_activity: 1_699_992_800 },
              { name: "bob", posts_count: 5, last_activity: null },
            ],
          });
        }
        return Promise.resolve({ action, payload });
      },
      onProgress() {},
      onLog() {},
      onPythonUnavailable(callback) {
        pythonUnavailableListeners.push(callback);
      },
      removeAllListeners() {},
    },
  };

  return {
    content,
    header,
    navItems,
    invokeCalls,
    triggerPythonUnavailable() {
      pythonUnavailableListeners.forEach((listener) => listener());
    },
  };
}

test("renderer api wrapper and home view work", async () => {
  const env = createEnvironment();
  const originalDateNow = Date.now;
  Date.now = () => 1_700_000_000_000;
  const apiModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\api.js"),
  );
  const appModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\app.js"),
  );

  const { api } = await import(`${apiModuleUrl.href}?api-test`);
  await api.config.load();
  await api.config.save({ theme: "light" });
  await api.apou.crawl("tester");
  await api.apou.outputs();
  await api.dopj.crawl("input.json", 3);
  await api.users.list();
  await api.users.detail("tester");

  assert.deepEqual(env.invokeCalls, [
    { action: "config:load", payload: {} },
    { action: "config:save", payload: { theme: "light" } },
    { action: "apou:crawl", payload: { username: "tester" } },
    { action: "apou:outputs", payload: {} },
    { action: "dopj:crawl", payload: { input_json: "input.json", threads: 3 } },
    { action: "users:list", payload: {} },
    { action: "users:detail", payload: { username: "tester" } },
  ]);

  await import(appModuleUrl.href);

  assert.equal(env.header.textContent, "首页");
  assert.match(env.content.innerHTML, /已爬取用户/);
  assert.match(env.content.innerHTML, />2</);
  assert.match(env.content.innerHTML, /帖子总数/);
  assert.match(env.content.innerHTML, />8</);
  assert.match(env.content.innerHTML, /最近活动/);
  assert.match(env.content.innerHTML, /2小时前/);
  assert.match(env.content.innerHTML, /开始 APoU/);
  assert.match(env.content.innerHTML, /开始 DoPJ/);
  assert.equal(env.navItems[0].classList.contains("active"), true);

  env.content.dispatchClick(env.content.querySelector('[data-nav="apou"]'));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(env.header.textContent, "APoU");
  assert.match(env.content.innerHTML, /开始 APoU 爬取/);
  assert.equal(env.navItems[1].classList.contains("active"), true);

  env.navItems[2].click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(env.header.textContent, "DoPJ");
  assert.match(env.content.innerHTML, /开始 DoPJ 爬取/);
  assert.match(env.content.innerHTML, /账户状态/);
  assert.equal(env.navItems[0].classList.contains("active"), false);
  assert.equal(env.navItems[2].classList.contains("active"), true);

  env.triggerPythonUnavailable();
  assert.match(env.content.innerHTML, /Python 未找到/);
  assert.match(env.content.innerHTML, /下载 Python/);

  Date.now = originalDateNow;
});

test("home view shows error state when users list fails", async () => {
  const env = createEnvironment({ usersListError: "接口异常" });
  const appModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\app.js"),
  );

  const { initApp } = await import(appModuleUrl.href);
  initApp();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(env.header.textContent, "首页");
  assert.match(env.content.innerHTML, /加载失败：接口异常/);
});
