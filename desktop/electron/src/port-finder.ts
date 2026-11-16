import * as net from 'node:net'

// True if something is already accepting connections on this port on the
// given host. A bind test alone is not enough: a server listening on IPv6
// `[::]:8080` does not stop a bind to IPv4 `127.0.0.1:8080`, yet it can
// still answer requests to that port — which would make our health check
// hit the wrong server. Probing an actual connection catches that case.
function isSomethingListening(port: number, host: string): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket()
    const done = (listening: boolean) => {
      socket.destroy()
      resolve(listening)
    }
    socket.setTimeout(400)
    socket.once('connect', () => done(true))
    socket.once('timeout', () => done(false))
    socket.once('error', () => done(false))
    socket.connect(port, host)
  })
}

function canBind(port: number, host: string): Promise<boolean> {
  return new Promise((resolve) => {
    const tester = net.createServer()
    tester.once('error', () => resolve(false))
    tester.once('listening', () => tester.close(() => resolve(true)))
    tester.listen(port, host)
  })
}

async function isPortFree(port: number): Promise<boolean> {
  // Free only if we can bind it on IPv4 loopback (where the backend listens)
  // AND nothing is already answering on either IPv4 or IPv6 loopback.
  if (!(await canBind(port, '127.0.0.1'))) return false
  if (await isSomethingListening(port, '127.0.0.1')) return false
  if (await isSomethingListening(port, '::1')) return false
  return true
}

// The backend defaults to 8080, but that is not guaranteed to be free on
// the user's machine (another app, or a previous MoneyPrinterTurbo
// instance that did not shut down cleanly). Try a small range instead of
// failing outright.
export async function findAvailablePort(preferred: number, maxAttempts = 20): Promise<number> {
  for (let offset = 0; offset < maxAttempts; offset += 1) {
    const candidate = preferred + offset
    if (await isPortFree(candidate)) {
      return candidate
    }
  }
  throw new Error(`no available port found starting from ${preferred}`)
}
