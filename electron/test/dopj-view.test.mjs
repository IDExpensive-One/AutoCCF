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

class FakeChildElement {
  constructor({ dataset = {}, value = "", hidden = false } = {}) {
    this.dataset = dataset;
    this.value = value;
    this.hidden = hidden;
    this.disabled = false;
    this.innerHTML = "";
    this.textContent = "";
    this.listeners = new Map();
    this.style = {};
    this.scrollTop = 0;
    this.scrollHeight = 0;
    this.focused = false;
    this.children = [];
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
      listener({ preventDefault() {}, target: this, ...event });
    }
  }

  append(child) {
    this.children.push(child);
    const line = child?.textContent || "";
    this.textContent = this.textContent ? `${this.textContent}\n${line}` : line;
    this.scrollHeight = this.children.length;
    this.scrollTop = this.scrollHeight;
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

class FakeContainer {
  constructor() {
    this._innerHTML = "";
    this.listeners = new Map();
    this.children = new Map();
  }

  set innerHTML(value) {
    this._innerHTML = value;
    this.children.clear();

    if (value.includes("data-dopj-form")) {
      this.children.set("[data-dopj-form]", new FakeChildElement());
      this.children.set("[data-user-select]", new FakeChildElement());
      this.children.set("[data-start-crawl]", new FakeChildElement());
      this.children.set("[data-status]", new FakeChildElement());
      this.children.set("[data-account-body]", new FakeChildElement());
      this.children.set("[data-progress-card]", new FakeChildElement({ hidden: true }));
      this.children.set("[data-progress-fill]", new FakeChildElement());
      this.children.set("[data-progress-text]", new FakeChildElement());
      this.children.set("[data-log-card]", new FakeChildElement({ hidden: true }));
      this.children.set("[data-log-viewer]", new FakeChildElement());
    }

    if (value.includes('data-nav="apou"')) {
      this.children.set('[data-nav="apou"]', new FakeChildElement({ dataset: { nav: "apou" } }));
    }

    if (value.includes('data-nav="dopj"')) {
      this.children.set('[data-nav="dopj"]', new FakeChildElement({ dataset: { nav: "dopj" } }));
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

function createApiStub(options = {}) {
  const progressListeners = [];
  const logListeners = [];
  const removedChannels = [];
  const invokeCalls = [];

  const crawlResult = options.crawlResult || { success: true };

  globalThis.window = {
    api: {
      invoke(action, payload) {
        invokeCalls.push({ action, payload });

        if (action === "apou:outputs") {
          return Promise.resolve({
            success: true,
            outputs: options.outputs || [],
          });
        }

        if (action === "config:load") {
          return Promise.resolve({
            success: true,
            config: {
              accounts: options.accounts || [],
            },
          });
        }

        if (action === "dopj:crawl") {
          if (options.crawlPromise) {
            return options.crawlPromise;
          }

          return Promise.resolve(crawlResult);
        }

        if (action === "users:list") {
          return Promise.resolve({ success: true, users: [] });
        }

        return Promise.resolve({ success: true });
      },
      onProgress(listener) {
        progressListeners.push(listener);
      },
      onLog(listener) {
        logListeners.push(listener);
      },
      onPythonUnavailable() {},
      removeAllListeners(channel) {
        removedChannels.push(channel);
        if (channel === "bridge:progress") {
          progressListeners.length = 0;
        }

        if (channel === "bridge:log") {
          logListeners.length = 0;
        }
      },
    },
  };

  return {
    invokeCalls,
    removedChannels,
    emitProgress(data) {
      progressListeners.forEach((listener) => listener(data));
    },
    emitLog(data) {
      logListeners.forEach((listener) => listener(data));
    },
  };
}

function createDocumentEnvironment() {
  const content = new FakeContainer();
  const header = new FakeChildElement();
  const navItems = [
    new FakeNavItem("home", true),
    new FakeNavItem("apou"),
    new FakeNavItem("dopj"),
    new FakeNavItem("users"),
    new FakeNavItem("settings"),
  ];

  globalThis.document = {
    createElement() {
      return new FakeChildElement();
    },
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

  return { content, header, navItems };
}

test("dopj view loads outputs and accounts then handles crawl progress", async () => {
  let resolveCrawl = null;
  const crawlPromise = new Promise((resolve) => {
    resolveCrawl = resolve;
  });
  const apiStub = createApiStub({
    outputs: [
      {
        username: "团子传说",
        path: "Q:/data/tuanzi_posts.json",
        posts_count: 12,
        has_index: true,
      },
    ],
    accounts: [
      { name: "账号A", bduss: "ABCDEF123456" },
      { name: "账号B", bduss: "ZYXWVU654321" },
    ],
    crawlPromise,
  });
  const { content } = createDocumentEnvironment();
  const moduleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\views\\dopj.js"),
  );

  const dopjView = await import(`${moduleUrl.href}?dopj-view-test`);
  await dopjView.mount(content, {});

  const select = content.querySelector("[data-user-select]");
  const accountBody = content.querySelector("[data-account-body]");
  const startButton = content.querySelector("[data-start-crawl]");
  const progressCard = content.querySelector("[data-progress-card]");
  const progressFill = content.querySelector("[data-progress-fill]");
  const progressText = content.querySelector("[data-progress-text]");
  const logCard = content.querySelector("[data-log-card]");
  const logViewer = content.querySelector("[data-log-viewer]");
  const status = content.querySelector("[data-status]");

  assert.match(select.innerHTML, /团子传说 \(12 条帖子\)/);
  assert.match(accountBody.innerHTML, /账号A/);
  assert.match(accountBody.innerHTML, /ABCDEF\.\.\./);
  assert.match(accountBody.innerHTML, /badge badge-success/);
  assert.equal(progressCard.hidden, true);
  assert.equal(logCard.hidden, true);

  select.value = "Q:/data/tuanzi_posts.json";
  select.dispatch("change", { target: select });
  content.querySelector("[data-dopj-form]").dispatch("submit");
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.deepEqual(apiStub.invokeCalls.slice(0, 3), [
    { action: "apou:outputs", payload: {} },
    { action: "config:load", payload: {} },
    { action: "dopj:crawl", payload: { input_json: "Q:/data/tuanzi_posts.json", threads: undefined } },
  ]);
  assert.equal(startButton.disabled, true);
  assert.equal(progressCard.hidden, false);
  assert.equal(logCard.hidden, false);

  apiStub.emitProgress({ success: 4, failed: 1, skipped: 2, total: 10, message: "已处理 7/10" });
  apiStub.emitLog({ level: "info", message: "抓取中" });

  assert.equal(progressFill.style.width, "70%");
  assert.equal(progressText.textContent, "成功 4 / 失败 1 / 跳过 2 / 总计 10");
  assert.match(logViewer.textContent, /\[INFO\] 抓取中/);

  resolveCrawl({ success: true, message: "爬取完成" });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(startButton.disabled, false);
  assert.match(status.innerHTML, /爬取完成/);

  dopjView.unmount();
  assert.deepEqual(apiStub.removedChannels, [
    "bridge:progress",
    "bridge:log",
    "bridge:progress",
    "bridge:log",
    "bridge:progress",
    "bridge:log",
  ]);
});

test("app registers dopj route with real view", async () => {
  createApiStub();
  const env = createDocumentEnvironment();
  const appModuleUrl = pathToFileURL(
    path.resolve("Q:\\Document\\MySoftware\\AutoCCF\\.worktrees\\electron-migration\\electron\\renderer\\js\\app.js"),
  );

  await import(appModuleUrl.href);
  env.navItems[2].click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(env.header.textContent, "DoPJ");
  assert.match(env.content.innerHTML, /开始 DoPJ 爬取/);
  assert.match(env.content.innerHTML, /账户状态/);
});
