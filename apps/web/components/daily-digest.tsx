"use client"

import { useCallback, useEffect, useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronRight, ChevronDown, RefreshCw, Clock, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { UpgradeModal } from "@/components/upgrade-modal"
import Link from "next/link"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useSession } from "next-auth/react"
import { fetchSetupStatusModel, SetupStatusModel } from "@/lib/setup-status"

/* ── Types ────────────────────────────────────── */

interface DigestItem {
  source: string
  subject: string
  body: string
  due_date: string | null
  tags: string[]
  child_id?: number | null
  child_name?: string
}

interface DigestFull {
  id: number
  digest_date: string | null
  created_at: string
  summary_md: string
  items: DigestItem[]
  source: string
}

interface DigestSummary {
  id: number
  digest_date: string | null
  created_at: string
  item_count: number
  preview: string
}

interface SetupModalState {
  open: boolean
  title: string
  description: string
  ctaLabel: string
  ctaHref: string
}

/* ── Helpers ──────────────────────────────────── */

function mapItem(item: DigestItem, idx: number) {
  const tags = item.tags || []
  const type = tags.includes("event") ? "event" : item.source === "pdf" ? "document" : "reminder"
  const priority = tags.includes("action") ? "high" : tags.includes("finance") ? "medium" : "low"
  return { ...item, _type: type, _priority: priority, _idx: idx }
}

function emojiForType(type: string) {
  switch (type) {
    case "event": return "📅"
    case "document": return "📄"
    default: return "💬"
  }
}

function emojiForPriority(p: string) {
  switch (p) {
    case "high": return "🔴"
    case "medium": return "🟡"
    default: return "🔵"
  }
}

function priorityColor(p: string) {
  switch (p) {
    case "high": return "bg-destructive/10 text-destructive border-destructive/20"
    case "medium": return "bg-accent/10 text-accent border-accent/20"
    default: return "bg-muted text-muted-foreground border-border"
  }
}

function friendlyDate(dateStr: string | null) {
  if (!dateStr) return "Unknown"
  const d = new Date(dateStr + "T00:00:00")
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((today.getTime() - d.getTime()) / 86400000)
  if (diff === 0) return "Today"
  if (diff === 1) return "Yesterday"
  return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
}

/* ── Component ────────────────────────────────── */

export function DailyDigest() {
  const { data: session } = useSession()
  const [loading, setLoading] = useState(false)
  const [showUpgrade, setShowUpgrade] = useState(false)
  const [todayDigest, setTodayDigest] = useState<DigestFull | null>(null)
  const [pastDigests, setPastDigests] = useState<DigestSummary[]>([])
  const [showPast, setShowPast] = useState(false)
  const [expandedPastId, setExpandedPastId] = useState<number | null>(null)
  const [expandedPastDigest, setExpandedPastDigest] = useState<DigestFull | null>(null)
  const [loadingPast, setLoadingPast] = useState(false)
  const [initialLoad, setInitialLoad] = useState(true)
  const [setupStatus, setSetupStatus] = useState<SetupStatusModel | null>(null)
  const [setupLoading, setSetupLoading] = useState(true)
  const [setupModal, setSetupModal] = useState<SetupModalState>({
    open: false,
    title: "",
    description: "",
    ctaLabel: "",
    ctaHref: "/settings",
  })

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch("/api/digest/dashboard")
      if (!res.ok) return
      const data = await res.json()
      if (data.ok) {
        setTodayDigest(data.today_digest || null)
        setPastDigests(data.past_digests || [])
      }
    } catch {
      // silent
    } finally {
      setInitialLoad(false)
    }
  }, [])

  useEffect(() => {
    fetchDashboard()
  }, [fetchDashboard])

  const fetchSetupStatus = useCallback(async () => {
    setSetupLoading(true)
    try {
      const model = await fetchSetupStatusModel({
        provider: (session as any)?.provider,
        grantedScopes: (session as any)?.grantedScopes,
      })
      setSetupStatus(model)
    } finally {
      setSetupLoading(false)
    }
  }, [session])

  useEffect(() => {
    fetchSetupStatus()
  }, [fetchSetupStatus])

  const setupIncomplete = !setupStatus?.hasChildren
  const showOnboardingEmptyState = !todayDigest && !setupLoading && setupIncomplete

  const openSetupPrompt = (kind: "child" | "integrations") => {
    if (kind === "child") {
      setSetupModal({
        open: true,
        title: "Add your child first to generate a digest",
        description: "Parently needs at least one child profile before creating your first digest.",
        ctaLabel: "Add Child",
        ctaHref: "/settings?tab=children",
      })
      return
    }
    setSetupModal({
      open: true,
      title: "You’re signed in with Google. Grant Gmail access to include school emails in digests.",
      description: "You can continue with school sources now, or grant Gmail/Drive access for richer digests.",
      ctaLabel: "Open Integrations",
      ctaHref: "/settings?tab=integrations",
    })
  }

  const parseSetupErrorKind = (body: any): "child" | "integrations" | null => {
    const detail = body?.detail
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail?.message === "string"
          ? detail.message
          : typeof body?.error === "string"
            ? body.error
            : ""
    const normalized = message.toLowerCase()

    if (normalized.includes("no children") || normalized.includes("child")) return "child"
    if (normalized.includes("no integration") || normalized.includes("integration")) {
      return "integrations"
    }
    return null
  }

  const handleRunDigest = async () => {
    if (!setupStatus?.hasChildren) {
      openSetupPrompt("child")
      return
    }

    setLoading(true)
    try {
      const res = await fetch("/api/digest/run", { method: "POST" })
      if (res.ok) {
        const data = await res.json()
        toast.success(data.cached ? "Digest already up to date" : "Digest generated!")
        fetchDashboard()
        fetchSetupStatus()
      } else if (res.status === 402) {
        setShowUpgrade(true)
      } else {
        const data = await res.json().catch(() => ({}))
        const setupKind = parseSetupErrorKind(data)
        if (setupKind) {
          openSetupPrompt(setupKind)
          return
        }
        toast.error("Failed to generate digest")
      }
    } catch {
      toast.error("Network error — is the backend running?")
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshDigest = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/digest/run?refresh=true", { method: "POST" })
      if (res.ok) {
        toast.success("Digest regenerated!")
        fetchDashboard()
        fetchSetupStatus()
      } else if (res.status === 402) {
        setShowUpgrade(true)
      } else {
        const data = await res.json().catch(() => ({}))
        const setupKind = parseSetupErrorKind(data)
        if (setupKind) {
          openSetupPrompt(setupKind)
          return
        }
        toast.error("Failed to regenerate digest")
      }
    } catch {
      toast.error("Network error")
    } finally {
      setLoading(false)
    }
  }

  const loadPastDigest = async (digestId: number) => {
    if (expandedPastId === digestId) {
      setExpandedPastId(null)
      setExpandedPastDigest(null)
      return
    }
    setExpandedPastId(digestId)
    setLoadingPast(true)
    try {
      const res = await fetch(`/api/digest/${digestId}`)
      if (res.ok) {
        const data = await res.json()
        if (data.ok) setExpandedPastDigest(data.digest)
      }
    } catch {
      // silent
    } finally {
      setLoadingPast(false)
    }
  }

  const items = todayDigest?.items?.map(mapItem) || []

  return (
    <div className="space-y-4">
      {/* ── Today's Digest ──────────────────── */}
      <Card className="overflow-hidden border-primary/10 shadow-lg shadow-primary/5">
        <CardHeader className="bg-gradient-to-br from-primary/8 via-accent/5 to-card pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📋</span>
              <div>
                <CardTitle className="text-xl">Today&apos;s Digest</CardTitle>
                <CardDescription>
                  Your calm overview of school communications
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="hidden sm:flex text-xs font-medium">
                {new Date().toLocaleDateString("en-US", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                })}
              </Badge>
              {todayDigest ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={handleRefreshDigest}
                  disabled={loading}
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                  {loading ? "Updating..." : "Refresh"}
                </Button>
              ) : (
                <Button
                  className="gap-1.5 shadow-md shadow-primary/20"
                  size="sm"
                  onClick={handleRunDigest}
                  disabled={loading}
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                  {loading
                    ? "Running..."
                    : !setupStatus?.hasChildren
                      ? "Add Child"
                      : "Run Digest"}
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {initialLoad ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading...
            </div>
          ) : showOnboardingEmptyState ? (
            <div className="py-12 text-center space-y-3 px-4">
              <span className="text-4xl block">🌱</span>
              <p className="text-base font-semibold">
                You&apos;re one step away from your first digest
              </p>
              <p className="text-sm text-muted-foreground">
                Add your child first and Parently will start creating daily digests.
              </p>
              <div className="flex flex-wrap justify-center gap-2 pt-1">
                <Button asChild size="sm">
                  <Link href="/settings?tab=children">Add Child</Link>
                </Button>
              </div>
            </div>
          ) : !todayDigest ? (
            <div className="py-12 text-center space-y-3">
              <span className="text-4xl block">📭</span>
              <p className="text-sm text-muted-foreground">
                No digest yet today. Click <strong>Run Digest</strong> to generate one.
              </p>
            </div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <span className="text-4xl block">✅</span>
              <p className="text-sm text-muted-foreground">
                All clear! No new school items found today.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border/60">
              {items.map((item) => (
                <div
                  key={item._idx}
                  className="group flex items-start gap-4 px-5 py-4 transition-all duration-200 hover:bg-primary/3"
                >
                  <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted text-lg">
                    {emojiForType(item._type)}
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold leading-snug text-foreground">
                        {item.subject || "Update"}
                      </h3>
                      <Badge
                        variant="outline"
                        className={`shrink-0 text-xs ${priorityColor(item._priority)}`}
                      >
                        {emojiForPriority(item._priority)} {item._priority}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {(item.body || "").slice(0, 140)}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      {item.due_date && (
                        <>
                          <span className="flex items-center gap-1">🕐 {item.due_date}</span>
                          <span>&bull;</span>
                        </>
                      )}
                      <span className="font-semibold text-primary/70">{item.source}</span>
                      {item.child_name && (
                        <>
                          <span>&bull;</span>
                          <span>👧 {item.child_name}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Past 7 Days ─────────────────────── */}
      <Card className="border-border/50">
        <button
          className="flex w-full items-center justify-between px-5 py-4 text-left hover:bg-muted/30 transition-colors rounded-xl"
          onClick={() => setShowPast(!showPast)}
        >
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-semibold">Past 7 Days</span>
            {pastDigests.length > 0 && (
              <Badge variant="secondary" className="text-[10px] h-5 px-1.5">
                {pastDigests.length}
              </Badge>
            )}
          </div>
          <ChevronDown
            className={`h-4 w-4 text-muted-foreground transition-transform ${showPast ? "rotate-180" : ""}`}
          />
        </button>

        {showPast && (
          <CardContent className="pt-0 pb-3 px-3">
            {pastDigests.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No past digests yet. They&apos;ll appear here as you use Parently.
              </p>
            ) : (
              <div className="space-y-1">
                {pastDigests.map((d) => (
                  <div key={d.id}>
                    <button
                      className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-muted/50 ${
                        expandedPastId === d.id ? "bg-muted/40" : ""
                      }`}
                      onClick={() => loadPastDigest(d.id)}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">📋</span>
                        <div>
                          <p className="text-sm font-medium">{friendlyDate(d.digest_date)}</p>
                          <p className="text-xs text-muted-foreground">
                            {d.item_count} item{d.item_count !== 1 ? "s" : ""}
                          </p>
                        </div>
                      </div>
                      <ChevronRight
                        className={`h-4 w-4 text-muted-foreground transition-transform ${
                          expandedPastId === d.id ? "rotate-90" : ""
                        }`}
                      />
                    </button>

                    {expandedPastId === d.id && (
                      <div className="ml-8 mr-2 mt-1 mb-2 rounded-lg border border-border/40 bg-muted/20 p-3">
                        {loadingPast ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                            <Loader2 className="h-4 w-4 animate-spin" /> Loading...
                          </div>
                        ) : expandedPastDigest ? (
                          <div className="space-y-2">
                            {expandedPastDigest.items.map((item, idx) => {
                              const m = mapItem(item, idx)
                              return (
                                <div key={idx} className="flex items-start gap-2 text-sm">
                                  <span>{emojiForType(m._type)}</span>
                                  <div className="min-w-0">
                                    <p className="font-medium">{item.subject || "Update"}</p>
                                    <p className="text-xs text-muted-foreground line-clamp-1">
                                      {(item.body || "").slice(0, 100)}
                                    </p>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">No data</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        )}
      </Card>

      <UpgradeModal open={showUpgrade} onOpenChange={setShowUpgrade} />
      <Dialog
        open={setupModal.open}
        onOpenChange={(open) => setSetupModal((prev) => ({ ...prev, open }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{setupModal.title}</DialogTitle>
            <DialogDescription>{setupModal.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button asChild>
              <Link href={setupModal.ctaHref}>{setupModal.ctaLabel}</Link>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
