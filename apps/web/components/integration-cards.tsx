"use client"

import { useEffect, useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  CheckCircle2,
  Settings,
  Mail,
  FolderOpen,
  GraduationCap,
  Puzzle,
  Sun,
  Sparkles,
  Globe,
  Calendar,
  FileText,
  Rss,
} from "lucide-react"
import Link from "next/link"

interface IntegrationDef {
  key: string
  name: string
  description: string
  status: string
  color: string
  emoji: string
  group: "official" | "public_sources"
  badge?: string
}

const DEFAULTS: IntegrationDef[] = [
  // Official integrations
  { key: "gmail", name: "Gmail", description: "School emails and newsletters", status: "not_connected", color: "bg-red-500/10 text-red-600", emoji: "📧", group: "official" },
  { key: "gdrive", name: "Google Drive", description: "Documents and permission slips", status: "not_connected", color: "bg-amber-500/10 text-amber-600", emoji: "📁", group: "official" },
  // Public sources (auto-discovered)
  { key: "public_website", name: "School Website", description: "Announcements and news from your child's school", status: "not_connected", color: "bg-sky-500/10 text-sky-600", emoji: "🌐", group: "public_sources", badge: "auto-discovered" },
  { key: "public_calendar", name: "School Calendar", description: "Events, holidays, and important dates", status: "not_connected", color: "bg-indigo-500/10 text-indigo-600", emoji: "📅", group: "public_sources", badge: "auto-discovered" },
]

const GROUP_INFO = {
  official: {
    title: "Official Integrations",
    subtitle: "Connect directly with OAuth or API key",
    icon: "🔗",
  },
  public_sources: {
    title: "Public Sources",
    subtitle: "Auto-discovered from your child's school — no setup needed",
    icon: "🌐",
  },
}

export function IntegrationCards() {
  const [integrations, setIntegrations] = useState<IntegrationDef[]>(DEFAULTS)

  useEffect(() => {
    fetch("/api/integrations/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.integrations) {
          setIntegrations((prev) =>
            prev.map((i) => ({
              ...i,
              status: data.integrations[i.key]?.status || i.status,
            }))
          )
        }
      })
      .catch(() => { /* keep defaults */ })
  }, [])

  const groups: ("official" | "public_sources")[] = [
    "official",
    "public_sources",
  ]

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔌</span>
          <div>
            <h2 className="text-lg font-bold text-foreground">
              Connected Platforms
            </h2>
            <p className="text-sm text-muted-foreground">
              All your school communication in one place
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="font-semibold" asChild>
          <Link href="/settings">
            <Settings className="mr-2 h-4 w-4" />
            Manage
          </Link>
        </Button>
      </div>

      <div className="rounded-xl border border-primary/10 bg-primary/5 p-4 mb-6">
        <div className="flex items-start gap-3">
          <span className="text-lg mt-0.5">🧠</span>
          <div>
            <p className="text-sm font-medium text-foreground">Smart Email Parsing</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Parently automatically detects and parses emails from <strong>ClassDojo</strong>, <strong>Brightwheel</strong>, <strong>Skyward</strong>, and <strong>Kumon</strong> — combined with your school&apos;s public district calendar, website, and other feeds to build your daily digest. Just connect Gmail and we handle the rest.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-8">
        {groups.map((groupKey) => {
          const info = GROUP_INFO[groupKey]
          const items = integrations.filter((i) => i.group === groupKey)
          const connectedCount = items.filter((i) => i.status === "connected").length

          return (
            <div key={groupKey}>
              <div className="mb-3 flex items-center gap-2">
                <span className="text-lg">{info.icon}</span>
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    {info.title}
                    {connectedCount > 0 && (
                      <Badge
                        variant="outline"
                        className="ml-2 gap-1 border-emerald-500/20 bg-emerald-500/10 text-emerald-600 text-[10px]"
                      >
                        {connectedCount} active
                      </Badge>
                    )}
                  </h3>
                  <p className="text-xs text-muted-foreground">{info.subtitle}</p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((integration) => (
                  <Card
                    key={integration.key}
                    className={`group transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 ${
                      integration.status === "connected"
                        ? "ring-1 ring-emerald-500/20 border-emerald-200/50"
                        : "border-border/60"
                    }`}
                  >
                    <CardHeader className="pb-2 pt-4 px-4">
                      <div className="flex items-start justify-between">
                        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${integration.color} transition-transform duration-200 group-hover:scale-110`}>
                          <span className="text-lg">{integration.emoji}</span>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          {integration.status === "connected" ? (
                            <Badge
                              variant="outline"
                              className="gap-1 border-emerald-500/20 bg-emerald-500/10 text-emerald-600 text-[10px]"
                            >
                              <CheckCircle2 className="h-3 w-3" />
                              Connected
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="gap-1 text-muted-foreground text-[10px]">
                              Not connected
                            </Badge>
                          )}
                          {integration.badge && (
                            <Badge variant="outline" className="text-[9px] text-muted-foreground border-border/40">
                              {integration.badge}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <CardTitle className="text-sm font-bold mt-1">{integration.name}</CardTitle>
                      <CardDescription className="text-[11px] leading-tight">
                        {integration.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="px-4 pb-3">
                      <div className="flex items-center justify-between">
                        {integration.status === "connected" ? (
                          <span className="flex items-center gap-1 text-xs text-emerald-600">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            Active
                          </span>
                        ) : groupKey === "public_sources" ? (
                          <span className="text-[11px] text-muted-foreground">
                            Auto
                          </span>
                        ) : (
                          <span className="text-[11px] text-muted-foreground">
                            Not configured
                          </span>
                        )}
                        <Button
                          variant={integration.status === "connected" ? "ghost" : "default"}
                          size="sm"
                          className={`h-7 text-[11px] font-semibold ${integration.status !== "connected" ? "shadow-sm" : ""}`}
                          asChild
                        >
                          <Link href="/settings">
                            {integration.status === "connected" ? "View" : "Connect →"}
                          </Link>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
