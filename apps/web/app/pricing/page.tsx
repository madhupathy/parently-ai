"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  CheckCircle2,
  Sparkles,
  Zap,
  ArrowLeft,
  HelpCircle,
} from "lucide-react"
import Link from "next/link"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

const FREE_FEATURES = [
  "30 free digests",
  "Gmail + PDF connectors",
  "AI-powered summarization",
  "RAG context retrieval",
  "PWA mobile app",
]

const PREMIUM_FEATURES = [
  "Unlimited daily digests",
  "All connectors included",
  "Priority AI summarization",
  "RAG-powered context retrieval",
  "PWA mobile app",
  "Priority support",
]

const FAQ = [
  {
    q: "What happens when I run out of free digests?",
    a: "You'll see a prompt to upgrade. Your data and settings are preserved — you just can't generate new digests until you subscribe or wait for us to add more free credits.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes! You can cancel your subscription at any time from your Stripe dashboard. You'll keep premium access until the end of your billing period.",
  },
  {
    q: "How does AI summarization work?",
    a: "We use Google's Gemini 1.5 Flash to read your school emails, documents, and connector updates, then generate a calm, prioritized daily digest in seconds.",
  },
  {
    q: "Is my data secure?",
    a: "Absolutely. We use encrypted connections, never store raw credentials, and your data is only used to generate your personal digest. We never sell or share your information.",
  },
  {
    q: "What connectors are supported?",
    a: "Gmail, Google Drive, and PDF uploads. We also auto-discover your school's public calendar and website. Emails from ClassDojo, Brightwheel, Skyward, and Kumon are automatically parsed from Gmail — no extra setup needed!",
  },
]

export default function PricingPage() {
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
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-primary/5">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/80 backdrop-blur">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center gap-4">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/dashboard">
                <ArrowLeft className="h-5 w-5" />
              </Link>
            </Button>
            <Link href="/dashboard" className="flex items-center gap-2">
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

      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Hero */}
        <div className="text-center mb-12">
          <Badge variant="outline" className="mb-4 gap-1.5 px-3 py-1 text-sm">
            <Sparkles className="h-3.5 w-3.5" />
            Simple pricing
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl mb-4">
            Choose your plan
          </h1>
          <p className="text-lg text-muted-foreground max-w-xl mx-auto">
            Start free with 30 digests. Upgrade when you need unlimited access.
          </p>
        </div>

        {/* Plan Cards */}
        <div className="grid gap-8 md:grid-cols-2 max-w-3xl mx-auto mb-16">
          {/* Free */}
          <Card className="relative border-border/60">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl">Free</CardTitle>
                <Badge variant="secondary">Current</Badge>
              </div>
              <div className="mt-2">
                <span className="text-4xl font-bold">$0</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Perfect to get started
              </p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {FREE_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-muted-foreground shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button variant="outline" className="w-full mt-6" disabled>
                Your current plan
              </Button>
            </CardContent>
          </Card>

          {/* Premium */}
          <Card className="relative border-primary/30 shadow-xl shadow-primary/10 ring-1 ring-primary/20">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <Badge className="bg-primary text-primary-foreground gap-1 px-3 py-1 shadow-lg shadow-primary/30">
                <Zap className="h-3 w-3" />
                Most Popular
              </Badge>
            </div>
            <CardHeader className="pb-4 pt-8">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl">Premium</CardTitle>
              </div>
              <div className="mt-2">
                <span className="text-4xl font-bold">$3</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                For busy parents who need it all
              </p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {PREMIUM_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                    <span className="font-medium">{f}</span>
                  </li>
                ))}
              </ul>
              <Button
                className="w-full mt-6 h-11 text-base font-semibold gap-2 shadow-lg shadow-primary/20"
                onClick={handleUpgrade}
                disabled={loading}
              >
                <Zap className="h-4 w-4" />
                {loading ? "Redirecting..." : "Upgrade to Premium"}
              </Button>
              {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
            </CardContent>
          </Card>
        </div>

        {/* FAQ */}
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-2 mb-6">
            <HelpCircle className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-2xl font-bold">Frequently Asked Questions</h2>
          </div>
          <Accordion type="single" collapsible className="w-full">
            {FAQ.map((item, i) => (
              <AccordionItem key={i} value={`faq-${i}`}>
                <AccordionTrigger className="text-left text-sm font-semibold">
                  {item.q}
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground">
                  {item.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 py-6 text-center text-xs text-muted-foreground">
        Made with ❤️ for busy parents &middot; Support: support@parently-ai.com &middot;{" "}
        <a href="/support" className="underline hover:text-foreground">Support</a> &middot;{" "}
        <a href="/privacy" className="underline hover:text-foreground">Privacy</a> &middot;{" "}
        <a href="/terms" className="underline hover:text-foreground">Terms</a> &middot; &copy;{" "}
        {new Date().getFullYear()} Parently
      </footer>
    </div>
  )
}
