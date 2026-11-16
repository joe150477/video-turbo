import { useState } from 'react'
import { CreateVideoTab } from './CreateVideoTab'
import { SettingsTab } from './SettingsTab'

type Tab = 'create' | 'settings'

export function MainApp() {
  const [tab, setTab] = useState<Tab>('create')

  return (
    <div className="flex min-h-full flex-col">
      <header className="flex items-center justify-center gap-1 border-b border-[var(--color-border)] p-3">
        <button
          type="button"
          onClick={() => setTab('create')}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === 'create'
              ? 'bg-[var(--color-primary)] text-white'
              : 'text-[var(--color-text-muted)]'
          }`}
        >
          Crear vídeo
        </button>
        <button
          type="button"
          onClick={() => setTab('settings')}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === 'settings'
              ? 'bg-[var(--color-primary)] text-white'
              : 'text-[var(--color-text-muted)]'
          }`}
        >
          Configuración
        </button>
      </header>
      <main className="flex-1 overflow-y-auto">
        {tab === 'create' ? <CreateVideoTab /> : <SettingsTab />}
      </main>
    </div>
  )
}
