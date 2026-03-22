const { contextBridge } = require('electron');

// 占位 — 后续任务会添加 IPC 方法
contextBridge.exposeInMainWorld('api', {});
