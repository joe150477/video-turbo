import { BrowserWindow, app, dialog, shell } from 'electron'
import * as path from 'node:path'
import { BackendManager, hasActiveTask } from './backend-manager'
import { registerIpcHandlers } from './ipc-handlers'
import { logger } from './logger'

const MAX_BACKEND_START_ATTEMPTS = 3
const DEV_FRONTEND_URL = 'http://localhost:5173'

const backendManager = new BackendManager()
let mainWindow: BrowserWindow | null = null
let quitConfirmed = false

// A second launch (double-clicking the app icon while it's already open)
// must not spawn a second backend process on top of the first.
const gotSingleInstanceLock = app.requestSingleInstanceLock()
if (!gotSingleInstanceLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.whenReady().then(startApp)
}

async function startApp(): Promise<void> {
  let attempt = 0
  let started = false

  while (attempt < MAX_BACKEND_START_ATTEMPTS && !started) {
    attempt += 1
    try {
      // Kill any backend left over from a previous failed attempt before
      // spawning a new one — otherwise multiple backends fight over the
      // same port and none of them ever becomes reachable.
      await backendManager.stop()
      await backendManager.start()
      started = true
    } catch (error) {
      logger.error(`backend failed to start (attempt ${attempt}/${MAX_BACKEND_START_ATTEMPTS}): ${error}`)
    }
  }

  if (!started) {
    await showStartupFailureDialog()
    app.quit()
    return
  }

  registerIpcHandlers(backendManager, () => mainWindow)
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
}

async function showStartupFailureDialog(): Promise<void> {
  const result = await dialog.showMessageBox({
    type: 'error',
    title: 'No se pudo iniciar MoneyPrinterTurbo',
    message: 'La aplicación no pudo iniciarse correctamente. Inténtalo de nuevo más tarde.',
    detail: `Si el problema continúa, comparte este archivo de registro con soporte:\n${logger.logFilePath}`,
    buttons: ['Cerrar', 'Ver registro'],
  })
  if (result.response === 1) {
    shell.showItemInFolder(logger.logFilePath)
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    title: 'MoneyPrinterTurbo',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  if (app.isPackaged) {
    // Load the SPA over HTTP from the bundled backend (which serves
    // MPT_FRONTEND_DIR), mirroring the dev server. Loading via file://
    // breaks the SPA's absolute asset paths and ES modules → blank window.
    mainWindow.loadURL(`http://127.0.0.1:${backendManager.port}/`)
  } else {
    mainWindow.loadURL(DEV_FRONTEND_URL)
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', async (event) => {
  if (quitConfirmed || !backendManager.isRunning()) {
    return
  }

  event.preventDefault()

  const busy = backendManager.hasPort() && (await hasActiveTask(backendManager.port))
  if (busy) {
    const result = await dialog.showMessageBox({
      type: 'warning',
      title: 'Hay un vídeo generándose',
      message: 'Hay un vídeo generándose. ¿Seguro que quieres salir? El progreso se perderá.',
      buttons: ['Cancelar', 'Salir de todos modos'],
      defaultId: 0,
      cancelId: 0,
    })
    if (result.response !== 1) {
      return
    }
  }

  quitConfirmed = true
  await backendManager.stop()
  app.quit()
})
