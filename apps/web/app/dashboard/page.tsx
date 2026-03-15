"use client"

import { QuickStats } from "@/components/quick-stats"
import { DailyDigest } from "@/components/daily-digest"
import { IntegrationCards } from "@/components/integration-cards"
import { PdfUpload } from "@/components/pdf-upload"
import { RuntimeGuard } from "@/components/runtime-guard"
import { useSession } from "next-auth/react"
import { useEffect } from "react"

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return { text: "Good morning", emoji: "☀️" }
  if (h < 17) return { text: "Good afternoon", emoji: "🌤️" }
  return { text: "Good evening", emoji: "🌙" }
}

export default function DashboardPage() {
  const { data: session } = useSession()
  const userName = typeof session?.user?.name === "string" ? session.user.name : ""
  const firstName = userName.trim() ? userName.split(" ")[0] : "there"
  const greeting = getGreeting()

  useEffect(() => {
    console.debug("[dashboard] session snapshot", {
      hasSession: Boolean(session),
      email: session?.user?.email || null,
      name: session?.user?.name || null,
    })
  }, [session])

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-primary/10 bg-gradient-to-br from-primary/10 via-accent/5 to-card px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{greeting.emoji}</span>
          <h1 className="text-2xl font-bold tracking-tight">
            {greeting.text}, {firstName}
          </h1>
        </div>
        <p className="mt-2 text-base text-muted-foreground">
          Your daily school updates, in one calm place.
        </p>
      </section>

      {/* First: Today's Digest */}
      <RuntimeGuard name="daily-digest">
        <DailyDigest />
      </RuntimeGuard>

      {/* Then: Upcoming Events, Children, Digests Left */}
      <RuntimeGuard name="quick-stats">
        <QuickStats />
      </RuntimeGuard>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-8">
          <RuntimeGuard name="integration-cards">
            <IntegrationCards />
          </RuntimeGuard>
        </div>
        <div className="space-y-8">
          <RuntimeGuard name="pdf-upload">
            <PdfUpload />
          </RuntimeGuard>
        </div>
      </div>
    </div>
  )
}
