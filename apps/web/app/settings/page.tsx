"use client"

import { useCallback, useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Mail,
  FolderOpen,
  GraduationCap,
  Puzzle,
  Sun,
  Sparkles,
  CheckCircle2,
  ExternalLink,
  Baby,
  Plus,
  Trash2,
  School,
  CreditCard,
  Zap,
  Save,
  Loader2,
} from "lucide-react"

/* ─── Types ─────────────────────────────────────────── */

interface ChildData {
  id?: number
  name: string
  grade: string
  school_name: string
  teacher_name: string
}

interface SearchProfile {
  subject_keywords: string[]
  sender_allowlist: string[]
  sender_blocklist: string[]
  label_whitelist: string[]
  exclude_keywords: string[]
  gmail_query_base: string | null
  last_sync_at: string | null
}

interface Prefs {
  digest_time: string
  timezone: string
  email_notifications: boolean
  push_notifications: boolean
  urgent_alerts: boolean
  lookback_days: number
}

interface BillingData {
  plan: string
  digests_remaining: number
  premium_active: boolean
  premium_started_at: string | null
  premium_ends_at: string | null
  stripe_subscription_id: string | null
}

const GRADES = [
  "Pre-K", "Kindergarten",
  "1st Grade", "2nd Grade", "3rd Grade", "4th Grade", "5th Grade",
  "6th Grade", "7th Grade", "8th Grade",
  "9th Grade", "10th Grade", "11th Grade", "12th Grade",
]

const TIMEZONES = [
  "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu",
]

export default function SettingsPage() {
  const { data: session } = useSession()

  /* ─── Children state ───────────────────────────────── */
  const [children, setChildren] = useState<ChildData[]>([])
  const [childrenLoading, setChildrenLoading] = useState(true)
  const [childSaving, setChildSaving] = useState(false)
  const [profiles, setProfiles] = useState<Record<number, SearchProfile>>({})
  const [expandedChild, setExpandedChild] = useState<number | null>(null)
  const [profileSaving, setProfileSaving] = useState(false)

  const loadChildren = useCallback(async () => {
    try {
      const res = await fetch("/api/children")
      const data = await res.json()
      if (data.ok) setChildren(data.children)
    } finally {
      setChildrenLoading(false)
    }
  }, [])

  useEffect(() => { loadChildren() }, [loadChildren])

  const loadProfile = async (childId: number) => {
    try {
      const res = await fetch(`/api/search-profiles/${childId}`)
      const data = await res.json()
      if (data.ok && data.profile) {
        setProfiles((prev) => ({ ...prev, [childId]: data.profile }))
      } else {
        setProfiles((prev) => ({
          ...prev,
          [childId]: {
            subject_keywords: [], sender_allowlist: [], sender_blocklist: [],
            label_whitelist: [], exclude_keywords: [], gmail_query_base: null, last_sync_at: null,
          },
        }))
      }
    } catch { /* ignore */ }
  }

  const toggleExpand = (childId: number | undefined) => {
    if (!childId) return
    if (expandedChild === childId) {
      setExpandedChild(null)
    } else {
      setExpandedChild(childId)
      if (!profiles[childId]) loadProfile(childId)
    }
  }

  const updateProfileField = (childId: number, field: keyof SearchProfile, value: string) => {
    const items = value.split(",").map((s) => s.trim()).filter(Boolean)
    setProfiles((prev) => ({
      ...prev,
      [childId]: { ...prev[childId], [field]: items },
    }))
  }

  const saveProfile = async (childId: number) => {
    const p = profiles[childId]
    if (!p) return
    setProfileSaving(true)
    try {
      await fetch(`/api/search-profiles/${childId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_keywords: p.subject_keywords,
          sender_allowlist: p.sender_allowlist,
          sender_blocklist: p.sender_blocklist,
          label_whitelist: p.label_whitelist,
          exclude_keywords: p.exclude_keywords,
          gmail_query_base: p.gmail_query_base,
        }),
      })
    } finally {
      setProfileSaving(false)
    }
  }

  const addChildRow = () => {
    setChildren([...children, { name: "", grade: "", school_name: "", teacher_name: "" }])
  }

  const updateChildField = (index: number, field: keyof ChildData, value: string) => {
    const updated = [...children]
    updated[index] = { ...updated[index], [field]: value }
    setChildren(updated)
  }

  const saveChild = async (index: number) => {
    const child = children[index]
    if (!child.name.trim()) return
    setChildSaving(true)
    try {
      if (child.id) {
        await fetch(`/api/children/${child.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(child),
        })
      } else {
        const res = await fetch("/api/children", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(child),
        })
        const data = await res.json()
        if (data.ok) {
          const updated = [...children]
          updated[index] = { ...updated[index], id: data.child_id }
          setChildren(updated)
        }
      }
    } finally {
      setChildSaving(false)
    }
  }

  const deleteChild = async (index: number) => {
    const child = children[index]
    if (child.id) {
      await fetch(`/api/children/${child.id}`, { method: "DELETE" })
    }
    setChildren(children.filter((_, i) => i !== index))
  }

  /* ─── Preferences state ────────────────────────────── */
  const [prefs, setPrefs] = useState<Prefs>({
    digest_time: "06:00",
    timezone: "America/Chicago",
    email_notifications: true,
    push_notifications: false,
    urgent_alerts: true,
    lookback_days: 7,
  })
  const [prefsSaving, setPrefsSaving] = useState(false)

  useEffect(() => {
    fetch("/api/preferences")
      .then((r) => r.json())
      .then((data) => {
        if (data.ok && data.preferences) setPrefs(data.preferences)
      })
      .catch(() => {})
  }, [])

  const savePrefs = async () => {
    setPrefsSaving(true)
    try {
      await fetch("/api/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      })
    } finally {
      setPrefsSaving(false)
    }
  }

  /* ─── Billing state ────────────────────────────────── */
  const [billing, setBilling] = useState<BillingData | null>(null)
  const [billingError, setBillingError] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/billing/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) setBilling(data)
      })
      .catch(() => {})
  }, [])

  const handleUpgrade = async () => {
    setBillingError(null)
    const res = await fetch("/api/billing/create-checkout-session", {
      method: "POST",
      credentials: "include",
    })
    const data = await res.json().catch(() => ({}))
    if (data.checkout_url) {
      window.location.href = data.checkout_url
      return
    }
    setBillingError(data?.detail || data?.error || "Unable to start checkout.")
  }

  /* ─── Integration config ───────────────────────────── */
  const integrations = [
    {
      id: "gmail", name: "Gmail", description: "Scan school-related emails automatically",
      icon: Mail, color: "bg-red-500/10 text-red-600", connected: true,
      configFields: [{ label: "Email filter query", placeholder: "label:School newer_than:7d", key: "gmail_query" }],
    },
    {
      id: "gdrive", name: "Google Drive", description: "Sync documents from a shared folder",
      icon: FolderOpen, color: "bg-yellow-500/10 text-yellow-600", connected: false,
      configFields: [{ label: "Folder URL or ID", placeholder: "https://drive.google.com/drive/folders/...", key: "gdrive_folder" }],
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account, children, integrations, and billing.
        </p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="flex-wrap">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="children">Children</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="digest">Digest</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        {/* ── Profile Tab ─────────────────────────────── */}
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>Your account information from your login provider.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <Avatar className="h-16 w-16">
                  <AvatarImage src={session?.user?.image || ""} />
                  <AvatarFallback className="text-lg">
                    {session?.user?.name?.charAt(0) || "U"}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-lg font-medium">{session?.user?.name || "User"}</p>
                  <p className="text-sm text-muted-foreground">{session?.user?.email}</p>
                </div>
              </div>
              <Separator />
              <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                <p className="text-sm font-medium">Support Contact</p>
                <p className="text-xs text-muted-foreground">
                  support@parently-ai.com
                </p>
                <a href="/support" className="text-xs underline text-primary">
                  Contact support
                </a>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Children Tab ────────────────────────────── */}
        <TabsContent value="children">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Baby className="h-5 w-5" /> Children
                  </CardTitle>
                  <CardDescription>
                    Manage your children&apos;s profiles for personalized digests.
                  </CardDescription>
                </div>
                <Button size="sm" className="gap-1" onClick={addChildRow}>
                  <Plus className="h-4 w-4" /> Add Child
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {childrenLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading…
                </div>
              ) : children.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Baby className="h-10 w-10 mx-auto mb-3 opacity-40" />
                  <p className="font-medium">No children added yet</p>
                  <p className="text-sm">Click &ldquo;Add Child&rdquo; to get started.</p>
                </div>
              ) : (
                children.map((child, index) => (
                  <div
                    key={child.id || `new-${index}`}
                    className="space-y-4 rounded-xl border border-border/60 bg-muted/20 p-5"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="gap-1">
                        <Baby className="h-3 w-3" />
                        {child.id ? child.name || `Child ${index + 1}` : "New child"}
                      </Badge>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1"
                          disabled={childSaving || !child.name.trim()}
                          onClick={() => saveChild(index)}
                        >
                          <Save className="h-3.5 w-3.5" />
                          Save
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive gap-1"
                          onClick={() => deleteChild(index)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label>Name <span className="text-destructive">*</span></Label>
                        <Input
                          placeholder="e.g. Emma"
                          value={child.name}
                          onChange={(e) => updateChildField(index, "name", e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label>Grade</Label>
                        <Select
                          value={child.grade}
                          onValueChange={(v) => updateChildField(index, "grade", v)}
                        >
                          <SelectTrigger><SelectValue placeholder="Select grade" /></SelectTrigger>
                          <SelectContent>
                            {GRADES.map((g) => (<SelectItem key={g} value={g}>{g}</SelectItem>))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <Label className="flex items-center gap-1">
                          <School className="h-3.5 w-3.5" /> School
                        </Label>
                        <Input
                          placeholder="e.g. Lincoln Elementary"
                          value={child.school_name}
                          onChange={(e) => updateChildField(index, "school_name", e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="flex items-center gap-1">
                          <GraduationCap className="h-3.5 w-3.5" /> Teacher
                        </Label>
                        <Input
                          placeholder="e.g. Ms. Garcia"
                          value={child.teacher_name}
                          onChange={(e) => updateChildField(index, "teacher_name", e.target.value)}
                        />
                      </div>
                    </div>

                    {/* Search Profile Section */}
                    {child.id && (
                      <div className="border-t border-border/40 pt-3 mt-1">
                        <button
                          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => toggleExpand(child.id)}
                        >
                          <Mail className="h-3.5 w-3.5" />
                          {expandedChild === child.id ? "▾" : "▸"} Email Filters
                          {profiles[child.id!]?.last_sync_at && (
                            <span className="ml-2 text-[10px] text-muted-foreground">
                              Last sync: {new Date(profiles[child.id!].last_sync_at!).toLocaleDateString()}
                            </span>
                          )}
                        </button>

                        {expandedChild === child.id && profiles[child.id] && (
                          <div className="mt-3 space-y-3">
                            <div className="grid gap-3 sm:grid-cols-2">
                              <div className="space-y-1">
                                <Label className="text-xs">Known senders</Label>
                                <Input
                                  placeholder="@classdojo.com, @brightwheel.com"
                                  value={profiles[child.id].sender_allowlist.join(", ")}
                                  onChange={(e) => updateProfileField(child.id!, "sender_allowlist", e.target.value)}
                                  className="h-8 text-xs"
                                />
                              </div>
                              <div className="space-y-1">
                                <Label className="text-xs">Subject keywords</Label>
                                <Input
                                  placeholder="field trip, permission slip"
                                  value={profiles[child.id].subject_keywords.join(", ")}
                                  onChange={(e) => updateProfileField(child.id!, "subject_keywords", e.target.value)}
                                  className="h-8 text-xs"
                                />
                              </div>
                              <div className="space-y-1">
                                <Label className="text-xs">Blocked senders</Label>
                                <Input
                                  placeholder="noreply@promo.com"
                                  value={profiles[child.id].sender_blocklist.join(", ")}
                                  onChange={(e) => updateProfileField(child.id!, "sender_blocklist", e.target.value)}
                                  className="h-8 text-xs"
                                />
                              </div>
                              <div className="space-y-1">
                                <Label className="text-xs">Label whitelist</Label>
                                <Input
                                  placeholder="INBOX, School"
                                  value={profiles[child.id].label_whitelist.join(", ")}
                                  onChange={(e) => updateProfileField(child.id!, "label_whitelist", e.target.value)}
                                  className="h-8 text-xs"
                                />
                              </div>
                              <div className="space-y-1">
                                <Label className="text-xs">Exclude keywords</Label>
                                <Input
                                  placeholder="sale, promo, unsubscribe"
                                  value={profiles[child.id].exclude_keywords.join(", ")}
                                  onChange={(e) => updateProfileField(child.id!, "exclude_keywords", e.target.value)}
                                  className="h-8 text-xs"
                                />
                              </div>
                              <div className="space-y-1">
                                <Label className="text-xs">Gmail query override</Label>
                                <Input
                                  placeholder="newer_than:14d (child OR school)"
                                  value={profiles[child.id].gmail_query_base || ""}
                                  onChange={(e) => setProfiles((prev) => ({
                                    ...prev,
                                    [child.id!]: { ...prev[child.id!], gmail_query_base: e.target.value || null },
                                  }))}
                                  className="h-8 text-xs"
                                />
                              </div>
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1 h-7 text-xs"
                              disabled={profileSaving}
                              onClick={() => saveProfile(child.id!)}
                            >
                              {profileSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                              Save Filters
                            </Button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Integrations Tab ────────────────────────── */}
        <TabsContent value="integrations">
          <div className="space-y-4">
            {integrations.map((integration) => (
              <Card key={integration.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`rounded-lg p-2.5 ${integration.color}`}>
                        <integration.icon className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{integration.name}</CardTitle>
                        <CardDescription className="text-xs">
                          {integration.description}
                        </CardDescription>
                      </div>
                    </div>
                    {integration.connected ? (
                      <Badge variant="outline" className="gap-1 border-green-500/20 bg-green-500/10 text-green-600">
                        <CheckCircle2 className="h-3 w-3" /> Connected
                      </Badge>
                    ) : (
                      <Button size="sm">
                        <ExternalLink className="mr-1 h-3.5 w-3.5" /> Connect
                      </Button>
                    )}
                  </div>
                </CardHeader>
                {integration.configFields.length > 0 && (
                  <CardContent className="space-y-3">
                    <Separator />
                    {integration.configFields.map((field) => (
                      <div key={field.key} className="space-y-1.5">
                        <Label htmlFor={field.key}>{field.label}</Label>
                        <Input
                          id={field.key}
                          type={(field as any).type || "text"}
                          placeholder={field.placeholder}
                        />
                      </div>
                    ))}
                    <Button size="sm" variant="outline">Save Configuration</Button>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* ── Digest Preferences Tab ──────────────────── */}
        <TabsContent value="digest">
          <Card>
            <CardHeader>
              <CardTitle>Digest Preferences</CardTitle>
              <CardDescription>
                Configure when and how your daily digest is generated.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="digest-time">Digest time</Label>
                  <Input
                    id="digest-time"
                    type="time"
                    value={prefs.digest_time}
                    onChange={(e) => setPrefs({ ...prefs, digest_time: e.target.value })}
                    className="w-full"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Timezone</Label>
                  <Select
                    value={prefs.timezone}
                    onValueChange={(v) => setPrefs({ ...prefs, timezone: v })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TIMEZONES.map((tz) => (
                        <SelectItem key={tz} value={tz}>
                          {tz.replace("America/", "").replace("Pacific/", "").replace("_", " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="lookback">Email lookback period (days)</Label>
                <Input
                  id="lookback"
                  type="number"
                  value={prefs.lookback_days}
                  onChange={(e) => setPrefs({ ...prefs, lookback_days: parseInt(e.target.value) || 7 })}
                  className="w-40"
                />
              </div>
              <Button onClick={savePrefs} disabled={prefsSaving} className="gap-2">
                {prefsSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Preferences
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Notifications Tab ───────────────────────── */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>
                Choose how you want to be notified about new digests.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Email notifications</p>
                  <p className="text-xs text-muted-foreground">
                    Receive your daily digest via email
                  </p>
                </div>
                <Switch
                  checked={prefs.email_notifications}
                  onCheckedChange={(v) => setPrefs({ ...prefs, email_notifications: v })}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Push notifications</p>
                  <p className="text-xs text-muted-foreground">
                    Get push notifications on your device
                  </p>
                </div>
                <Switch
                  checked={prefs.push_notifications}
                  onCheckedChange={(v) => setPrefs({ ...prefs, push_notifications: v })}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Urgent alerts</p>
                  <p className="text-xs text-muted-foreground">
                    Get notified immediately for action-required items
                  </p>
                </div>
                <Switch
                  checked={prefs.urgent_alerts}
                  onCheckedChange={(v) => setPrefs({ ...prefs, urgent_alerts: v })}
                />
              </div>
              <Separator />
              <Button onClick={savePrefs} disabled={prefsSaving} className="gap-2">
                {prefsSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Notifications
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Billing Tab ─────────────────────────────── */}
        <TabsContent value="billing">
          <div className="space-y-4">
            {/* Current Plan */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" /> Current Plan
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {billing ? (
                  <>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={billing.premium_active ? "default" : "secondary"}
                        className={`text-sm px-3 py-1 ${
                          billing.premium_active
                            ? "bg-gradient-to-r from-yellow-500 to-orange-500 text-white"
                            : ""
                        }`}
                      >
                        {billing.premium_active ? (
                          <><Zap className="h-3.5 w-3.5 mr-1" /> Premium</>
                        ) : (
                          "Free"
                        )}
                      </Badge>
                      {billing.premium_active && billing.premium_started_at && (
                        <span className="text-sm text-muted-foreground">
                          Active since {new Date(billing.premium_started_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>

                    {!billing.premium_active && (
                      <div className="rounded-lg border border-border/50 bg-muted/30 p-4 space-y-2">
                        <p className="text-sm font-medium">
                          {billing.digests_remaining} of 30 free digests remaining
                        </p>
                        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${Math.min(100, (billing.digests_remaining / 30) * 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Upgrade to Premium for unlimited digests
                        </p>
                      </div>
                    )}

                    {!billing.premium_active && (
                      <Button className="gap-2" onClick={handleUpgrade}>
                        <Zap className="h-4 w-4" />
                        Upgrade to Premium — $3/month
                      </Button>
                    )}
                    {!billing.premium_active && billingError ? (
                      <p className="text-xs text-destructive">{billingError}</p>
                    ) : null}

                    {billing.premium_active && billing.stripe_subscription_id && (
                      <div className="space-y-3">
                        <Separator />
                        <p className="text-sm text-muted-foreground">
                          Manage your subscription, update payment methods, or view invoices through Stripe.
                        </p>
                        <Button variant="outline" className="gap-2">
                          <ExternalLink className="h-4 w-4" />
                          Manage Subscription
                        </Button>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center justify-center py-6 text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading billing info…
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
