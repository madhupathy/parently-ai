"use client"

import { QuickStats } from "@/components/quick-stats"
import { DailyDigest } from "@/components/daily-digest"
import { IntegrationCards } from "@/components/integration-cards"
import { PdfUpload } from "@/components/pdf-upload"
import { useSession } from "next-auth/react"
import { Coffee, Sunset, Moon } from "lucide-react"

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return { text: "Good morning", emoji: "☀️", Icon: Coffee }
  if (h < 17) return { text: "Good afternoon", emoji: "🌤️", Icon: Sunset }
  return { text: "Good evening", emoji: "🌙", Icon: Moon }
}

export default function DashboardPage() {
  const { data: session } = useSession()
  const firstName = session?.user?.name?.split(" ")[0] || "there"
  const greeting = getGreeting()

  return (
    <div className="space-y-8">
      {/* Welcome Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-primary/10 bg-gradient-to-br from-primary/15 via-accent/10 to-card px-6 py-10 sm:px-12 sm:py-12">
        {/* Decorative elements */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-primary/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 -left-16 h-48 w-48 rounded-full bg-accent/15 blur-3xl" />
        <div className="pointer-events-none absolute right-1/3 top-1/4 h-32 w-32 rounded-full bg-primary/8 blur-2xl" />

        <div className="relative flex items-start justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <span className="text-3xl">{greeting.emoji}</span>
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                {greeting.text}, {firstName}
              </h1>
            </div>
            <p className="mt-2 max-w-md text-base text-muted-foreground">
              Here&apos;s your calm overview of what&apos;s happening with your kids&apos; school today.
            </p>
          </div>
          <div className="hidden sm:block text-6xl opacity-20 select-none">
            📚
          </div>
        </div>
      </section>

      <QuickStats />

      {/* Main content grid */}
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <DailyDigest />
        </div>
        <div className="space-y-8">
          <PdfUpload />
        </div>
      </div>

      <IntegrationCards />
    </div>
  )
}
