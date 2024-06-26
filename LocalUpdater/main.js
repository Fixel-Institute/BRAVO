const { app, BrowserWindow, shell  } = require('electron');
const { exec } = require("child_process");

const createWindow = () => {
  const win = new BrowserWindow({
    width: 800,
    height: 300
  });
  win.loadURL('https://uf-bravo.jcagle.solutions/updater');

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  createWindow()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
