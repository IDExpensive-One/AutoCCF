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
    this.innerHTML = "";
    this.textContent = "";
  }
}

function createEnvironment() {
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

test("renderer api wrapper and router placeholders work", async () => {
  const env = createEnvironment();
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

  await import(`${appModuleUrl.href}?app-test`);

  assert.equal(env.header.textContent, "首页");
  assert.match(env.content.innerHTML, /首页 视图开发中/);
  assert.equal(env.navItems[0].classList.contains("active"), true);

  env.navItems[2].click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(env.header.textContent, "DoPJ");
  assert.match(env.content.innerHTML, /DoPJ 视图开发中/);
  assert.equal(env.navItems[0].classList.contains("active"), false);
  assert.equal(env.navItems[2].classList.contains("active"), true);

  env.triggerPythonUnavailable();
  assert.match(env.content.innerHTML, /Python 未找到/);
  assert.match(env.content.innerHTML, /下载 Python/);
});
