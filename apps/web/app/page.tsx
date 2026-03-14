"use client"

import { signIn } from "next-auth/react"
import { useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Mail, Apple, Heart, Sparkles, Shield, Clock, ChevronDown, ChevronUp } from "lucide-react"

export default function LoginPage() {
  const appleEnabled = process.env.NEXT_PUBLIC_APPLE_AUTH_ENABLED === "true"

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-primary/5 flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
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

      {/* Hero */}
      <main className="relative flex-1 flex items-center justify-center px-4 py-12 overflow-hidden">
        {/* Background decorative blobs */}
        <div className="pointer-events-none absolute -left-40 top-1/4 h-96 w-96 rounded-full bg-primary/8 blur-3xl" />
        <div className="pointer-events-none absolute -right-40 bottom-1/4 h-80 w-80 rounded-full bg-accent/8 blur-3xl" />
        <div className="pointer-events-none absolute left-1/2 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-yellow-400/5 blur-3xl" />

        <div className="relative w-full max-w-5xl grid gap-12 lg:grid-cols-2 items-center">
          {/* Left: Value Prop */}
          <div className="space-y-8">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
                <Sparkles className="h-4 w-4" />
                AI-powered school digest
              </div>
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
                  Parently
                </span>
              </h1>
              <p className="mt-3 text-xl text-muted-foreground">
                Your parent&apos;s desk in your pocket 📱
              </p>
            </div>

            <p className="text-lg leading-relaxed text-muted-foreground max-w-lg">
              50 school emails. 3 apps. 1 group chat. <strong className="text-foreground">Sound familiar?</strong> Parently
              gives you a calm <strong className="text-foreground">1-minute daily brief</strong> instead.
            </p>

            {/* Preview digest */}
            <div className="rounded-2xl border border-primary/10 bg-card p-6 shadow-lg shadow-primary/5 animate-[float_6s_ease-in-out_infinite]">
              <div className="mb-4 flex items-center gap-2">
                <span className="text-lg">☕</span>
                <p className="text-sm font-semibold text-foreground">
                  Your morning digest
                </p>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-3 rounded-lg bg-destructive/5 p-2.5">
                  <Badge variant="destructive" className="mt-0.5 shrink-0 text-xs">
                    🔴 Action
                  </Badge>
                  <span className="text-foreground font-medium">Bring costume Friday — Ms. Garcia&apos;s class</span>
                </div>
                <div className="flex items-start gap-3 rounded-lg bg-primary/5 p-2.5">
                  <Badge variant="default" className="mt-0.5 shrink-0 bg-primary text-xs">
                    📝 Due
                  </Badge>
                  <span className="text-foreground font-medium">
                    Permission slip due Thursday
                  </span>
                </div>
                <div className="flex items-start gap-3 rounded-lg bg-muted p-2.5">
                  <Badge variant="secondary" className="mt-0.5 shrink-0 text-xs">
                    ℹ️ Info
                  </Badge>
                  <span className="text-foreground font-medium">
                    Early dismissal at 1pm Wednesday
                  </span>
                </div>
              </div>
            </div>

            {/* Feature pills */}
            <div className="flex flex-wrap gap-2.5">
              {[
                { emoji: "📧", label: "Gmail" },
                { emoji: "📄", label: "PDFs" },
                { emoji: "�", label: "Google Drive" },
                { emoji: "📅", label: "School Calendar" },
                { emoji: "�", label: "School Website" },
              ].map((f) => (
                <div
                  key={f.label}
                  className="flex items-center gap-1.5 rounded-full border border-border/60 bg-card px-3.5 py-2 text-sm font-medium text-muted-foreground shadow-sm transition-all duration-300 hover:bg-primary/10 hover:text-primary hover:border-primary/20 hover:shadow-md hover:-translate-y-0.5"
                >
                  <span>{f.emoji}</span>
                  {f.label}
                </div>
              ))}
            </div>
          </div>

          {/* Right: Login Card */}
          <Card className="mx-auto w-full max-w-md overflow-hidden shadow-2xl shadow-primary/10 ring-1 ring-border/30">
            <CardHeader className="bg-gradient-to-br from-primary/5 to-accent/5 text-center pb-8 pt-8">
              <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-3xl">
                🏠
              </div>
              <CardTitle className="text-2xl">Welcome to Parently</CardTitle>
              <CardDescription className="text-base">
                Join thousands of parents who start their day calm.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-6">
              <Button
                className="w-full gap-2 h-12 text-base font-semibold shadow-md shadow-primary/20"
                size="lg"
                onClick={() => signIn("google", { callbackUrl: "/dashboard", prompt: "select_account" })}
              >
                <Mail className="h-5 w-5" />
                Continue with Google
              </Button>

              <Button
                variant="outline"
                className="w-full gap-2 h-12 text-base font-semibold"
                size="lg"
                disabled={!appleEnabled}
                onClick={() => signIn("apple", { callbackUrl: "/dashboard" })}
              >
                <Apple className="h-5 w-5" />
                {appleEnabled ? "Continue with Apple" : "Apple Login (Coming Soon)"}
              </Button>

              <div className="relative my-2">
                <Separator />
              </div>

              {/* Trust signals */}
              <div className="flex items-center justify-center gap-4 pt-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Shield className="h-3.5 w-3.5" />
                  <span>Private & secure</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  <span>2 min setup</span>
                </div>
                <div className="flex items-center gap-1">
                  <Heart className="h-3.5 w-3.5" />
                  <span>30 free digests</span>
                </div>
              </div>

              <p className="text-center text-[11px] text-muted-foreground pt-1">
                By continuing, you agree to our{" "}
                <a href="/terms" className="underline hover:text-foreground">Terms of Service</a>
                {" "}and{" "}
                <a href="/privacy" className="underline hover:text-foreground">Privacy Policy</a>.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* How it works */}
      <section className="border-t border-border/50 bg-card/50 py-16 px-4">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-center text-2xl font-bold tracking-tight mb-2">How it works</h2>
          <p className="text-center text-muted-foreground mb-10">Set up in under a minute. No third-party accounts needed.</p>
          <div className="grid gap-8 sm:grid-cols-3">
            {[
              { step: "1", emoji: "👶", title: "Add your kids", desc: "Enter their name and school — that's it." },
              { step: "2", emoji: "🔍", title: "We auto-discover", desc: "Parently finds your school's calendar, website, ICS feeds, and PDF schedules automatically." },
              { step: "3", emoji: "☕", title: "Get your daily digest", desc: "A calm 1-minute brief every morning with events, action items, and announcements grouped by child." },
            ].map((item) => (
              <div key={item.step} className="text-center space-y-3">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-3xl">
                  {item.emoji}
                </div>
                <div className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  {item.step}
                </div>
                <h3 className="font-semibold">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 rounded-xl border border-primary/10 bg-primary/5 p-5 text-center">
            <p className="text-sm text-muted-foreground">
              <span className="text-lg mr-1">🧠</span>
              <strong className="text-foreground">Smart email parsing:</strong> Parently automatically detects and extracts school info from <strong>ClassDojo</strong>, <strong>Brightwheel</strong>, <strong>Skyward</strong>, and <strong>Kumon</strong> emails — combined with your school&apos;s public district calendar, website, and other feeds. Just connect Gmail.
            </p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4">
        <div className="mx-auto max-w-2xl">
          <h2 className="text-center text-2xl font-bold tracking-tight mb-2">Frequently asked questions</h2>
          <p className="text-center text-muted-foreground mb-8">Everything you need to know before getting started.</p>
          <div className="space-y-3">
            {[
              { q: "What is Parently?", a: "Parently is an AI-powered daily digest for busy parents. It consolidates school emails, calendars, documents, and announcements into a calm 1-minute morning brief — grouped by child." },
              { q: "How does school discovery work?", a: "Just enter your child's school name and city. Parently uses AI + web crawling to automatically find the school website, calendar page, ICS feeds, and PDF schedules. No third-party API keys needed." },
              { q: "What platforms does it support?", a: "Gmail, Google Drive, and PDF uploads. We also auto-discover your school's public calendar and website. Emails from ClassDojo, Brightwheel, Skyward, and Kumon are automatically parsed from Gmail — no extra setup needed." },
              { q: "Is it free?", a: "Yes! You get 30 free digests to try everything out. After that, unlimited digests are just $3/month." },
              { q: "Is my data secure?", a: "Absolutely. We use encrypted connections, never store raw credentials, and your data is only used to generate your personal digest. We never sell or share your information." },
            ].map((faq, i) => (
              <details key={i} className="group rounded-xl border border-border/60 bg-card">
                <summary className="flex cursor-pointer items-center justify-between p-4 font-medium text-sm">
                  {faq.q}
                  <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
                </summary>
                <div className="px-4 pb-4 text-sm text-muted-foreground">
                  {faq.a}
                </div>
              </details>
            ))}
          </div>
        </div>
      </section>

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
