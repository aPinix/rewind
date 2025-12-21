# Electron App - Changelog

## v1.1.0 - Tray Icon & ESC Fix

### 🎯 Nuove Funzionalità
- **Icona Tray**: App vive nella barra menu (tray), non più nel Dock
- **Menu Tray**: Click destro per menu con "Show", "About", "Quit"
- **Click Icona**: Click sull'icona tray apre OpenReLife

### 🐛 Bug Fix
- **ESC Fix**: Risolto bug dove servivano 2x ESC per chiudere
  - Prima: ESC esce da fullscreen, poi serve ESC di nuovo
  - Ora: ESC chiude immediatamente, gestendo automaticamente il fullscreen
  
### ⚙️ Miglioramenti Tecnici
- `skipTaskbar: true` - App non appare nel Dock
- `simpleFullscreen: true` - Transizioni fullscreen più rapide
- `app.dock.hide()` - Nasconde icona Dock completamente
- Listener `leave-full-screen` per sincronizzazione corretta

### 📝 Comportamento
1. All'avvio, app si nasconde automaticamente
2. Solo icona nella tray è visibile
3. Cmd+Shift+Space o click icona → apre fullscreen
4. ESC → chiude immediatamente (1x, non 2x!)
5. Cmd+Q → esce completamente

### 🔧 File Modificati
- `main.js`: Aggiunto Tray, fix hideWindow(), dock.hide()
- `README.md`: Documentazione aggiornata
- `package.json`: (nessuna modifica)

## v1.0.0 - Versione Iniziale
- App Electron base
- Shortcuts globali (Cmd+Shift+Space, ESC)
- Fullscreen support
- Backend integration
