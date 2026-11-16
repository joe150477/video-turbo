interface ErrorBannerProps {
  message: string
  onRetry?: () => void
}

// The single place errors get rendered anywhere in the app. It only ever
// receives short, pre-translated Spanish text (see app/utils/error_messages.py)
// — never a raw exception, a stack trace, or an HTTP status code.
export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-center dark:border-red-900 dark:bg-red-950"
    >
      <p className="text-sm text-red-700 dark:text-red-300">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
