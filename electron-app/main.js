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
    skipTaskbar: true,  // Don't show in dock when hidden
    fullscreenable: true,
    simpleFullscreen: true  // Use simple fullscreen for faster transitions
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
    mainWindow.show();
    mainWindow.setFullScreen(true);
    mainWindow.focus();
  }
}

function hideWindow() {
  if (mainWindow) {
    // Check if in fullscreen
    if (mainWindow.isFullScreen()) {
      // Exit fullscreen first, then hide after animation
      mainWindow.once('leave-full-screen', () => {
        mainWindow.hide();
      });
      mainWindow.setFullScreen(false);
    } else {
      // Not in fullscreen, hide immediately
      mainWindow.hide();
    }
  }
}

function createTray() {
  // Try to load icon from file, fallback to embedded icon
  let icon;
  const iconPath = path.join(__dirname, 'tray-icon.png');
  const fs = require('fs');
  
  if (fs.existsSync(iconPath)) {
    icon = nativeImage.createFromPath(iconPath);
  } else {
    // Fallback: simple embedded icon (small circle)
    icon = nativeImage.createFromDataURL(
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAA7AAAAOwBeShxvQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAFNSURBVFiF7ZaxSgNBEIa/2SwJBEttLGwtLSzt7KwsLe0sLO0sLO0sLIR0NoKFhYWFhYWFhYWFhYWFhYWFhVhY+AI+gI8gwZ3lLuTubvcul+TD7c7Mf/+dmd0dWGeddVoVIAU8AA/AM5ACEn9FTgJ54N0xnwgJ4BJ4rYnzwCWQuCsCwngduPpL5BRwA7zVxDlgFpgFboFXYAaY+xPkJPAGvNTEWWAe2ATOgYS2D20MzAMbwJnMXQIXfsXNkRvAVU2cBZaBe2AJSAbIScA9sAwsy7odYAQ4AW6ADeCkWUEZn7x/bZz3LyQHNx51wCvAMzACPACHQAZ41X0yMfKSMgq8AweBJSAP5IBp4A3YBg6AI+Aw9ANovvfAPlAEisBOHdltkS3HNoAsUAL2gD3gCNgFdoA9YNt1D/wHsM466/wAX5hiiQaKfN3cAAAAAElFTkSuQmCC'
    );
  }
  
  tray = new Tray(icon.resize({ width: 16, height: 16 }));
  tray.setPressedImage(icon.resize({ width: 16, height: 16 }));
  
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
  
  // Click on tray icon to show window
  tray.on('click', () => {
    showWindow();
  });
}

app.whenReady().then(() => {
  // Don't show app in dock
  app.dock.hide();
  
  // Create tray icon
  createTray();
  
  // Create window but don't show it
  createWindow();

  // Register global shortcut: Cmd+Shift+Space
  const ret = globalShortcut.register('CommandOrControl+Shift+Space', () => {
    console.log('🎯 Hotkey pressed: Cmd+Shift+Space');
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
