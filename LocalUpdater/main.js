const { app, BrowserWindow, shell, ipcMain  } = require('electron');
const path = require('node:path');
const { exec } = require("child_process");

function handleUpdateDocker(event) {
  
  exec("bash " + path.join(__dirname, 'UpdateDocker.sh'), (error, stdout, stderr) => {
    const webContents = event.sender
    const win = BrowserWindow.fromWebContents(webContents)
    win.webContents.send("UpdateDocker", "Complete");
  });
}

const createWindow = () => {
  const win = new BrowserWindow({
    width: 800,
    height: 300,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });


  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  win.loadURL('https://uf-bravo.jcagle.solutions/updater');
}

app.whenReady().then(() => {
  ipcMain.on('RequestDockerUpdate', handleUpdateDocker);
  createWindow();
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
