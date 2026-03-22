import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL } from "node:url";

class FakeClassList {
  constructor(initial = []) {
    this.classes = new Set(initial);
  }

  add(name) {
    this.classes.add(name);
  }

  remove(name) {
    this.classes.delete(name);
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

class FakeElement {
  constructor({ dataset = {}, value = "", hidden = false } = {}) {
    this.dataset = dataset;
    this.value = value;
    this.hidden = hidden;
    this.disabled = false;
    this.innerHTML = "";
    this.textContent = "";
    this.style = {};
    this.listeners = new Map();
    this.classList = new FakeClassList();
    this.focused = false;
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

  dispatch(type, event = {}) {
    const listener = this.listeners.get(type);
    if (listener) {
      listener({ preventDefault() {}, target: this, currentTarget: this, ...event });
    }
  }

  focus() {
    this.focused = true;
  }

  click() {
    this.dispatch("click");
  }

  closest() {
    return this;
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

class FakeContainer {
  constructor() {
    this._innerHTML = "";
    this.children = new Map();
    this.listeners = new Map();
  }

  set innerHTML(value) {
    this._innerHTML = value;
    this.children.clear();

    if (value.includes("data-users-search")) {
      this.children.set("[data-users-search]", new FakeElement());
      this.children.set("[data-users-loading]", new FakeElement());
      this.children.set("[data-users-error]", new FakeElement({ hidden: true }));
      this.children.set("[data-users-body]", new FakeElement());
    }

    if (value.includes("data-user-detail-back")) {
      this.children.set("[data-user-detail-back]", new FakeElement());
      this.children.set("[data-user-detail-loading]", new FakeElement());
      this.children.set("[data-user-detail-error]", new FakeElement({ hidden: true }));
      this.children.set("[data-user-detail-header]", new FakeElement({ hidden: true }));
      this.children.set("[data-user-detail-username]", new FakeElement());
      this.children.set("[data-user-detail-meta]", new FakeElement());
      this.children.set("[data-user-detail-posts]", new FakeElement());
      this.children.set("[data-user-detail-threads]", new FakeElement());
      this.children.set("[data-user-detail-files]", new FakeElement());
      this.children.set('[data-tab="posts"]', new FakeElement({ dataset: { tab: "posts" } }));
      this.children.set('[data-tab="threads"]', new FakeElement({ dataset: { tab: "threads" } }));
      this.children.set('[data-tab="files"]', new FakeElement({ dataset: { tab: "files" } }));
    }

    if (value.includes('data-nav="users"')) {
      this.children.set('[data-nav="users"]', new FakeElement({ dataset: { nav: "users" } }));
    }
  }

  get innerHTML() {
    return this._innerHTML;
  }

  querySelector(selector) {
    const existing = this.children.get(selector);
    if (existing) {
      return existing;
    }

    const actionMatch = selector.match(/^\[data-user-action="(.+)"\]$/);
    if (actionMatch) {
      const username = actionMatch[1];
      for (const child of this.children.values()) {
        if (child.innerHTML.includes(`data-user-action="${username}"`)) {
          const actionElement = new FakeElement({ dataset: { userAction: username } });
          this.children.set(selector, actionElement);
          return actionElement;
        }
      }
    }

    return null;
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
}

function createUsersApiStub(options = {}) {
  const invokeCalls = [];
  const usersPromise = options.usersPromise || Promise.resolve({
    success: true,
    users: [
      { name: "alice", path: "Q:/users/alice", posts_count: 4, last_activity: 1 },
      { name: "bob", path: "Q:/users/bob", posts_count: 0, last_activity: 2 },
    ],
  });
  const detailPromise = options.detailPromise || Promise.resolve({
    success: true,
    username: "alice",
    user_dir: "Q:/users/alice",
    posts: [
      { tid: 101, pid: 501, title: "帖子一", forum: "测试吧", href: "https://tieba.baidu.com/p/101?pid=501" },
    ],
    threads: [
      { tid: 101, title: "主题一", status: "已完成" },
    ],
    files: [
      { name: "posts", is_dir: true, size_text: "-" },
      { name: "thread.json", is_dir: false, size_text: "3 KB" },
    ],
  });

  globalThis.window = {
    api: {
      invoke(action, payload) {
        invokeCalls.push({ action, payload });

        if (action === "users:list") {
          return usersPromise;
        }

        if (action === "users:detail") {
          return detailPromise;
        }

        return Promise.resolve({ success: true, users: [] });
      },
      onProgress() {},
      onLog() {},
      onPythonUnavailable() {},
      removeAllListeners() {},
    },
  };

  return { invokeCalls };
}

function createDocumentEnvironment() {
  const content = new FakeContainer();
  const header = new FakeElement();
  const navItems = [
    new FakeNavItem("home", true),
    new FakeNavItem("apou"),
    new FakeNavItem("dopj"),
    new FakeNavItem("users"),
    new FakeNavItem("settings"),
  ];

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
    createElement() {
      return new FakeElement();
    },
  };

  return { content, header, navItems };
}

test("users view loads users, filters by name, and navigates to detail", async () => {
  createUsersApiStub();
  const { content } = createDocumentEnvironment();
  const usersModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\views\\users.js"),
  );
  const appModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\app.js"),
  );

  const appModule = await import(appModuleUrl.href);
  appModule.initApp();
  const usersView = await import(`${usersModuleUrl.href}?users-view`);

  const navigations = [];
  appModule.router.navigate = async (name, params = {}) => {
    navigations.push({ name, params });
  };

  const mountPromise = usersView.mount(content, {});
  assert.match(content.innerHTML, /加载中/);
  await mountPromise;

  const searchInput = content.querySelector("[data-users-search]");
  const tableBody = content.querySelector("[data-users-body]");

  assert.match(tableBody.innerHTML, /alice/);
  assert.match(tableBody.innerHTML, /已完成/);
  assert.match(tableBody.innerHTML, /查看详情/);
  assert.match(tableBody.innerHTML, /bob/);

  searchInput.value = "ali";
  searchInput.dispatch("input", { target: searchInput });

  assert.match(tableBody.innerHTML, /alice/);
  assert.doesNotMatch(tableBody.innerHTML, /bob/);

  const detailButton = content.querySelector('[data-user-action="alice"]');
  detailButton.click();

  assert.deepEqual(navigations, [
    { name: "user-detail", params: { username: "alice" } },
  ]);

  usersView.unmount();
  assert.equal(searchInput.listeners.size, 0);
  assert.equal(detailButton.listeners.size, 0);
});

test("user detail view loads data, switches tabs, and supports back navigation", async () => {
  createUsersApiStub();
  const { content } = createDocumentEnvironment();
  const userDetailModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\views\\user-detail.js"),
  );
  const appModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\app.js"),
  );

  const appModule = await import(appModuleUrl.href);
  appModule.initApp();
  const userDetailView = await import(`${userDetailModuleUrl.href}?user-detail-view`);

  const navigations = [];
  appModule.router.navigate = async (name, params = {}) => {
    navigations.push({ name, params });
  };

  const mountPromise = userDetailView.mount(content, { username: "alice" });
  assert.match(content.innerHTML, /加载中/);
  await mountPromise;

  const backButton = content.querySelector("[data-user-detail-back]");
  const username = content.querySelector("[data-user-detail-username]");
  const meta = content.querySelector("[data-user-detail-meta]");
  const postsPanel = content.querySelector("[data-user-detail-posts]");
  const threadsPanel = content.querySelector("[data-user-detail-threads]");
  const filesPanel = content.querySelector("[data-user-detail-files]");
  const threadsTab = content.querySelector('[data-tab="threads"]');
  const filesTab = content.querySelector('[data-tab="files"]');

  assert.equal(username.textContent, "alice");
  assert.match(meta.textContent, /Q:\//);
  assert.match(postsPanel.innerHTML, /帖子一/);
  assert.match(postsPanel.innerHTML, /测试吧/);
  assert.equal(postsPanel.hidden, false);
  assert.equal(threadsPanel.hidden, true);
  assert.equal(filesPanel.hidden, true);

  threadsTab.click();
  assert.equal(postsPanel.hidden, true);
  assert.equal(threadsPanel.hidden, false);
  assert.match(threadsPanel.innerHTML, /主题一/);

  filesTab.click();
  assert.equal(threadsPanel.hidden, true);
  assert.equal(filesPanel.hidden, false);
  assert.match(filesPanel.innerHTML, /目录|📁/);
  assert.match(filesPanel.innerHTML, /thread.json/);

  backButton.click();
  assert.deepEqual(navigations, [
    { name: "users", params: {} },
  ]);

  userDetailView.unmount();
  assert.equal(backButton.listeners.size, 0);
  assert.equal(threadsTab.listeners.size, 0);
  assert.equal(filesTab.listeners.size, 0);
});

test("app registers users route with real view", async () => {
  createUsersApiStub();
  const env = createDocumentEnvironment();
  const appModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\app.js"),
  );

  const appModule = await import(appModuleUrl.href);
  appModule.initApp();
  env.navItems[3].click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(env.header.textContent, "用户");
  assert.match(env.content.innerHTML, /搜索用户/);
  assert.match(env.content.querySelector("[data-users-body]").innerHTML, /查看详情/);
});
