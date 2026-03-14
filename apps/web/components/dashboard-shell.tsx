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
    fetch("/api/auth/me")
      .then((r) => r.json())
      .then((data) => {
        if (data.ok && data.user && !data.user.onboarding_complete) {
          router.replace("/onboarding")
        } else {
          setChecked(true)
        }
      })
      .catch(() => setChecked(true))
  }, [router])

  if (!checked) return null
  return <>{children}</>
}
