const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const API_HOST = '127.0.0.1';
const API_PORT = 8000;
const API_URL = `http://${API_HOST}:${API_PORT}/docs`;
const STARTUP_TIMEOUT_MS = 30000;

const pythonBin = process.env.PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
const workspaceRoot = path.resolve(__dirname, '..');
const sourceProjectRoot = path.resolve(workspaceRoot, 'intern_assistant');
const packagedRoot = process.resourcesPath;
const isPackaged = app.isPackaged;

let backendProcess = null;
let backendStartedByApp = false;
let backendLogPath = null;

function runtimePaths() {
  if (isPackaged) {
    return {
      backendRoot: path.resolve(packagedRoot, 'backend'),
      frontendIndex: path.resolve(packagedRoot, 'frontend', 'dist', 'index.html')
    };
  }
  return {
    backendRoot: sourceProjectRoot,
    frontendIndex: path.resolve(sourceProjectRoot, 'frontend', 'dist', 'index.html')
  };
}

function runtimeDataPaths() {
  const dataRoot = path.resolve(app.getPath('userData'), 'intern-assistant-data');
  return {
    root: dataRoot,
    vault: path.resolve(dataRoot, 'vault'),
    database: path.resolve(dataRoot, 'database', 'intern_assistant.db'),
    envFile: path.resolve(dataRoot, '.env.local')
  };
}

async function isBackendRunning() {
  try {
    const response = await fetch(API_URL);
    return response.ok;
  } catch {
    return false;
  }
}

function waitForBackend() {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      fetch(API_URL)
        .then((response) => {
          if (response.ok) {
            resolve();
            return;
          }
          if (Date.now() - started > STARTUP_TIMEOUT_MS) {
            reject(new Error('Backend did not become ready in time.'));
            return;
          }
          setTimeout(check, 500);
        })
        .catch(() => {
          if (Date.now() - started > STARTUP_TIMEOUT_MS) {
            reject(new Error('Backend did not become ready in time.'));
            return;
          }
          setTimeout(check, 500);
        });
    };
    check();
  });
}

function startBackend() {
  const paths = runtimePaths();
  const data = runtimeDataPaths();
  fs.mkdirSync(path.dirname(data.database), { recursive: true });
  fs.mkdirSync(data.vault, { recursive: true });
  fs.mkdirSync(data.root, { recursive: true });
  backendLogPath = path.resolve(data.root, 'backend.log');
  const backendLogFd = fs.openSync(backendLogPath, 'a');

  backendProcess = spawn(
    pythonBin,
    ['-m', 'uvicorn', 'app.main:app', '--host', API_HOST, '--port', String(API_PORT)],
    {
      cwd: paths.backendRoot,
      stdio: ['ignore', backendLogFd, backendLogFd],
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        INTERN_ASSISTANT_ROOT: data.root,
        OBSIDIAN_VAULT_PATH: data.vault,
        DATABASE_PATH: data.database,
        LOCAL_ENV_PATH: data.envFile
      }
    }
  );
  fs.closeSync(backendLogFd);
  backendStartedByApp = true;
  backendProcess.unref();

  backendProcess.on('error', (error) => {
    dialog.showErrorBox('Backend Launch Error', String(error));
  });

  backendProcess.on('exit', (code) => {
    if (code !== 0) {
      const tail = readLogTail(backendLogPath);
      const details = tail ? `\n\nRecent log:\n${tail}` : '';
      dialog.showErrorBox(
        'Backend Stopped',
        `FastAPI backend exited with code ${code}.${backendLogPath ? `\n\nLog file: ${backendLogPath}` : ''}${details}`
      );
    }
    backendProcess = null;
    backendStartedByApp = false;
  });
}

function readLogTail(filePath) {
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    const lines = raw.trim().split(/\r?\n/);
    return lines.slice(-8).join('\n');
  } catch {
    return '';
  }
}

function stopBackend() {
  if (!backendProcess || !backendStartedByApp) {
    return;
  }
  const pid = backendProcess.pid;
  if (process.platform === 'win32' && pid) {
    spawn('taskkill', ['/pid', String(pid), '/t', '/f'], {
      stdio: 'ignore',
      windowsHide: true
    });
  } else {
    backendProcess.kill();
  }
  backendProcess = null;
  backendStartedByApp = false;
}

async function createWindow() {
  const paths = runtimePaths();

  if (!fs.existsSync(paths.backendRoot)) {
    dialog.showErrorBox('Backend Bundle Missing', `Missing ${paths.backendRoot}`);
    app.quit();
    return;
  }

  if (!fs.existsSync(paths.frontendIndex)) {
    dialog.showErrorBox(
      'Frontend Build Missing',
      `Missing ${paths.frontendIndex}. Run "npm run build" in intern_assistant/frontend first.`
    );
    app.quit();
    return;
  }

  const backendAlreadyRunning = await isBackendRunning();
  if (!backendAlreadyRunning) {
    startBackend();
    try {
      await waitForBackend();
    } catch (error) {
      dialog.showErrorBox('Startup Error', String(error));
      app.quit();
      return;
    }
  }

  const window = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 720,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      webSecurity: false
    }
  });

  await window.loadFile(paths.frontendIndex);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});
