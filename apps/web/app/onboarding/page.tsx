"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useSession, signIn } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Baby,
  Mail,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Plus,
  Trash2,
  CheckCircle2,
  School,
  Globe,
  Loader2,
  Search,
  Calendar,
  FileText,
  ExternalLink,
} from "lucide-react"

interface ChildForm {
  name: string
  school_text: string
  savedChildId: number | null
  discoveryJobId: number | null
  discoveryStatus: "idle" | "running" | "success" | "failed"
  discoveryResult: any | null
}

interface SourceInfo {
  id: number
  verified_name: string | null
  homepage_url: string | null
  calendar_page_url: string | null
  confidence_score: number | null
  status: string
  ics_urls: string[]
  rss_urls: string[]
  pdf_urls: string[]
}

export default function OnboardingPage() {
  const router = useRouter()
  const { data: session } = useSession()
  const firstName = session?.user?.name?.split(" ")[0] || "there"

  const [step, setStep] = useState(0)
  const [children, setChildren] = useState<ChildForm[]>([
    { name: "", school_text: "", savedChildId: null, discoveryJobId: null, discoveryStatus: "idle", discoveryResult: null },
  ])
  const [saving, setSaving] = useState(false)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [childSources, setChildSources] = useState<Record<number, SourceInfo[]>>({})

  const addChild = () => {
    setChildren([...children, { name: "", school_text: "", savedChildId: null, discoveryJobId: null, discoveryStatus: "idle", discoveryResult: null }])
  }

  const removeChild = (index: number) => {
    if (children.length <= 1) return
    setChildren(children.filter((_, i) => i !== index))
  }

  const updateChild = (index: number, field: keyof ChildForm, value: any) => {
    const updated = [...children]
    updated[index] = { ...updated[index], [field]: value }
    setChildren(updated)
  }

  const canProceedStep1 = children.some((c) => c.name.trim().length > 0)

  const saveChildrenAndDiscover = async () => {
    setSaving(true)
    const updated = [...children]

    for (let i = 0; i < updated.length; i++) {
      const child = updated[i]
      if (!child.name.trim()) continue

      try {
        // Create child
        const childRes = await fetch("/api/children", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: child.name.trim(),
            school_name: child.school_text.trim() || null,
          }),
        })
        const childData = await childRes.json()
        const childId = childData.child_id
        updated[i] = { ...updated[i], savedChildId: childId }

        // Kick off discovery if school text provided
        if (childId && child.school_text.trim()) {
          updated[i] = { ...updated[i], discoveryStatus: "running" }
          setChildren([...updated])

          try {
            const discoverRes = await fetch("/api/sources/discover", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                child_id: childId,
                school_query: child.school_text.trim(),
              }),
            })
            const discoverData = await discoverRes.json()
            updated[i] = {
              ...updated[i],
              discoveryJobId: discoverData.job_id,
              discoveryStatus: discoverData.ok ? "success" : "failed",
              discoveryResult: discoverData.result || null,
            }
          } catch {
            updated[i] = { ...updated[i], discoveryStatus: "failed" }
          }
        }
      } catch (err) {
        console.error("Failed to save child:", err)
      }
    }

    setChildren([...updated])
    setSaving(false)
    setStep(2)

    // Load discovered sources for each child
    for (const child of updated) {
      if (child.savedChildId) {
        try {
          const res = await fetch(`/api/sources/${child.savedChildId}`)
          const data = await res.json()
          if (data.ok && data.sources) {
            setChildSources((prev) => ({ ...prev, [child.savedChildId!]: data.sources }))
          }
        } catch {}
      }
    }
  }

  const handleConnectGmail = () => {
    signIn("google", { callbackUrl: window.location.href, prompt: "select_account" })
  }

  const handleFinish = async () => {
    setSaving(true)
    try {
      // Save default preferences
      await fetch("/api/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          digest_time: "06:00",
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Chicago",
        }),
      })

      // Mark onboarding complete
      await fetch("/api/auth/onboarding-complete", { method: "POST" })
      router.push("/dashboard")
    } catch (err) {
      console.error("Onboarding error:", err)
    } finally {
      setSaving(false)
    }
  }

  const steps = [
    { label: "Welcome", icon: Sparkles },
    { label: "Kids", icon: Baby },
    { label: "Sources", icon: Globe },
    { label: "Ready!", icon: CheckCircle2 },
  ]

  const totalSources = Object.values(childSources).flat().filter((s) => s.status === "verified").length
  const hasDiscoveries = children.some((c) => c.discoveryStatus === "success")

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-primary/5 flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/80 backdrop-blur">
        <div className="mx-auto max-w-3xl px-4 sm:px-6">
          <div className="flex h-16 items-center gap-2">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-2xl">🏠</span>
              <span className="text-xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
                  Parently
                </span>
              </span>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-start justify-center px-4 py-8 sm:py-12">
        <div className="w-full max-w-2xl space-y-8">
          {/* Progress */}
          <div className="flex items-center justify-center gap-2">
            {steps.map((s, i) => (
              <div key={s.label} className="flex items-center gap-2">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-all ${
                    i <= step
                      ? "bg-primary text-primary-foreground shadow-md shadow-primary/30"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {i < step ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <s.icon className="h-4 w-4" />
                  )}
                </div>
                {i < steps.length - 1 && (
                  <div
                    className={`h-0.5 w-8 sm:w-12 rounded transition-colors ${
                      i < step ? "bg-primary" : "bg-muted"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Step 0: Welcome */}
          {step === 0 && (
            <Card className="overflow-hidden shadow-xl shadow-primary/5">
              <CardHeader className="bg-gradient-to-br from-primary/10 to-accent/10 text-center pb-8 pt-10">
                <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10 text-5xl">
                  👋
                </div>
                <CardTitle className="text-3xl">
                  Welcome, {firstName}!
                </CardTitle>
                <CardDescription className="text-base mt-2 max-w-md mx-auto">
                  Let&apos;s set up Parently in under a minute. Just add your kids
                  and we&apos;ll find their school info automatically.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-8 space-y-6">
                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    { emoji: "👶", title: "Add your kids", desc: "Name + school" },
                    { emoji: "🔍", title: "We discover", desc: "Calendars & sources" },
                    { emoji: "✨", title: "Get digests!", desc: "Calm daily briefing" },
                  ].map((item) => (
                    <div
                      key={item.title}
                      className="flex flex-col items-center gap-2 rounded-xl border border-border/50 bg-muted/30 p-4 text-center"
                    >
                      <span className="text-3xl">{item.emoji}</span>
                      <p className="text-sm font-semibold">{item.title}</p>
                      <p className="text-xs text-muted-foreground">{item.desc}</p>
                    </div>
                  ))}
                </div>
                <Button className="w-full h-12 text-base font-semibold" onClick={() => setStep(1)}>
                  Let&apos;s get started
                  <ChevronRight className="ml-2 h-5 w-5" />
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Step 1: Add Children (simplified — name + school only) */}
          {step === 1 && (
            <Card className="overflow-hidden shadow-xl shadow-primary/5">
              <CardHeader className="bg-gradient-to-br from-pink-500/10 to-purple-500/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-pink-500/10 text-2xl">
                    👶
                  </div>
                  <div>
                    <CardTitle>Add your children</CardTitle>
                    <CardDescription>
                      Just a name and school — we&apos;ll handle the rest.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                {children.map((child, index) => (
                  <div
                    key={index}
                    className="space-y-4 rounded-xl border border-border/60 bg-muted/20 p-5"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="gap-1">
                        <Baby className="h-3 w-3" />
                        Child {index + 1}
                      </Badge>
                      {children.length > 1 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => removeChild(index)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Remove
                        </Button>
                      )}
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label>
                          Name <span className="text-destructive">*</span>
                        </Label>
                        <Input
                          placeholder="e.g. Emma"
                          value={child.name}
                          onChange={(e) => updateChild(index, "name", e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="flex items-center gap-1">
                          <School className="h-3.5 w-3.5" /> School
                        </Label>
                        <Input
                          placeholder="e.g. Harmony Georgetown, TX 78628"
                          value={child.school_text}
                          onChange={(e) => updateChild(index, "school_text", e.target.value)}
                        />
                        <p className="text-[10px] text-muted-foreground">
                          School name, city, state, or zip — we&apos;ll auto-discover the calendar
                        </p>
                      </div>
                    </div>
                  </div>
                ))}

                <Button variant="outline" className="w-full gap-2" onClick={addChild}>
                  <Plus className="h-4 w-4" />
                  Add another child
                </Button>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setStep(0)}>
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    className="flex-1"
                    disabled={!canProceedStep1 || saving}
                    onClick={saveChildrenAndDiscover}
                  >
                    {saving ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Discovering schools...
                      </>
                    ) : (
                      <>
                        Save & Discover
                        <Search className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 2: Connect Sources */}
          {step === 2 && (
            <Card className="overflow-hidden shadow-xl shadow-primary/5">
              <CardHeader className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10 text-2xl">
                    🔗
                  </div>
                  <div>
                    <CardTitle>Connect your sources</CardTitle>
                    <CardDescription>
                      Connect Gmail for school emails. We also found school sources automatically.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                {/* Gmail connect */}
                <div className="rounded-xl border border-border/60 bg-muted/20 p-5 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                      <Mail className="h-5 w-5 text-red-500" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">Gmail</p>
                      <p className="text-xs text-muted-foreground">
                        Parently reads school-related emails to include in your digest
                      </p>
                    </div>
                    {gmailConnected ? (
                      <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Connected
                      </Badge>
                    ) : (
                      <Button size="sm" variant="outline" onClick={handleConnectGmail}>
                        Connect
                      </Button>
                    )}
                  </div>
                </div>

                {/* Discovered sources per child */}
                {children.filter((c) => c.name.trim()).map((child, i) => (
                  <div key={i} className="rounded-xl border border-border/60 bg-muted/20 p-5 space-y-3">
                    <div className="flex items-center gap-2">
                      <Baby className="h-4 w-4 text-pink-500" />
                      <p className="font-medium">{child.name}</p>
                      {child.discoveryStatus === "running" && (
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      )}
                      {child.discoveryStatus === "success" && (
                        <Badge variant="outline" className="text-emerald-600 border-emerald-500/30 text-[10px]">
                          Discovered
                        </Badge>
                      )}
                    </div>

                    {/* Show discovered sources */}
                    {child.savedChildId && childSources[child.savedChildId]?.length > 0 ? (
                      <div className="space-y-2 ml-6">
                        {childSources[child.savedChildId].map((source) => (
                          <div key={source.id} className="flex items-start gap-2 text-sm">
                            <Globe className="h-3.5 w-3.5 mt-0.5 text-blue-500 shrink-0" />
                            <div className="min-w-0">
                              <p className="font-medium text-xs truncate">
                                {source.verified_name || "School website"}
                              </p>
                              <div className="flex flex-wrap gap-1.5 mt-1">
                                {source.homepage_url && (
                                  <Badge variant="outline" className="text-[10px] gap-0.5">
                                    <ExternalLink className="h-2.5 w-2.5" />
                                    Website
                                  </Badge>
                                )}
                                {source.calendar_page_url && (
                                  <Badge variant="outline" className="text-[10px] gap-0.5 border-emerald-500/30 text-emerald-600">
                                    <Calendar className="h-2.5 w-2.5" />
                                    Calendar
                                  </Badge>
                                )}
                                {source.ics_urls?.length > 0 && (
                                  <Badge variant="outline" className="text-[10px] gap-0.5 border-blue-500/30 text-blue-600">
                                    <Calendar className="h-2.5 w-2.5" />
                                    ICS feed
                                  </Badge>
                                )}
                                {source.pdf_urls?.length > 0 && (
                                  <Badge variant="outline" className="text-[10px] gap-0.5 border-orange-500/30 text-orange-600">
                                    <FileText className="h-2.5 w-2.5" />
                                    PDF calendar
                                  </Badge>
                                )}
                                <Badge
                                  variant="outline"
                                  className={`text-[10px] ${
                                    source.status === "verified"
                                      ? "border-emerald-500/30 text-emerald-600"
                                      : "border-yellow-500/30 text-yellow-600"
                                  }`}
                                >
                                  {source.status === "verified" ? "Auto-verified" : "Needs confirmation"}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : child.discoveryStatus === "success" && child.discoveryResult?.sources_created === 0 ? (
                      <p className="text-xs text-muted-foreground ml-6">
                        No school sources found automatically. You can add sources later from Settings.
                      </p>
                    ) : child.discoveryStatus === "failed" ? (
                      <p className="text-xs text-muted-foreground ml-6">
                        Discovery didn&apos;t find sources — you can try again from Settings.
                      </p>
                    ) : !child.school_text.trim() ? (
                      <p className="text-xs text-muted-foreground ml-6">
                        No school provided — add one later from Settings to discover sources.
                      </p>
                    ) : null}
                  </div>
                ))}

                <div className="rounded-xl border border-primary/10 bg-primary/5 p-4 text-sm text-muted-foreground">
                  <p>
                    <strong className="text-foreground">Smart sources:</strong> We automatically parse ClassDojo,
                    Brightwheel, and other school emails — no setup needed. Just connect Gmail above.
                  </p>
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setStep(1)}>
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    Back
                  </Button>
                  <Button className="flex-1" onClick={() => setStep(3)}>
                    Continue
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 3: All set */}
          {step === 3 && (
            <Card className="overflow-hidden shadow-xl shadow-primary/5">
              <CardHeader className="bg-gradient-to-br from-emerald-500/10 to-green-500/10 text-center pb-8 pt-10">
                <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-emerald-500/10 text-5xl">
                  🎉
                </div>
                <CardTitle className="text-3xl">You&apos;re all set!</CardTitle>
                <CardDescription className="text-base mt-2 max-w-md mx-auto">
                  Parently will generate a calm daily digest for{" "}
                  {children.filter((c) => c.name.trim()).map((c) => c.name.trim()).join(" & ")}.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-8 space-y-6">
                <div className="space-y-3">
                  {children
                    .filter((c) => c.name.trim())
                    .map((child, i) => {
                      const sources = child.savedChildId ? childSources[child.savedChildId] || [] : []
                      const verifiedSources = sources.filter((s) => s.status === "verified")
                      return (
                        <div
                          key={i}
                          className="flex items-center gap-3 rounded-lg border border-border/50 bg-muted/30 p-3"
                        >
                          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-pink-500/10 text-lg">
                            👧
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{child.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {child.school_text || "No school yet"}
                              {verifiedSources.length > 0 && (
                                <span className="text-emerald-600">
                                  {" "}· {verifiedSources.length} source{verifiedSources.length !== 1 ? "s" : ""} found
                                </span>
                              )}
                            </p>
                          </div>
                          {verifiedSources.length > 0 && (
                            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                          )}
                        </div>
                      )
                    })}
                </div>

                <div className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <Sparkles className="h-5 w-5 text-emerald-500" />
                  <div>
                    <p className="text-sm font-medium">30 free digests included</p>
                    <p className="text-xs text-muted-foreground">
                      Upgrade anytime for unlimited digests at $3/mo
                    </p>
                  </div>
                </div>

                {totalSources > 0 && (
                  <div className="flex items-center gap-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
                    <Globe className="h-5 w-5 text-blue-500" />
                    <div>
                      <p className="text-sm font-medium">
                        {totalSources} school source{totalSources !== 1 ? "s" : ""} auto-discovered
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Calendar events and announcements will appear in your digest
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setStep(2)}>
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    className="flex-1 h-12 text-base font-semibold"
                    disabled={saving}
                    onClick={handleFinish}
                  >
                    {saving ? "Setting up…" : "Go to Dashboard"}
                    {!saving && <ChevronRight className="ml-2 h-5 w-5" />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}
