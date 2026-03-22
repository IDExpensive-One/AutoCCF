export const api = {
  config: {
    load: () => window.api.invoke("config:load", {}),
    save: (config) => window.api.invoke("config:save", config),
  },
  apou: {
    crawl: (username) => window.api.invoke("apou:crawl", { username }),
    outputs: () => window.api.invoke("apou:outputs", {}),
  },
  dopj: {
    crawl: (inputJson, threads) => window.api.invoke("dopj:crawl", {
      input_json: inputJson,
      threads,
    }),
  },
  users: {
    list: () => window.api.invoke("users:list", {}),
    detail: (username) => window.api.invoke("users:detail", { username }),
  },
  onProgress: (callback) => window.api.onProgress(callback),
  onLog: (callback) => window.api.onLog(callback),
  onPythonUnavailable: (callback) => window.api.onPythonUnavailable(callback),
  removeAllListeners: (channel) => window.api.removeAllListeners(channel),
};
