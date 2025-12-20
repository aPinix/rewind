const { app, BrowserWindow, globalShortcut, screen, Tray, Menu, nativeImage } = require('electron');
const path = require('path');

const OPENRECALL_URL = 'http://localhost:8082';
let mainWindow = null;
let tray = null;

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
    simpleFullscreen: true
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
    mainWindow.setSimpleFullScreen(true);
    mainWindow.show();
    mainWindow.focus();
  }
}

function hideWindow() {
  if (mainWindow) {
    mainWindow.setSimpleFullScreen(false);
    setTimeout(() => {
      if (mainWindow) {
        mainWindow.hide();
      }
    }, 100);
  }
}

function createTray() {
  const iconPath = path.join(__dirname, 'tray-iconTemplate.png');
  const icon = nativeImage.createFromPath(iconPath);
  // if you want to resize it, be careful, it creates a copy
  const trayIcon = icon.resize({ width: 22 });
  // here is the important part (has to be set on the resized version)
  trayIcon.setTemplateImage(true);
  tray = new Tray(trayIcon);
  
  const contextMenu = Menu.buildFromTemplate([
    { 
      label: 'Show OpenRecall', 
      click: () => showWindow(),
      accelerator: 'CommandOrControl+Shift+Space'
    },
    { type: 'separator' },
    { 
      label: 'About OpenRecall',
      click: () => {
        console.log('OpenRecall v1.0.0 - Screen Memory for macOS');
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
  
  tray.setToolTip('OpenRecall - Cmd+Shift+Space to open');
  tray.setContextMenu(contextMenu);
}

app.whenReady().then(() => {
  // Create tray icon first
  createTray();
  
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
  console.log('🎯 OpenRecall Electron App');
  console.log('='.repeat(50));
  console.log('⌨️  Cmd+Shift+Space: Open/Focus OpenRecall');
  console.log('⎋  ESC: Close OpenRecall window');
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
