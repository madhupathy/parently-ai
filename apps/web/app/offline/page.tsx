"use client"

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <span className="text-6xl" role="img" aria-label="No connection">
        📡
      </span>
      <h1 className="text-2xl font-bold tracking-tight">You&apos;re offline</h1>
      <p className="max-w-sm text-muted-foreground">
        Parently can&apos;t reach the server right now. Check your internet connection and try again.
      </p>
      <button
        className="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        onClick={() => window.location.reload()}
      >
        Try again
      </button>
    </div>
  )
}
