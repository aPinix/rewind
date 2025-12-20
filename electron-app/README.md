# OpenRecall Electron App

App Electron nativa per macOS che sostituisce Chrome, evitando popup indesiderati.

## 🚀 Avvio Rapido

```bash
cd electron-app
./start.sh
```

Questo script:
1. Avvia automaticamente il backend Python (porta 8082)
2. Installa le dipendenze Electron se necessario
3. Lancia l'app Electron

## ⌨️ Shortcuts

- **Cmd+Shift+Space**: Apri/Mostra OpenRecall
- **ESC**: Nascondi la finestra
- **Cmd+Q**: Esci completamente

## 📦 Setup Iniziale

```bash
cd electron-app
npm install
```

## 🏗️ Costruire l'App

Per creare un'app `.app` standalone:

```bash
npm run build
```

Questo genera un'app in `dist/` che puoi trascinare in `/Applications`.

## 🔧 Sviluppo

### Solo Backend
```bash
cd ..
./start_openrecall.sh start
```

### Solo Electron (backend già avviato)
```bash
cd electron-app
npm start
```

### Fermare Backend
```bash
./start.sh stop
# oppure
cd ..
./start_openrecall.sh stop
```

## ✨ Vantaggi vs Chrome

1. **Nessun popup estensioni**: Finestra pulita dedicata
2. **Controllo completo**: Frame personalizzabile
3. **Prestazioni**: Più leggera di Chrome con profilo completo
4. **Integrazione macOS**: Migliore supporto fullscreen e shortcuts
5. **Privacy**: Sessione isolata senza cookies/cache del browser

## 📝 File Principali

- `main.js`: Processo principale Electron, gestisce finestra e shortcuts
- `preload.js`: Script di sicurezza per il renderer
- `package.json`: Configurazione e dipendenze
- `start.sh`: Script unificato per avvio backend + frontend

## 🐛 Troubleshooting

### Backend non parte
```bash
cd ..
cat logs/openrecall-backend.log
```

### Electron non trova il backend
Verifica che sia in ascolto su porta 8082:
```bash
lsof -i :8082
```

### Reinstallare dipendenze
```bash
rm -rf node_modules package-lock.json
npm install
```
