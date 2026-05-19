"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Loader2, Save, Clock, Calendar, Bell, Mail } from "lucide-react"
import { toast } from "sonner"

/* ─── Types ─────────────────────────────────────────── */

type Frequency = "daily" | "weekdays" | "custom"

const CUSTOM_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const

const HOURS = Array.from({ length: 24 }, (_, i) => i)
const MINUTES = [0, 15, 30, 45]

const TIMEZONES: { value: string; label: string }[] = [
  { value: "America/New_York", label: "Eastern Time (ET)" },
  { value: "America/Chicago", label: "Central Time (CT)" },
  { value: "America/Denver", label: "Mountain Time (MT)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
  { value: "America/Anchorage", label: "Alaska Time (AKT)" },
  { value: "Pacific/Honolulu", label: "Hawaii Time (HT)" },
  { value: "America/Phoenix", label: "Arizona (MST, no DST)" },
  { value: "Europe/London", label: "London (GMT/BST)" },
  { value: "Europe/Paris", label: "Central European Time (CET)" },
  { value: "Asia/Tokyo", label: "Japan Standard Time (JST)" },
  { value: "Asia/Shanghai", label: "China Standard Time (CST)" },
  { value: "Australia/Sydney", label: "Australian Eastern Time (AEST)" },
]

const TZ_SHORT: Record<string, string> = {
  "America/New_York": "Eastern Time",
  "America/Chicago": "Central Time",
  "America/Denver": "Mountain Time",
  "America/Los_Angeles": "Pacific Time",
  "America/Anchorage": "Alaska Time",
  "Pacific/Honolulu": "Hawaii Time",
  "America/Phoenix": "Arizona",
  "Europe/London": "London",
  "Europe/Paris": "Central European Time",
  "Asia/Tokyo": "Japan Time",
  "Asia/Shanghai": "China Time",
  "Australia/Sydney": "Australian Eastern Time",
}

function pad(n: number) {
  return String(n).padStart(2, "0")
}

function formatHour(h: number) {
  const suffix = h < 12 ? "AM" : "PM"
  const display = h === 0 ? 12 : h > 12 ? h - 12 : h
  return `${display}:00 ${suffix}`
}

function getNextDigestLabel(
  hour: number,
  minute: number,
  frequency: Frequency,
  customDays: string[],
  timezone: string
): string {
  const tzLabel = TZ_SHORT[timezone] || timezone
  const timeStr = `${pad(hour)}:${pad(minute)}`

  if (frequency === "daily") {
    return `Your next digest will be sent tomorrow at ${timeStr} (${tzLabel})`
  }
  if (frequency === "weekdays") {
    return `Your next digest will be sent on the next weekday at ${timeStr} (${tzLabel})`
  }
  if (customDays.length === 0) {
    return `Select at least one day to schedule your digest.`
  }
  return `Your digest will be sent on ${customDays.join(", ")} at ${timeStr} (${tzLabel})`
}

/* ─── Component ──────────────────────────────────────── */

export default function SchedulePage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [hour, setHour] = useState(7)
  const [minute, setMinute] = useState(0)
  const [timezone, setTimezone] = useState("America/New_York")
  const [frequency, setFrequency] = useState<Frequency>("daily")
  const [customDays, setCustomDays] = useState<string[]>(["Mon", "Tue", "Wed", "Thu", "Fri"])
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [inAppNotifications, setInAppNotifications] = useState(true)

  // Load existing preferences
  useEffect(() => {
    fetch("/api/preferences")
      .then((r) => r.json())
      .then((data) => {
        if (data.ok && data.preferences) {
          const prefs = data.preferences
          if (prefs.digest_time) {
            const [h, m] = prefs.digest_time.split(":").map(Number)
            setHour(isNaN(h) ? 7 : h)
            setMinute(isNaN(m) ? 0 : m)
          }
          if (prefs.timezone) setTimezone(prefs.timezone)
          if (prefs.frequency) setFrequency(prefs.frequency as Frequency)
          if (typeof prefs.email_notifications === "boolean") {
            setEmailNotifications(prefs.email_notifications)
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const toggleCustomDay = (day: string) => {
    setCustomDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const digest_time = `${pad(hour)}:${pad(minute)}`
      const res = await fetch("/api/preferences", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          digest_time,
          timezone,
          frequency,
          email_notifications: emailNotifications,
        }),
      })
      const data = await res.json()
      if (data.ok) {
        toast.success("Schedule saved!")
      } else {
        toast.error("Failed to save schedule.")
      }
    } catch {
      toast.error("Failed to save schedule.")
    } finally {
      setSaving(false)
    }
  }

  const preview = useMemo(
    () => getNextDigestLabel(hour, minute, frequency, customDays, timezone),
    [hour, minute, frequency, customDays, timezone]
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading preferences…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Digest Schedule</h1>
        <p className="text-muted-foreground">
          Control when and how often you receive school update digests.
        </p>
      </div>

      {/* ── Timing ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" /> Delivery Time
          </CardTitle>
          <CardDescription>Choose what time your digest is generated each day.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label>Hour</Label>
              <Select
                value={String(hour)}
                onValueChange={(v) => setHour(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue>{formatHour(hour)}</SelectValue>
                </SelectTrigger>
                <SelectContent className="max-h-52">
                  {HOURS.map((h) => (
                    <SelectItem key={h} value={String(h)}>
                      {formatHour(h)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Minute</Label>
              <Select
                value={String(minute)}
                onValueChange={(v) => setMinute(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue>:{pad(minute)}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {MINUTES.map((m) => (
                    <SelectItem key={m} value={String(m)}>
                      :{pad(m)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {TIMEZONES.map((tz) => (
                    <SelectItem key={tz.value} value={tz.value}>
                      {tz.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Frequency ──────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" /> Frequency
          </CardTitle>
          <CardDescription>How often should your digest be generated?</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            {(["daily", "weekdays", "custom"] as Frequency[]).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFrequency(f)}
                className={`rounded-lg border p-3 text-left transition-colors ${
                  frequency === f
                    ? "border-primary bg-primary/5 text-primary font-medium"
                    : "border-border hover:bg-muted/40"
                }`}
              >
                <p className="text-sm font-medium capitalize">{f === "weekdays" ? "Weekdays only" : f === "custom" ? "Custom days" : "Every day"}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {f === "daily" && "Mon – Sun"}
                  {f === "weekdays" && "Mon – Fri"}
                  {f === "custom" && "Pick specific days"}
                </p>
              </button>
            ))}
          </div>

          {frequency === "custom" && (
            <div className="mt-3">
              <Label className="mb-2 block text-sm">Select days</Label>
              <div className="flex flex-wrap gap-2">
                {CUSTOM_DAYS.map((day) => (
                  <button
                    key={day}
                    type="button"
                    onClick={() => toggleCustomDay(day)}
                    className={`rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                      customDays.includes(day)
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-border hover:bg-muted/40 text-foreground"
                    }`}
                  >
                    {day}
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Notifications ──────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" /> Notification Channels
          </CardTitle>
          <CardDescription>Where should Parently send your digest?</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-blue-500/10 p-2 text-blue-600">
                <Bell className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium">In-app notifications</p>
                <p className="text-xs text-muted-foreground">Bell icon in the header</p>
              </div>
            </div>
            <Switch
              checked={inAppNotifications}
              onCheckedChange={setInAppNotifications}
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-red-500/10 p-2 text-red-600">
                <Mail className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium">Email notifications</p>
                <p className="text-xs text-muted-foreground">Daily digest sent to your inbox</p>
              </div>
            </div>
            <Switch
              checked={emailNotifications}
              onCheckedChange={setEmailNotifications}
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between opacity-50">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-green-500/10 p-2 text-green-600">
                <Bell className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium">SMS <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">Coming soon</span></p>
                <p className="text-xs text-muted-foreground">Text message alerts</p>
              </div>
            </div>
            <Switch disabled checked={false} />
          </div>
        </CardContent>
      </Card>

      {/* ── Preview ────────────────────────────────────────── */}
      <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
        <p className="text-sm text-muted-foreground">{preview}</p>
      </div>

      <Button onClick={handleSave} disabled={saving} className="gap-2">
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
        Save Schedule
      </Button>
    </div>
  )
}
