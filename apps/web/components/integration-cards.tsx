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
import { CheckCircle2, Mail, FolderOpen } from "lucide-react"
import { useSession, signIn } from "next-auth/react"
import { fetchSetupStatusModel } from "@/lib/setup-status"

interface IntegrationDef {
  key: string
  name: string
  description: string
  status: "not_found" | "connected"
  color: string
  emoji: string
  helperText?: string
  actionLabel: string
}

const DEFAULTS: IntegrationDef[] = [
  { key: "gmail", name: "Gmail", description: "School emails and newsletters", status: "not_found", color: "bg-red-500/10 text-red-600", emoji: "📧", actionLabel: "Grant Gmail access" },
  { key: "gdrive", name: "Google Drive", description: "Documents and permission slips", status: "not_found", color: "bg-amber-500/10 text-amber-600", emoji: "📁", actionLabel: "Grant Google Drive access" },
]

export function IntegrationCards() {
  const { data: session } = useSession()
  const [integrations, setIntegrations] = useState<IntegrationDef[]>(DEFAULTS)

  useEffect(() => {
    fetchSetupStatusModel({
      provider: (session as any)?.provider,
      grantedScopes: (session as any)?.grantedScopes,
    })
      .then((model) => {
        setIntegrations((prev) =>
          prev.map((item) => {
            if (item.key === "gmail") {
              const googleSignedIn = ((session as any)?.provider || "") === "google"
              return {
                ...item,
                status: model.gmailConnected ? "connected" : "not_found",
                helperText: model.gmailConnected
                  ? "Connected via Google"
                  : googleSignedIn
                    ? "You’re signed in with Google. Grant Gmail access to include school emails in digests."
                    : "Connect Gmail to include school emails in digests.",
                actionLabel: model.gmailConnected
                  ? "Connected"
                  : googleSignedIn
                    ? "Grant Gmail access"
                    : "Connect Gmail",
              }
            }
            return {
              ...item,
              status: model.driveConnected ? "connected" : "not_found",
              helperText: model.driveConnected
                ? "Connected via Google"
                : "Grant Google Drive access to include permission slips and documents.",
              actionLabel: model.driveConnected
                ? "Connected"
                : ((session as any)?.provider || "") === "google"
                  ? "Grant Google Drive access"
                  : "Connect Google Drive",
            }
          })
        )
      })
      .catch(() => {
        // keep defaults
      })
  }, [session])

  return (
    <div>
      <div className="mb-5 flex items-center gap-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔌</span>
          <div>
            <h2 className="text-xl font-bold text-foreground">
              Gmail & Drive
            </h2>
            <p className="text-base text-muted-foreground">
              Connect your Google tools for richer daily digests.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-primary/10 bg-primary/5 p-4 mb-5">
        <div className="flex items-start gap-3">
          <span className="text-lg mt-0.5">🧠</span>
          <div>
            <p className="text-base font-semibold text-foreground">Smart Email Parsing</p>
            <p className="text-sm text-muted-foreground mt-0.5">
              Parently automatically detects and parses emails from <strong>ClassDojo</strong>, <strong>Brightwheel</strong>, <strong>Skyward</strong>, and <strong>Kumon</strong> — combined with your school&apos;s public district calendar, website, and other feeds to build your daily digest. Just connect Gmail and we handle the rest.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {integrations.map((integration) => (
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
                <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${integration.color}`}>
                  <span className="text-xl">{integration.emoji}</span>
                </div>
                {integration.status === "connected" ? (
                  <Badge
                    variant="outline"
                    className="gap-1 border-emerald-500/20 bg-emerald-500/10 text-emerald-600 text-xs"
                  >
                    <CheckCircle2 className="h-3 w-3" />
                    Connected
                  </Badge>
                ) : (
                  <Badge variant="outline" className="gap-1 text-muted-foreground text-xs">
                    Not connected
                  </Badge>
                )}
              </div>
              <CardTitle className="text-base font-bold mt-2">{integration.name}</CardTitle>
              <CardDescription className="text-sm">
                {integration.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="mb-3 text-sm text-muted-foreground">
                {integration.helperText || "Connect this integration to include more items in your digest."}
              </p>
              <Button
                variant={integration.status === "connected" ? "outline" : "default"}
                className="w-full text-sm font-semibold"
                onClick={() => {
                  if (integration.status === "connected") return
                  signIn("google", {
                    callbackUrl: "/settings?tab=integrations",
                    prompt: "consent",
                    scope:
                      integration.key === "gmail"
                        ? "openid email profile https://www.googleapis.com/auth/gmail.readonly"
                        : "openid email profile https://www.googleapis.com/auth/drive.readonly",
                    access_type: "offline",
                  })
                }}
              >
                {integration.actionLabel}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
