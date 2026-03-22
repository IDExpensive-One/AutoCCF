const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  invoke: (action, payload) => ipcRenderer.invoke('bridge:invoke', { action, payload }),
  onProgress: (callback) => {
    ipcRenderer.on('bridge:progress', (_event, data) => callback(data));
  },
  onLog: (callback) => {
    ipcRenderer.on('bridge:log', (_event, data) => callback(data));
  },
  onPythonUnavailable: (callback) => {
    ipcRenderer.on('python:unavailable', (_event) => callback());
  },
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },
});
