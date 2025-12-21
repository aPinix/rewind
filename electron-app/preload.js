const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onResetUI: (callback) => ipcRenderer.on('reset-ui', (_event, value) => callback(value)),
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', (_event, value) => callback(value))
});

window.addEventListener('DOMContentLoaded', () => {
  console.log('OpenReLife Electron App loaded');
});
