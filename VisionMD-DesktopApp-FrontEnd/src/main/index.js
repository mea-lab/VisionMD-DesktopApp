// src/main/index.js
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');


// --------------------------------------
// ---------- Environment Vars ----------
// --------------------------------------
const appEnv = process.env.APP_ENV;
const isDev = process.env.NODE_ENV === 'development';
const isDevStatic = appEnv === 'dev_static';
const isProd = process.env.NODE_ENV === 'production';
let djangoProcess = null;


// --------------------------------------
// ---------- Helper Functions ----------
// --------------------------------------
function startDjangoServer() {
  const platform = process.platform;  // 'win32', 'darwin', 'linux'
  let executableName;
  let dirName;
  let basePath;

  if (platform === 'win32') {
    executableName = 'serve_windows.exe';
    dirName = 'serve_windows'
    basePath = path.join(process.resourcesPath, dirName);
  } else if (platform === 'linux') {
    executableName = 'serve_linux';
    dirName = 'serve_linux'
    basePath = path.join(process.resourcesPath, dirName);
  } else if (platform === 'darwin') {
    executableName = 'serve_mac_container';
    dirName = 'serve_mac'
    basePath = path.join(process.resourcesPath, '..', 'backend', dirName);  
  } else {
    throw new Error(`Unsupported platform: ${platform}`);
  }

  const djangoExecutable = path.join(basePath, executableName);
  console.log("Attempting to start django server from", djangoExecutable)

  djangoProcess = spawn(djangoExecutable, [], {
    cwd: basePath,
    stdio: ['inherit'],
    shell: false,
    detached: false,
    windowsHide: true,
    env: {
      ...process.env,
      PATH: `${process.env.PATH}${path.delimiter}${basePath}`,
    },
  });
}

function createWindow() {
  console.log("Dir root: ", __dirname)
  console.log("Dev Mode:", isDev)
  console.log("Production Mode:", isProd)

  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    autoHideMenuBar: true,
    icon: path.join(__dirname, '../../resources/icon.png'),
  });

  win.once('ready-to-show', () => win.show());

  if (isDev) {
    console.log("Loading app from: ", process.env.ELECTRON_RENDERER_URL)
    win.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    console.log("Loading app from: ", path.join(__dirname, '../renderer/index.html'))
    win.loadFile(path.join(__dirname, '../renderer/index.html'));
  }

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

function waitForServer(url, timeout = 30000, interval = 500) {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(url, res => {
        res.destroy();
        resolve();
      });

      req.on('error', () => {
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Server at ${url} did not start within ${timeout}ms`));
        } else {
          setTimeout(check, interval);
        }
      });
    };

    check();
  });
}

function killDjangoProcess() {
  if (djangoProcess && djangoProcess.pid) {
    try {
      process.kill(djangoProcess.pid, 'SIGTERM');
      setTimeout(() => {
        try {
          process.kill(djangoProcess.pid, 'SIGKILL');
        } catch (e) {
          console.warn('Failed to send SIGKILL, process might be killed already:', e);
        }
      }, 1)
    } catch (e) {
      process.kill(djangoProcess.pid, 'SIGKILL');
      console.warn('Failed to kill Django process, sent one more SIGKILL before termination:', e);
    }
  }
}


// ------------------------------------
// ---------- App Life Cycle ----------
// ------------------------------------
app.whenReady().then(async () => {
  if (!isDev || isDevStatic) {
    try {
      startDjangoServer();
      await waitForServer('http://127.0.0.1:8000');
      console.log("Server running on http://127.0.0.1:8000")
    } catch (err) {
      console.error("Django server did not start:", err.message);
    }
  }

  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('will-quit', killDjangoProcess);
app.on('before-quit', killDjangoProcess);

process.on('exit', killDjangoProcess);
process.on('SIGINT', killDjangoProcess);
process.on('SIGTERM', killDjangoProcess);
process.on('uncaughtException', err => {
  console.error('Fatal error:', err);
  killDjangoProcess();
  process.exit(1);
});