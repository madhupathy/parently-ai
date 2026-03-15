"use client"

import type React from "react"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useUserSync } from "@/hooks/use-user-sync"

export function DashboardShell({ children }: { children: React.ReactNode }) {
  useUserSync()
  const router = useRouter()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 4000)

    fetch("/api/auth/me", { signal: controller.signal, cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok && data.user && !data.user.onboarding_complete) {
          router.replace("/onboarding")
          return
        }
        setChecked(true)
      })
      .catch(() => setChecked(true))
      .finally(() => clearTimeout(timeout))

    return () => {
      clearTimeout(timeout)
      controller.abort()
    }
  }, [router])

  if (!checked) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground">
        Loading dashboard...
      </div>
    )
  }
  return <>{children}</>
}
