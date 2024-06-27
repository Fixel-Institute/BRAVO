const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  updateDocker: () => ipcRenderer.send('RequestDockerUpdate'),
  onDockerUpdated: (callback) => ipcRenderer.on('UpdateDocker', (_event, value) => callback(value))
});
