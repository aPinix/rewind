const { app, BrowserWindow, globalShortcut, screen, Tray, Menu, nativeImage, Notification, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

const OPENRECALL_URL = 'http://127.0.0.1:8082';
let mainWindow = null;
let tray = null;
let isPaused = false;
let pauseReminderInterval = null;


// Set explicit app name for notifications
if (process.platform === 'darwin') {
  app.setName('OpenReLife');
}

function loadApp() {
  if (!mainWindow) return;

  fetch(OPENRECALL_URL)
    .then(res => {
      if (res.ok) {
        mainWindow.loadURL(OPENRECALL_URL);
        if (process.platform === 'darwin') {
           mainWindow.setSimpleFullScreen(true);
        }
        mainWindow.show();
        mainWindow.focus();
      } else {
        throw new Error('Not ready');
      }
    })
    .catch(() => {
      setTimeout(loadApp, 1000);
    });
}

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: width,
    height: height,
    show: false,
    frame: false,
    transparent: false,
    backgroundColor: '#000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      enableRemoteModule: false
    },
    skipTaskbar: true,
    simpleFullscreen: true,
    icon: path.join(__dirname, 'app-icon.png')
  });

  // Load splash screen immediately
  mainWindow.loadFile(path.join(__dirname, 'loading.html'));
  
  // Start trying to connect to backend
  loadApp();

  mainWindow.once('ready-to-show', () => {
    console.log('✅ Window ready');
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle navigation errors
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    if (errorCode === -3) { // ERR_ABORTED is normal during navigation
      return;
    }
    console.error('Failed to load:', errorDescription);
    
    // Go back to loading screen if main app fails
    if (mainWindow) {
        mainWindow.loadFile(path.join(__dirname, 'loading.html'));
        setTimeout(loadApp, 1000);
    }
  });
} 

function showWindow() {
  if (mainWindow === null) {
    createWindow();
  }
  
  if (mainWindow) {
    mainWindow.webContents.send('reset-ui');
    mainWindow.setSimpleFullScreen(true);
    mainWindow.show();
    mainWindow.focus();
  }
}

function hideWindow() {
  if (mainWindow) {
    mainWindow.webContents.send('reset-ui');
    mainWindow.setSimpleFullScreen(false);
    setTimeout(() => {
      if (mainWindow) {
        mainWindow.hide();
      }
    }, 100);
  }
}


async function checkRecordingStatus(retryCount = 0) {
  try {
    const res = await fetch(`${OPENRECALL_URL}/api/recording-status`);
    if (!res.ok) throw new Error('Status check failed');
    const data = await res.json();
    isPaused = data.paused;
    updateTrayMenu();
    handlePauseReminder(isPaused);
  } catch (err) {
    if (retryCount < 10) {
        // Backend might be starting up, retry in 1s
        setTimeout(() => checkRecordingStatus(retryCount + 1), 1000);
    } else {
        console.error('Failed to check recording status after retries:', err);
    }
  }
}

async function toggleRecording() {
  try {
    const endpoint = isPaused ? '/api/resume-recording' : '/api/pause-recording';
    const res = await fetch(`${OPENRECALL_URL}${endpoint}`, { method: 'POST' });
    const data = await res.json();
    isPaused = data.paused;
    updateTrayMenu();
    handlePauseReminder(isPaused);
  } catch (err) {
    console.error('Failed to toggle recording:', err);
  }
}

function handlePauseReminder(paused) {
  if (paused) {
    if (!pauseReminderInterval) {
      // Send reminder every 30 minutes
      pauseReminderInterval = setInterval(() => {
        const notification = new Notification({
          title: 'OpenReLife Paused',
          body: 'Recording is currently paused. Resume to capture your history.',
          silent: false,
          urgency: 'critical', // Attempt to make it more visible
          hasReply: false
        });
        
        notification.on('click', () => {
          showWindow();
        });
        
        notification.show();
      }, 30 * 60 * 1000); 
    }
  } else {
    if (pauseReminderInterval) {
      clearInterval(pauseReminderInterval);
      pauseReminderInterval = null;
    }
  }
}

function updateTrayMenu() {
  if (!tray) return;

  if (isPaused && trayIconPaused) {
    tray.setImage(trayIconPaused);
  } else if (trayIconNormal) {
    tray.setImage(trayIconNormal);
  }

  const contextMenu = Menu.buildFromTemplate([
    {
      label: isPaused ? 'Resume Recording' : 'Pause Recording',
      click: () => toggleRecording(),
      icon: isPaused ? null : null // Could add icon here
    },
    { type: 'separator' },
    { 
      label: 'Show OpenReLife', 
      click: () => showWindow(),
      accelerator: 'CommandOrControl+Shift+Space'
    },
    { 
      label: 'Settings', 
      click: () => {
        showWindow();
        if (mainWindow) {
            mainWindow.webContents.send('open-settings');
        }
      }
    },
    { type: 'separator' },
    { 
      label: 'About OpenReLife',
      click: () => {
        dialog.showMessageBox({
          type: 'info',
          title: 'About OpenReLife',
          message: 'OpenReLife v1.0.0',
          detail: 'Screen Memory (powered by AI) - made with ❤️ by Porech - https://github.com/porech/openrelife',
          buttons: ['OK'],
          icon: path.join(__dirname, 'app-icon.png')
        });
      }
    },
    { type: 'separator' },
    { 
      label: 'Quit', 
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
      accelerator: 'CommandOrControl+Q'
    }
  ]);
  
  tray.setToolTip(isPaused ? 'OpenReLife (Paused)' : 'OpenReLife - Recording active');
  tray.setContextMenu(contextMenu);
}


let trayIconNormal = null;
let trayIconPaused = null;

function createTray() {
  const iconPath = path.join(__dirname, 'tray-iconTemplate.png');
  const pausedIconPath = path.join(__dirname, 'tray-icon-pausedTemplate.png');
  
  const icon = nativeImage.createFromPath(iconPath);
  const pausedIcon = nativeImage.createFromPath(pausedIconPath);
  
  trayIconNormal = icon.resize({ width: 22 });
  trayIconNormal.setTemplateImage(true);
  
  trayIconPaused = pausedIcon.resize({ width: 22 });
  trayIconPaused.setTemplateImage(true);
  
  tray = new Tray(trayIconNormal);
  updateTrayMenu();
}



let pythonProcess = null;

function startBackend() {
  const isDev = !app.isPackaged;
  // In prod, resourcesPath points to Contents/Resources where we copied openrelife and pyproject.toml
  const projectRoot = isDev ? path.join(__dirname, '..') : process.resourcesPath;

  console.log('Starting backend in:', projectRoot);
  
  // Enhance PATH to find uv in common user locations
  const homeDir = app.getPath('home');
  const commonPaths = [
    path.join(homeDir, '.cargo/bin'),
    '/usr/local/bin',
    '/opt/homebrew/bin',
    process.env.PATH
  ];
  
  const env = { 
    ...process.env, 
    PATH: commonPaths.join(path.delimiter),
    PYTHONUNBUFFERED: '1' 
  };
  
  console.log('Spawning backend with PATH:', env.PATH);

  pythonProcess = spawn('uv', ['run', '-m', 'openrelife.app'], {
    cwd: projectRoot,
    shell: true,
    env: env,
    detached: true
  });
  
  pythonProcess.on('error', (err) => {
    console.error('Failed to start python process:', err);
    dialog.showErrorBox('Backend Error', `Failed to start backend: ${err.message}. Make sure 'uv' is installed.`);
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    // Werkzeug logs to stderr by default, treat as info
    const str = data.toString();
    if (str.includes('Error:') || str.includes('Exception:') || str.includes('Traceback')) {
        console.error(`Backend Error: ${str}`);
    } else {
        console.log(`Backend Log: ${str}`); 
    }
  });

  pythonProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
    pythonProcess = null;
  });
}

function stopBackend() {
  if (pythonProcess) {
    console.log('Stopping backend...');
    // Kill the process group to ensure children (python) are killed since we used shell: true
    if (process.platform === 'win32') {
        spawn("taskkill", ["/pid", pythonProcess.pid, '/f', '/t']);
    } else {
        try {
            // Kill the entire process group
            // This requires the process to be spawned with detached: true
            process.kill(-pythonProcess.pid, 'SIGTERM'); 
        } catch (err) {
            console.error('Failed to kill process group:', err);
            // Fallback
            try {
                pythonProcess.kill();
            } catch (e) {
                console.error('Failed to kill process:', e);
            }
        }
    }
    pythonProcess = null;
  }
}

app.whenReady().then(() => {
  // Start backend server
  startBackend();

  // Set app icon (works for dock in dev mode)
  if (process.platform === 'darwin') {
    app.dock.setIcon(path.join(__dirname, 'app-icon.png'));
  }

  // Create tray icon first
  createTray();
  
  // Check initial recording status
  checkRecordingStatus();
  
  // Don't show app in dock
  app.dock.hide();

  // Register global shortcut: Cmd+Shift+Space
  const ret = globalShortcut.register('CommandOrControl+Shift+Space', () => {
    console.log('🎯 Hotkey pressed: Cmd+Shift+Space');
    if (mainWindow && mainWindow.isVisible()) {
      return;
    }
    showWindow();
  });

  if (!ret) {
    console.error('❌ Failed to register global shortcut');
  }

  // ESC to hide window
  globalShortcut.register('Escape', () => {
    if (mainWindow && mainWindow.isVisible()) {
      console.log('🔒 ESC pressed - hiding window');
      hideWindow();
    }
  });

  console.log('='.repeat(50));
  console.log('🎯 OpenReLife Electron App');
  console.log('='.repeat(50));
  console.log('⌨️  Cmd+Shift+Space: Open/Focus OpenReLife');
  console.log('⎋  ESC: Close OpenReLife window');
  console.log('📍 Tray icon: Click to open');
  console.log('='.repeat(50));

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // Keep app running even if window is closed
  // Only quit if explicitly requested
  if (app.isQuitting) {
    app.quit();
  }
});

app.on('will-quit', () => {
  // Unregister all shortcuts
  globalShortcut.unregisterAll();
  stopBackend();
});

// Prevent app from quitting
app.on('before-quit', (event) => {
  stopBackend();
  // Allow quit only if explicitly requested
});
