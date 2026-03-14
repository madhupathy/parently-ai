"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, Sparkles, Zap } from "lucide-react"

interface UpgradeModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function UpgradeModal({ open, onOpenChange }: UpgradeModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleUpgrade = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/billing/create-checkout-session", {
        method: "POST",
        credentials: "include",
      })
      const data = await res.json()
      if (data.checkout_url) {
        window.location.href = data.checkout_url
        return
      }
      setError(data?.detail || data?.error || "Unable to start checkout.")
    } catch {
      setError("Unable to start checkout.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20">
            <Sparkles className="h-7 w-7 text-primary" />
          </div>
          <DialogTitle className="text-xl">Upgrade to Premium</DialogTitle>
          <DialogDescription>
            You&apos;ve used all your free digests. Upgrade for unlimited access.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-accent/5 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-lg">Premium</h3>
                <p className="text-sm text-muted-foreground">Everything you need</p>
              </div>
              <div className="text-right">
                <span className="text-3xl font-bold">$3</span>
                <span className="text-muted-foreground">/mo</span>
              </div>
            </div>

            <ul className="space-y-2.5">
              {[
                "Unlimited daily digests",
                "Priority AI summarization",
                "All connectors included",
                "RAG-powered context retrieval",
                "Cancel anytime",
              ].map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>

          <Button
            className="w-full h-12 text-base font-semibold gap-2 shadow-lg shadow-primary/20"
            onClick={handleUpgrade}
            disabled={loading}
          >
            <Zap className="h-4 w-4" />
            {loading ? "Redirecting to Stripe..." : "Upgrade for $3/month"}
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Secure payment via Stripe. Cancel anytime.
          </p>
          {error ? (
            <p className="text-center text-xs text-destructive">{error}</p>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
