# 🚀 OpenRecall Global Hotkey Setup

Launch OpenRecall with **Cmd+Shift+Space** (just like Rewind.ai)!

**New:** Runs like an Electron app with no visible terminals, toolbars, or extensions!

## 🎯 Quick Install

```bash
./install.sh
```

This will:
- Install dependencies (pynput)
- Create OpenRecall.app
- Set up everything automatically

## 🚀 Quick Start

### Option 1: Launch as macOS App (Recommended)

1. Open **Spotlight** (Cmd+Space)
2. Type "OpenRecall" and press Enter
3. Grant Accessibility permissions if prompted
4. Press **Cmd+Shift+Space** to open OpenRecall anytime!

### Option 2: Launch from Terminal

```bash
./start_openrecall.sh start
```

The app runs completely in the background - no visible terminal windows!

## ⌨️ Keyboard Shortcuts

- **Cmd+Shift+Space**: Open OpenRecall in fullscreen (like Electron app)
- **ESC**: Close the OpenRecall window
- No need to quit - it stays running in the background!

## 🛠️ Management Commands

```bash
# Check if running
./start_openrecall.sh status

# Stop the app
./start_openrecall.sh stop

# Restart the app
./start_openrecall.sh restart
```

## ✨ Features

- 🎨 **Electron-like experience**: Opens in Chrome's app mode (no bookmarks, no extensions)
- 👻 **Invisible**: No visible terminal windows, runs silently in background
- ⚡ **Fast**: Opens instantly with Cmd+Shift+Space
- 🔒 **ESC to close**: Press ESC to close the window (app keeps running)
- 📝 **Logging**: All logs saved to `logs/` directory
- 🔄 **Auto-restart**: Automatically restarts if crashed

## ⚙️ Setup Requirements

### Grant Accessibility Permissions (Required)

The hotkey listener needs accessibility permissions:

1. Open **System Settings** (or System Preferences)
2. Go to **Privacy & Security** > **Accessibility**
3. When you first launch, macOS will prompt you to add **Google Chrome** or **Python**
4. Click "Open System Settings" and enable the checkbox
5. You may need to restart the app after granting permissions

### Browser Requirements

The app will open in Chrome's **app mode** (clean, no UI):
- **Google Chrome** - Recommended (opens in app mode like Electron)
- **Safari** - Fallback option (less clean UI)

## 📁 File Structure

```
openrecall/
├── install.sh              # One-click installation
├── start_openrecall.sh     # Start/stop/status commands
├── launch_openrecall.py    # Hotkey listener (Cmd+Shift+Space, ESC)
├── create_app.sh           # Create OpenRecall.app
├── logs/                   # Log files
│   ├── openrecall.log     # Server logs
│   ├── hotkey.log         # Hotkey listener logs
│   └── openrecall.pid     # Process ID (when running)
└── HOTKEY_SETUP.md        # This file
```

## 🐛 Troubleshooting

### Hotkey not working?

1. **Grant Accessibility permissions** (most common issue)
   - System Settings > Privacy & Security > Accessibility
   - Add Chrome/Python and enable
   
2. **Check if app is running**
   ```bash
   ./start_openrecall.sh status
   ```

3. **Check logs**
   ```bash
   tail -f logs/hotkey.log
   ```

### Window doesn't open?

1. **Make sure Chrome is installed** at `/Applications/Google Chrome.app`
2. **Check server is running**
   ```bash
   curl http://localhost:8082
   ```
3. **Check server logs**
   ```bash
   tail -f logs/openrecall.log
   ```

### ESC not closing window?

- ESC only works when the OpenRecall window is **not focused**
- If inside the window, click outside first, then press ESC
- Or just press Cmd+W to close normally

### App doesn't start in background?

1. **Check for errors**
   ```bash
   ./start_openrecall.sh start
   cat logs/openrecall.log
   ```

2. **Try manual start** (to see errors)
   ```bash
   uv run -m openrecall.app
   ```

### Multiple instances running?

```bash
# Stop all
./start_openrecall.sh stop

# Check status
./start_openrecall.sh status

# Start fresh
./start_openrecall.sh start
```

## 🎨 Customization

### Change the hotkey

Edit `launch_openrecall.py`:

```python
# Change from Cmd+Shift+Space to something else
if all([
    Key.cmd in current_keys,      # Change to Key.alt for Option key
    Key.shift in current_keys,    # Remove this line to not require Shift
    Key.space in current_keys     # Change to another key
]):
```

### Change the port

Edit `launch_openrecall.py`:

```python
OPENRECALL_URL = "http://localhost:8082"  # Change port here
```

Also update the app server port in your OpenRecall config.

### Use different browser

Edit `launch_openrecall.py` and modify the `open_fullscreen_browser()` function.

## 🎉 Tips & Tricks

1. **Add to Login Items** to auto-start on boot:
   - System Settings > General > Login Items
   - Add OpenRecall.app

2. **Create a dock icon** (if you want):
   - The app runs hidden by default
   - Edit `Info.plist` and set `LSUIElement` to `0`

3. **View logs in real-time**:
   ```bash
   tail -f logs/openrecall.log logs/hotkey.log
   ```

4. **Uninstall**:
   ```bash
   ./start_openrecall.sh stop
   rm -rf ~/Applications/OpenRecall.app
   rm -rf logs/
   ```

## 📝 Notes

- The app uses Chrome's `--app` flag to create an Electron-like experience
- All terminal output is logged to `logs/` directory
- The app stays running in background until you explicitly stop it
- Pressing ESC closes the window but keeps the app running
- Press Cmd+Shift+Space again to reopen instantly

## 🎉 Enjoy!

Press **Cmd+Shift+Space** anytime to access your screen history! 🚀

No visible windows, no clutter, just pure functionality. 💎
