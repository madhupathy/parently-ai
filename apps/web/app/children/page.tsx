"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, Baby, CalendarDays, AlertCircle, ChevronRight, BookOpen } from "lucide-react"

/* ── Types ──────────────────────────────────────── */

interface ChildProfile {
  id: number
  name: string
  grade: string | null
  school_name: string | null
  teacher_name: string | null
}

interface ChildDigestSummary {
  id: number
  digest_date: string | null
  created_at: string
  item_count: number
  preview: string
}

interface UpcomingEvent {
  subject: string
  body: string
  due_date: string | null
  digest_id: number
  digest_date: string | null
}

interface ActionItem {
  subject: string
  body: string
  due_date: string | null
  digest_id: number
  digest_date: string | null
}

interface ChildDashboardData {
  child_name: string
  child_id: number
  total: number
  digests: ChildDigestSummary[]
  upcoming_events: UpcomingEvent[]
  action_items: ActionItem[]
  loading: boolean
  error: string | null
}

/* ── Helpers ────────────────────────────────────── */

function friendlyDate(dateStr: string | null) {
  if (!dateStr) return ""
  try {
    const d = new Date(dateStr + "T00:00:00")
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
  } catch {
    return dateStr
  }
}

function daysUntil(dateStr: string | null): string {
  if (!dateStr) return ""
  try {
    const due = new Date(dateStr + "T00:00:00")
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const diff = Math.round((due.getTime() - today.getTime()) / 86400000)
    if (diff === 0) return "Today"
    if (diff === 1) return "Tomorrow"
    if (diff < 0) return `${Math.abs(diff)}d ago`
    return `In ${diff}d`
  } catch {
    return ""
  }
}

/* ── Child Card ─────────────────────────────────── */

function ChildCard({ child, data }: { child: ChildProfile; data: ChildDashboardData }) {
  const latestDigest = data.digests[0] ?? null

  return (
    <Card className="overflow-hidden border-border/60 shadow-sm">
      <CardHeader className="bg-gradient-to-br from-primary/5 to-accent/5 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-2xl">
              👧
            </div>
            <div>
              <CardTitle className="text-lg">{child.name}</CardTitle>
              <CardDescription className="text-xs">
                {[child.grade, child.school_name].filter(Boolean).join(" · ") || "No school set"}
                {child.teacher_name && ` · ${child.teacher_name}`}
              </CardDescription>
            </div>
          </div>
          <Button asChild variant="ghost" size="sm" className="shrink-0 gap-1 text-xs">
            <Link href={`/digest`}>
              <BookOpen className="h-3.5 w-3.5" />
              View Digests
            </Link>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-0 divide-y divide-border/50">
        {/* Latest digest */}
        <div className="px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Latest Digest
          </p>
          {data.loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading...
            </div>
          ) : data.error ? (
            <p className="text-sm text-muted-foreground">{data.error}</p>
          ) : latestDigest ? (
            <Link
              href={`/digest`}
              className="group flex items-center justify-between rounded-lg border border-border/40 bg-muted/20 px-3 py-2.5 hover:bg-primary/5 transition-colors"
            >
              <div>
                <p className="text-sm font-medium">{friendlyDate(latestDigest.digest_date)}</p>
                <p className="text-xs text-muted-foreground line-clamp-1 max-w-xs">{latestDigest.preview || "No items"}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-[10px]">
                  {latestDigest.item_count} item{latestDigest.item_count !== 1 ? "s" : ""}
                </Badge>
                <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
            </Link>
          ) : (
            <p className="text-sm text-muted-foreground">No digests yet for {child.name}.</p>
          )}
        </div>

        {/* Upcoming events */}
        <div className="px-5 py-4">
          <div className="flex items-center gap-2 mb-2">
            <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Upcoming (next 7 days)
            </p>
          </div>
          {data.loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading...
            </div>
          ) : data.upcoming_events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No upcoming events found.</p>
          ) : (
            <div className="space-y-1.5">
              {data.upcoming_events.slice(0, 5).map((ev, idx) => (
                <div key={idx} className="flex items-start gap-3 rounded-lg bg-primary/5 px-3 py-2">
                  <span className="text-base shrink-0">📅</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium line-clamp-1">{ev.subject}</p>
                    {ev.due_date && (
                      <p className="text-xs text-muted-foreground">{daysUntil(ev.due_date)} · {friendlyDate(ev.due_date)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action items */}
        <div className="px-5 py-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-3.5 w-3.5 text-muted-foreground" />
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Action Items
            </p>
          </div>
          {data.loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading...
            </div>
          ) : data.action_items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pending action items.</p>
          ) : (
            <div className="space-y-1.5">
              {data.action_items.slice(0, 5).map((action, idx) => (
                <div key={idx} className="flex items-start gap-3 rounded-lg bg-destructive/5 px-3 py-2">
                  <Badge variant="destructive" className="text-[10px] mt-0.5 shrink-0">Action</Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium line-clamp-1">{action.subject}</p>
                    {action.due_date && (
                      <p className="text-xs text-muted-foreground">Due: {friendlyDate(action.due_date)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

/* ── Page ────────────────────────────────────────── */

export default function ChildrenPage() {
  const [children, setChildren] = useState<ChildProfile[]>([])
  const [childrenLoading, setChildrenLoading] = useState(true)
  const [dashboards, setDashboards] = useState<Record<number, ChildDashboardData>>({})

  const fetchChildren = useCallback(async () => {
    setChildrenLoading(true)
    try {
      const res = await fetch("/api/children", { cache: "no-store" })
      if (!res.ok) return
      const data = await res.json()
      if (data.ok && Array.isArray(data.children)) {
        setChildren(data.children)
      }
    } finally {
      setChildrenLoading(false)
    }
  }, [])

  const fetchChildDashboard = useCallback(async (child: ChildProfile) => {
    setDashboards((prev) => ({
      ...prev,
      [child.id]: {
        child_name: child.name,
        child_id: child.id,
        total: 0,
        digests: [],
        upcoming_events: [],
        action_items: [],
        loading: true,
        error: null,
      },
    }))

    try {
      const res = await fetch(`/api/digest/children/${encodeURIComponent(child.name)}?limit=5`)
      if (!res.ok) {
        setDashboards((prev) => ({
          ...prev,
          [child.id]: { ...prev[child.id], loading: false, error: "Failed to load" },
        }))
        return
      }
      const data = await res.json()
      if (data.ok) {
        setDashboards((prev) => ({
          ...prev,
          [child.id]: {
            child_name: data.child_name,
            child_id: data.child_id,
            total: data.total,
            digests: data.digests || [],
            upcoming_events: data.upcoming_events || [],
            action_items: data.action_items || [],
            loading: false,
            error: null,
          },
        }))
      } else {
        setDashboards((prev) => ({
          ...prev,
          [child.id]: { ...prev[child.id], loading: false, error: data.error || "No data" },
        }))
      }
    } catch {
      setDashboards((prev) => ({
        ...prev,
        [child.id]: { ...prev[child.id], loading: false, error: "Network error" },
      }))
    }
  }, [])

  useEffect(() => {
    fetchChildren()
  }, [fetchChildren])

  useEffect(() => {
    if (children.length > 0) {
      children.forEach((child) => fetchChildDashboard(child))
    }
  }, [children, fetchChildDashboard])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Children</h1>
          <p className="text-muted-foreground">
            Latest digest, upcoming events, and action items for each child.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/settings?tab=children">Manage Children</Link>
        </Button>
      </div>

      {childrenLoading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin mr-3" /> Loading children...
        </div>
      ) : children.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center space-y-4">
            <Baby className="h-12 w-12 mx-auto text-muted-foreground/40" />
            <div>
              <p className="text-base font-semibold">No children added yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Add your children in Settings to see their personalized dashboards.
              </p>
            </div>
            <Button asChild>
              <Link href="/settings?tab=children">Add Child</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {children.map((child) => (
            <ChildCard
              key={child.id}
              child={child}
              data={
                dashboards[child.id] ?? {
                  child_name: child.name,
                  child_id: child.id,
                  total: 0,
                  digests: [],
                  upcoming_events: [],
                  action_items: [],
                  loading: true,
                  error: null,
                }
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
