"use client"

export default function DashboardError({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  console.error("[dashboard-error-boundary]", error)

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-5">
        <h2 className="text-lg font-semibold">Dashboard failed to load</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Something went wrong while rendering this page. You can retry without signing out.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Retry
        </button>
      </div>
    </div>
  )
}
