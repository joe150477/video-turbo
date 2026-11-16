export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-6 text-sm text-[var(--color-text-muted)]">
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-primary)]"
        aria-hidden="true"
      />
      {label && <p>{label}</p>}
    </div>
  )
}
