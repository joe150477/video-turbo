import { app } from 'electron'
import * as fs from 'node:fs'
import * as path from 'node:path'

// A plain-text log the user can attach to a support request. Electron's
// main process console output disappears once the app is packaged (there
// is no terminal), so this is the only place a crash-loop or backend
// startup failure leaves a trace a non-technical user could hand over.
const logDir = path.join(app.getPath('userData'), 'logs')
fs.mkdirSync(logDir, { recursive: true })
const logFilePath = path.join(logDir, 'app.log')

function write(level: string, message: string): void {
  const line = `[${new Date().toISOString()}] ${level} ${message}\n`
  fs.appendFile(logFilePath, line, () => {
    // Best-effort: a failed log write must never crash the app.
  })
}

export const logger = {
  logFilePath,
  info(message: string): void {
    console.log(message)
    write('INFO', message)
  },
  warn(message: string): void {
    console.warn(message)
    write('WARN', message)
  },
  error(message: string): void {
    console.error(message)
    write('ERROR', message)
  },
}
