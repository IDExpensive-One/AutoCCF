const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, execFile } = require('child_process');
const readline = require('readline');

let mainWindow = null;
let pythonCommand = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  return mainWindow;
}

async function findPython() {
  const candidates = process.platform === 'win32'
    ? [
        { command: 'py', args: ['-3', '--version'] },
        { command: 'python', args: ['--version'] },
      ]
    : [
        { command: 'python3', args: ['--version'] },
        { command: 'python', args: ['--version'] },
      ];

  for (const candidate of candidates) {
    try {
      await new Promise((resolve, reject) => {
        execFile(candidate.command, candidate.args, (error) => {
          if (error) {
            reject(error);
            return;
          }
          resolve();
        });
      });
      return candidate.command;
    } catch (_error) {
      continue;
    }
  }

  return null;
}

ipcMain.handle('bridge:invoke', async (event, { action, payload }) => {
  if (!pythonCommand) {
    throw new Error('Python 未找到');
  }

  const bridgePath = app.isPackaged
    ? path.join(process.resourcesPath, 'bridge.py')
    : path.join(__dirname, 'bridge.py');
  const projectRoot = app.isPackaged
    ? process.resourcesPath
    : path.join(__dirname, '..');

  let timeout = 30000;
  if (action === 'apou:crawl') {
    timeout = 300000;
  } else if (action === 'dopj:crawl') {
    timeout = 0;
  }

  return new Promise((resolve, reject) => {
    const child = spawn(
      pythonCommand,
      pythonCommand === 'py' ? ['-3', bridgePath] : [bridgePath],
      {
        cwd: projectRoot,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      },
    );
    const stderrBuffer = [];
    let resolveValue = null;
    let rejectValue = null;
    let settled = false;
    let timer = null;

    const cleanup = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    };

    const settleReject = (error) => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      reject(error);
    };

    const settleResolve = (value) => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      resolve(value);
    };

    const stdoutReader = readline.createInterface({ input: child.stdout });
    stdoutReader.on('line', (line) => {
      if (!line.trim()) {
        return;
      }

      try {
        const parsed = JSON.parse(line);
        if (parsed.type === 'progress') {
          event.sender.send('bridge:progress', parsed.data);
          return;
        }

        if (parsed.type === 'log') {
          event.sender.send('bridge:log', parsed.data);
          return;
        }

        if (parsed.type === 'result') {
          resolveValue = parsed.data;
          return;
        }

        if (parsed.type === 'error') {
          rejectValue = parsed.data;
        }
      } catch (error) {
        settleReject(new Error(`Bridge 输出解析失败: ${error.message}`));
      }
    });

    const stderrReader = readline.createInterface({ input: child.stderr });
    stderrReader.on('line', (line) => {
      stderrBuffer.push(line);
    });

    child.on('error', (error) => {
      settleReject(error);
    });

    child.on('close', (code) => {
      if (settled) {
        return;
      }

      cleanup();

      if (code !== 0) {
        const stderrText = stderrBuffer.join('\n');
        settleReject(new Error(`Bridge 进程退出异常 (code=${code})${stderrText ? `\n${stderrText}` : ''}`));
        return;
      }

      if (rejectValue) {
        const errorMessage = typeof rejectValue === 'string'
          ? rejectValue
          : JSON.stringify(rejectValue);
        settleReject(new Error(errorMessage));
        return;
      }

      settleResolve(resolveValue);
    });

    if (timeout > 0) {
      timer = setTimeout(() => {
        child.kill();
        settleReject(new Error(`Bridge 调用超时: ${action}`));
      }, timeout);
    }

    child.stdin.write(JSON.stringify({ action, payload }));
    child.stdin.end();
  });
});

ipcMain.handle('dialog:openDirectory', async () => {
  const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
  return result.filePaths[0] || null;
});

app.whenReady().then(async () => {
  pythonCommand = await findPython();
  createWindow();

  if (!pythonCommand && mainWindow) {
    mainWindow.webContents.once('did-finish-load', () => {
      mainWindow.webContents.send('python:unavailable');
    });
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();

      if (!pythonCommand && mainWindow) {
        mainWindow.webContents.once('did-finish-load', () => {
          mainWindow.webContents.send('python:unavailable');
        });
      }
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
