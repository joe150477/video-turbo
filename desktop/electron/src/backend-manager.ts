import { app } from 'electron'
import { type ChildProcess, spawn } from 'node:child_process'
import * as path from 'node:path'
import treeKill from 'tree-kill'
import { logger } from './logger'
import { findAvailablePort } from './port-finder'

const PREFERRED_PORT = 8080
const HEALTH_CHECK_INTERVAL_MS = 300
// The frozen (PyInstaller) backend can take ~20s to import its full graph
// (moviepy, numpy, provider SDKs) and start serving on a cold or busy
// machine. Give it generous headroom so the first attempt succeeds instead
// of timing out and re-spawning.
const HEALTH_CHECK_TIMEOUT_MS = 45000

// Mirrors app/models/const.py::TASK_STATE_PROCESSING. Duplicated rather
// than shared because the Electron main process and the Python backend
// have no build-time link to each other.
const TASK_STATE_PROCESSING = 4

export class BackendManager {
  private childProcess: ChildProcess | null = null
  private boundPort: number | null = null

  hasPort(): boolean {
    return this.boundPort !== null
  }

  get port(): number {
    if (this.boundPort === null) {
      throw new Error('backend has not started yet')
    }
    return this.boundPort
  }

  isRunning(): boolean {
    return this.childProcess !== null
  }

  async start(): Promise<number> {
    const port = await findAvailablePort(PREFERRED_PORT)
    this.boundPort = port

    const env: NodeJS.ProcessEnv = {
      ...process.env,
      MPT_PORT: String(port),
      MPT_HOST: '127.0.0.1',
      MPT_USER_DATA_DIR: app.getPath('userData'),
      // So the backend can tell GitHub's latest release from the running app.
      MPT_APP_VERSION: app.getVersion(),
    }

    if (app.isPackaged) {
      // Let the backend serve the built React app over HTTP so the window
      // can load it via http:// (not file://, which blocks the SPA).
      env.MPT_FRONTEND_DIR = path.join(process.resourcesPath, 'frontend')
      const backendDir = path.join(process.resourcesPath, 'backend')
      const executableName =
        process.platform === 'win32' ? 'moneyprinterturbo-backend.exe' : 'moneyprinterturbo-backend'
      const executable = path.join(backendDir, executableName)
      logger.info(`starting packaged backend: ${executable} (port ${port})`)
      this.childProcess = spawn(executable, [], { cwd: backendDir, env })
    } else {
      const repoRoot = path.resolve(__dirname, '..', '..', '..')
      logger.info(`starting dev backend via uv in ${repoRoot} (port ${port})`)
      this.childProcess = spawn('uv', ['run', 'python', 'main.py'], { cwd: repoRoot, env })
    }

    this.childProcess.stdout?.on('data', (chunk: Buffer) => {
      logger.info(`[backend] ${chunk.toString().trim()}`)
    })
    this.childProcess.stderr?.on('data', (chunk: Buffer) => {
      logger.warn(`[backend] ${chunk.toString().trim()}`)
    })
    this.childProcess.on('exit', (code, signal) => {
      logger.warn(`backend process exited (code=${code}, signal=${signal})`)
      this.childProcess = null
    })

    await this.waitUntilHealthy(port)
    return port
  }

  private async waitUntilHealthy(port: number): Promise<void> {
    const deadline = Date.now() + HEALTH_CHECK_TIMEOUT_MS
    while (Date.now() < deadline) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/api/v1/system/ping`)
        if (response.ok) return
      } catch {
        // Backend is not listening yet; keep polling until the deadline.
      }
      await new Promise((resolve) => setTimeout(resolve, HEALTH_CHECK_INTERVAL_MS))
    }
    throw new Error('backend did not become healthy in time')
  }

  async stop(): Promise<void> {
    const proc = this.childProcess
    if (!proc || proc.pid === undefined) {
      return
    }
    await new Promise<void>((resolve) => {
      treeKill(proc.pid as number, 'SIGTERM', () => resolve())
    })
    this.childProcess = null
  }
}

export async function hasActiveTask(port: number): Promise<boolean> {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/v1/tasks?page=1&page_size=50`)
    if (!response.ok) return false
    const body = (await response.json()) as { data?: { tasks?: Array<{ state?: number }> } }
    const tasks = body.data?.tasks ?? []
    return tasks.some((task) => task.state === TASK_STATE_PROCESSING)
  } catch {
    return false
  }
}
