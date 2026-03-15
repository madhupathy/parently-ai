import type React from "react"
import { Header } from "@/components/header"
import { DashboardShell } from "@/components/dashboard-shell"
import { MobileNav } from "@/components/mobile-nav"
import { RuntimeGuard } from "@/components/runtime-guard"

export const dynamic = "force-dynamic"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background">
      <RuntimeGuard name="header">
        <Header />
      </RuntimeGuard>
      <DashboardShell>
        <main className="mx-auto max-w-7xl px-4 py-6 pb-24 sm:px-6 lg:px-8 md:pb-6">
          {children}
        </main>
      </DashboardShell>
      <RuntimeGuard name="mobile-nav">
        <MobileNav />
      </RuntimeGuard>
    </div>
  )
}
