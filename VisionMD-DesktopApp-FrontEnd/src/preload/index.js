// src/preload/index.js
const { contextBridge, ipcRenderer } = require('electron');

dge.exposeInMainWorld('api', {
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  send: (channel, data) => ipcRenderer.send(channel, data),
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),
  receive: (channel, fn) => {
    const subscription = (_event, ...args) => fn(...args);
    ipcRenderer.on(channel, subscription);
    return () => ipcRenderer.removeListener(channel, subscription);
  }
});
