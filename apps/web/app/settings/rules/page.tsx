"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Loader2, Trash2, Plus, ChevronLeft, Filter } from "lucide-react"
import { toast } from "sonner"

/* ── Types ──────────────────────────────────────── */

type RuleType = "always_important" | "never_notify" | "tag"
type RuleField = "sender" | "subject" | "body"

interface DigestRule {
  id: number
  rule_type: RuleType
  field: RuleField
  pattern: string
  label: string | null
  created_at: string
}

/* ── Helpers ────────────────────────────────────── */

const RULE_TYPE_LABELS: Record<RuleType, { label: string; color: string }> = {
  always_important: { label: "Always important", color: "bg-destructive/10 text-destructive border-destructive/20" },
  never_notify: { label: "Never notify", color: "bg-muted text-muted-foreground" },
  tag: { label: "Tag as", color: "bg-primary/10 text-primary border-primary/20" },
}

const FIELD_LABELS: Record<RuleField, string> = {
  sender: "Sender",
  subject: "Subject",
  body: "Body",
}

function ruleDescription(rule: DigestRule): string {
  const fieldLabel = FIELD_LABELS[rule.field]
  const ruleLabel = RULE_TYPE_LABELS[rule.rule_type].label
  if (rule.rule_type === "tag" && rule.label) {
    return `If ${fieldLabel.toLowerCase()} contains "${rule.pattern}" → tag as "${rule.label}"`
  }
  return `If ${fieldLabel.toLowerCase()} contains "${rule.pattern}" → ${ruleLabel.toLowerCase()}`
}

/* ── Page ───────────────────────────────────────── */

export default function RulesPage() {
  const [rules, setRules] = useState<DigestRule[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<number | null>(null)

  // Form state
  const [ruleType, setRuleType] = useState<RuleType>("always_important")
  const [field, setField] = useState<RuleField>("sender")
  const [pattern, setPattern] = useState("")
  const [label, setLabel] = useState("")

  const fetchRules = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/rules")
      if (!res.ok) return
      const data = await res.json()
      if (data.ok) setRules(data.rules || [])
    } catch {
      toast.error("Failed to load rules")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRules()
  }, [fetchRules])

  const handleAdd = async () => {
    if (!pattern.trim()) {
      toast.error("Pattern is required")
      return
    }
    if (ruleType === "tag" && !label.trim()) {
      toast.error("Label is required for tag rules")
      return
    }
    setSaving(true)
    try {
      const res = await fetch("/api/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rule_type: ruleType,
          field,
          pattern: pattern.trim(),
          label: ruleType === "tag" ? label.trim() : null,
        }),
      })
      if (res.ok) {
        toast.success("Rule added")
        setPattern("")
        setLabel("")
        fetchRules()
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err?.detail?.[0]?.msg || err?.detail || "Failed to add rule")
      }
    } catch {
      toast.error("Network error")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (ruleId: number) => {
    setDeleting(ruleId)
    try {
      const res = await fetch(`/api/rules/${ruleId}`, { method: "DELETE" })
      if (res.ok) {
        setRules((prev) => prev.filter((r) => r.id !== ruleId))
        toast.success("Rule deleted")
      } else {
        toast.error("Failed to delete rule")
      }
    } catch {
      toast.error("Network error")
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="gap-1">
          <Link href="/settings">
            <ChevronLeft className="h-4 w-4" /> Settings
          </Link>
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Filter className="h-6 w-6" /> Priority Rules
          </h1>
          <p className="text-muted-foreground text-sm">
            Teach Parently what to always flag or ignore in your school emails.
          </p>
        </div>
      </div>

      {/* Add rule form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Plus className="h-4 w-4" /> Add a Rule
          </CardTitle>
          <CardDescription>
            Define how Parently should handle matching emails in your digest.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label>If</Label>
              <Select value={field} onValueChange={(v) => setField(v as RuleField)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sender">Sender</SelectItem>
                  <SelectItem value="subject">Subject</SelectItem>
                  <SelectItem value="body">Body</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label>contains</Label>
              <Input
                placeholder={
                  field === "sender"
                    ? "e.g. principal, @rrisd.org"
                    : field === "subject"
                      ? "e.g. permission slip, field trip"
                      : "e.g. urgent, important"
                }
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Then</Label>
              <Select value={ruleType} onValueChange={(v) => setRuleType(v as RuleType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="always_important">Mark as always important</SelectItem>
                  <SelectItem value="never_notify">Never notify about</SelectItem>
                  <SelectItem value="tag">Tag as...</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {ruleType === "tag" && (
              <div className="space-y-1.5">
                <Label>Tag label</Label>
                <Input
                  placeholder="e.g. Field Trip, Fundraiser"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </div>
            )}
          </div>

          <Button
            onClick={handleAdd}
            disabled={saving || !pattern.trim() || (ruleType === "tag" && !label.trim())}
            className="gap-2"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add Rule
          </Button>
        </CardContent>
      </Card>

      {/* Existing rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your Rules</CardTitle>
          <CardDescription>
            {rules.length === 0
              ? "No rules yet. Add one above."
              : `${rules.length} rule${rules.length !== 1 ? "s" : ""} active`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading rules...
            </div>
          ) : rules.length === 0 ? (
            <div className="text-center py-8 space-y-2">
              <Filter className="h-10 w-10 mx-auto text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">
                No rules yet. Add your first rule above.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-4 py-3"
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <Badge
                      variant="outline"
                      className={`shrink-0 text-xs ${RULE_TYPE_LABELS[rule.rule_type].color}`}
                    >
                      {RULE_TYPE_LABELS[rule.rule_type].label}
                    </Badge>
                    <p className="text-sm text-foreground line-clamp-2">
                      {ruleDescription(rule)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 ml-3 text-muted-foreground hover:text-destructive"
                    disabled={deleting === rule.id}
                    onClick={() => handleDelete(rule.id)}
                  >
                    {deleting === rule.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Rules are applied the next time a digest is generated. Patterns match case-insensitively.
      </p>
    </div>
  )
}
