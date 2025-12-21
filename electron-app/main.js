const { app, BrowserWindow, globalShortcut, screen, Tray, Menu, nativeImage, Notification, dialog } = require('electron');
const path = require('path');

const OPENRECALL_URL = 'http://127.0.0.1:8082';
let mainWindow = null;
let tray = null;
let isPaused = false;
let pauseReminderInterval = null;


// Set explicit app name for notifications
if (process.platform === 'darwin') {
  app.setName('OpenReLife');
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

  mainWindow.loadURL(OPENRECALL_URL);

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
    setTimeout(() => {
      if (mainWindow) {
        mainWindow.loadURL(OPENRECALL_URL);
      }
    }, 1000);
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


async function checkRecordingStatus() {
  try {
    const res = await fetch(`${OPENRECALL_URL}/api/recording-status`);
    const data = await res.json();
    isPaused = data.paused;
    updateTrayMenu();
    handlePauseReminder(isPaused);
  } catch (err) {
    console.error('Failed to check recording status:', err);
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
    { type: 'separator' },
    { 
      label: 'About OpenReLife',
      click: () => {
        dialog.showMessageBox({
          type: 'info',
          title: 'About OpenReLife',
          message: 'OpenReLife v1.0.0',
          detail: 'Screen Memory for macOS - made with ❤️ by Porech (powered by AI)',
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


app.whenReady().then(() => {
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
});

// Prevent app from quitting
app.on('before-quit', (event) => {
  // Allow quit only if explicitly requested
});
