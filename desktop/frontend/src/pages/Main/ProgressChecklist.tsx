import { useQuery } from '@tanstack/react-query'
import { ErrorBanner } from '../../components/ErrorBanner'
import { Button } from '../../components/Button'
import { api } from '../../api/client'
import { TASK_STATE_COMPLETE, TASK_STATE_FAILED, type TaskStage } from '../../api/types'

interface ChecklistStep {
  stage: TaskStage
  label: string
}

// Reflects the real pipeline order in app/services/task.py::_run_pipeline —
// showing steps out of order (or steps that do not really exist as separate
// checkpoints) would be worse than a plain progress bar.
const STEPS: ChecklistStep[] = [
  { stage: 'script', label: 'Generando guion' },
  { stage: 'terms', label: 'Buscando ideas para las imágenes' },
  { stage: 'audio', label: 'Generando voz' },
  { stage: 'subtitle', label: 'Creando subtítulos' },
  { stage: 'materials', label: 'Descargando vídeos' },
  { stage: 'video', label: 'Exportando vídeo' },
]

const STAGE_ORDER: Record<TaskStage, number> = {
  script: 0,
  terms: 1,
  audio: 2,
  subtitle: 3,
  materials: 4,
  video: 5,
  done: 6,
}

interface ProgressChecklistProps {
  taskId: string
  onRetry: () => void
  onCreateAnother: () => void
}

export function ProgressChecklist({ taskId, onRetry, onCreateAnother }: ProgressChecklistProps) {
  const { data: task } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => api.getTask(taskId),
    refetchInterval: (query) => {
      const state = query.state.data?.state
      const finished = state === TASK_STATE_COMPLETE || state === TASK_STATE_FAILED
      return finished ? false : 1500
    },
  })

  if (!task) {
    return <p className="p-6 text-center text-sm text-[var(--color-text-muted)]">Iniciando…</p>
  }

  if (task.state === TASK_STATE_FAILED) {
    return (
      <div className="mx-auto flex max-w-md flex-col gap-4 p-6">
        <ErrorBanner
          message={task.error_message ?? 'No se pudo generar el vídeo. Inténtalo de nuevo.'}
          onRetry={onRetry}
        />
        <Button variant="ghost" onClick={onCreateAnother}>
          Volver a empezar
        </Button>
      </div>
    )
  }

  const isComplete = task.state === TASK_STATE_COMPLETE
  const currentStageOrder = isComplete ? STEPS.length : STAGE_ORDER[task.stage ?? 'script']

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 p-6">
      <div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-border)]">
          <div
            className="h-full bg-[var(--color-primary)] transition-all"
            style={{ width: `${task.progress}%` }}
          />
        </div>
        <p className="mt-1 text-right text-xs text-[var(--color-text-muted)]">{task.progress}%</p>
      </div>

      <ul className="flex flex-col gap-2 text-sm">
        {STEPS.map((step) => {
          const stepOrder = STAGE_ORDER[step.stage]
          const status =
            stepOrder < currentStageOrder ? 'done' : stepOrder === currentStageOrder ? 'active' : 'pending'
          return (
            <li key={step.stage} className="flex items-center gap-2">
              <span
                className={
                  status === 'done'
                    ? 'text-[var(--color-success)]'
                    : status === 'active'
                      ? 'animate-pulse text-[var(--color-primary)]'
                      : 'text-[var(--color-text-muted)]'
                }
              >
                {status === 'done' ? '✓' : status === 'active' ? '●' : '○'}
              </span>
              <span className={status === 'pending' ? 'text-[var(--color-text-muted)]' : ''}>
                {step.label}
              </span>
            </li>
          )
        })}
      </ul>

      {isComplete && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-[var(--color-border)] p-4">
          <p className="text-sm font-medium text-[var(--color-success)]">¡Tu vídeo está listo!</p>
          {task.videos?.[0] && (
            <video src={task.videos[0]} controls className="w-full rounded-lg" />
          )}
          <div className="flex gap-3">
            {task.videos?.[0] && (
              <a href={task.videos[0]} download>
                <Button variant="secondary">Guardar vídeo</Button>
              </a>
            )}
            <Button onClick={onCreateAnother}>Crear otro</Button>
          </div>
        </div>
      )}
    </div>
  )
}
