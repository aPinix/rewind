#!/usr/bin/env python3
"""
OpenReLife Global Hotkey Launcher
Launch OpenReLife with Cmd+Shift+Space (like Rewind.ai)
"""

import subprocess
import sys
import time
import signal
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

# URL to open
OPENRECALL_URL = "http://localhost:8082"

# Track which keys are currently pressed
current_keys = set()
browser_process = None
window_id = None

def close_openrelife_window():
    """Close the OpenReLife window"""
    global browser_process, window_id
    
    print("🔒 Closing OpenReLife window...")
    
    # Close the specific Chrome window
    applescript = '''
    tell application "Google Chrome"
        set windowList to every window
        repeat with aWindow in windowList
            set tabList to every tab of aWindow
            repeat with aTab in tabList
                if URL of aTab contains "localhost:8082" then
                    close aWindow
                    return
                end if
            end repeat
        end repeat
    end tell
    '''
    
    try:
        subprocess.run(['osascript', '-e', applescript], check=False, 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass
    
    browser_process = None
    window_id = None

def open_fullscreen_browser():
    """Open browser in app mode (like Electron)"""
    global browser_process, window_id
    
    # Try to focus existing window first
    applescript_focus = '''
    tell application "Google Chrome"
        set windowList to every window
        repeat with aWindow in windowList
            set tabList to every tab of aWindow
            repeat with aTab in tabList
                if URL of aTab contains "localhost:8082" then
                    set index of aWindow to 1
                    activate
                    return true
                end if
            end repeat
        end repeat
        return false
    end tell
    '''
    
    try:
        result = subprocess.run(['osascript', '-e', applescript_focus], 
                              capture_output=True, text=True, timeout=2)
        if result.stdout.strip() == 'true':
            print("🔄 Focusing existing window...")
            return
    except:
        pass
    
    print("🚀 Launching OpenReLife...")
    
    # Launch Chrome in app mode (no extensions, no bookmarks bar, minimal UI)
    try:
        browser_process = subprocess.Popen([
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            f'--app={OPENRECALL_URL}',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-sync',
            '--disable-background-networking',
            '--disable-default-apps',
            '--no-first-run',
            '--disable-features=TranslateUI',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a moment for window to open, then fullscreen it
        time.sleep(0.8)
        applescript = '''
        tell application "System Events"
            tell application process "Google Chrome"
                set frontmost to true
                tell window 1
                    set value of attribute "AXFullScreen" to true
                end tell
            end tell
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ OpenReLife opened in app mode")
        
    except FileNotFoundError:
        print("❌ Chrome not found, trying Safari...")
        # Fallback to Safari (no app mode, but clean window)
        applescript = f'''
        tell application "Safari"
            activate
            make new document
            set URL of document 1 to "{OPENRECALL_URL}"
            delay 0.8
            tell application "System Events"
                keystroke "f" using {{command down, control down}}
            end tell
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ OpenReLife opened in Safari")

def on_press(key):
    """Handle key press"""
    global current_keys
    
    # Check for ESC first (close window) - don't add to current_keys
    if key == Key.esc:
        close_openrelife_window()
        return
    
    current_keys.add(key)
    
    # Check for Cmd+Shift+Space (open)
    if all([
        Key.cmd in current_keys or Key.cmd_r in current_keys,
        Key.shift in current_keys or Key.shift_r in current_keys,
        Key.space in current_keys
    ]):
        open_fullscreen_browser()
        current_keys.clear()

def on_release(key):
    """Handle key release"""
    try:
        current_keys.discard(key)
    except KeyError:
        pass

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n👋 Shutting down...")
    close_openrelife_window()
    sys.exit(0)

def main():
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("🎯 OpenReLife Global Hotkey Listener")
    print("=" * 50)
    print(f"⌨️  Cmd+Shift+Space: Open/Focus OpenReLife")
    print(f"⎋  ESC: Close OpenReLife window")
    print(f"⌃  Ctrl+C: Quit listener")
    print("=" * 50)
    print("👂 Listening for hotkeys...")
    print()
    
    # Start listening
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        close_openrelife_window()
        sys.exit(0)
