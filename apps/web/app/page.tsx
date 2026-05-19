"use client"

import { signIn } from "next-auth/react"
import { useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Mail,
  Apple,
  Heart,
  Sparkles,
  Shield,
  Clock,
  ChevronDown,
  Star,
  CheckCircle2,
  X,
  Search,
  Bell,
} from "lucide-react"

/* ── Sample Digest Modal ──────────────────────────── */

function SampleDigestModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>☕</span> Sample Daily Digest — Monday, Jan 13
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-sm mt-2">
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="destructive" className="text-xs">🔴 Action Required</Badge>
              <span className="font-semibold">Emma · Westlake Elementary</span>
            </div>
            <p className="font-medium">Permission slip due Friday — Science Museum trip</p>
            <p className="text-muted-foreground text-xs">
              Ms. Garcia&apos;s class is visiting the Austin Science Museum on Jan 17. Return signed permission slip
              with $12 fee by Friday. Contact office@westlake.rrisd.org with questions.
            </p>
          </div>

          <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 space-y-1">
            <div className="flex items-center gap-2">
              <Badge className="text-xs bg-primary">📅 Event</Badge>
              <span className="font-semibold">Emma · Westlake Elementary</span>
            </div>
            <p className="font-medium">Talent Show auditions — Wednesday 3:30 PM</p>
            <p className="text-muted-foreground text-xs">
              Auditions for the Spring Talent Show will be held in the gymnasium on Wednesday.
              Students must sign up with their homeroom teacher by Tuesday.
            </p>
          </div>

          <div className="rounded-lg border border-border/50 bg-muted/30 p-3 space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-xs">ℹ️ Info</Badge>
              <span className="font-semibold">Noah · Cedar Ridge Middle</span>
            </div>
            <p className="font-medium">Early dismissal Wednesday at 1:00 PM</p>
            <p className="text-muted-foreground text-xs">
              Cedar Ridge will have early dismissal this Wednesday for teacher professional development.
              After-school programs are canceled. Plan alternate pickup arrangements.
            </p>
          </div>

          <div className="rounded-lg border border-accent/20 bg-accent/5 p-3 space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs border-accent/40 text-accent">📝 Reminder</Badge>
              <span className="font-semibold">Noah · Cedar Ridge Middle</span>
            </div>
            <p className="font-medium">Math olympiad registration closes Jan 20</p>
            <p className="text-muted-foreground text-xs">
              Students interested in the district Math Olympiad can register through the school portal.
              Deadline is January 20th. Contact Mr. Thompson for details.
            </p>
          </div>

          <div className="rounded-lg border border-border/40 bg-muted/20 p-3 space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-xs">📄 Document</Badge>
              <span className="font-semibold">Emma · Westlake Elementary</span>
            </div>
            <p className="font-medium">January Newsletter — Key dates inside</p>
            <p className="text-muted-foreground text-xs">
              The January newsletter was shared via Google Drive. Key dates: Jan 20 — No school (MLK Day),
              Jan 27 — Report cards sent home, Feb 3 — Parent-teacher conferences.
            </p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground text-center pt-2">
          This is a realistic example. Your actual digest is generated from your school&apos;s real emails and calendar.
        </p>
      </DialogContent>
    </Dialog>
  )
}

/* ── Page ──────────────────────────────────────────── */

export default function LoginPage() {
  const appleEnabled = process.env.NEXT_PUBLIC_APPLE_AUTH_ENABLED === "true"
  const [showSampleDigest, setShowSampleDigest] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-primary/5 flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-2">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-2xl">🏠</span>
              <span className="text-xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
                  Parently
                </span>
              </span>
            </Link>
            <nav className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-foreground hidden sm:inline-flex"
                onClick={() => setShowSampleDigest(true)}
              >
                See a sample
              </Button>
              <Button
                size="sm"
                onClick={() => signIn("google", { callbackUrl: "/dashboard", prompt: "select_account" })}
              >
                Get started free
              </Button>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="relative flex-1 flex items-center justify-center px-4 py-16 overflow-hidden">
        {/* Background decorative blobs */}
        <div className="pointer-events-none absolute -left-40 top-1/4 h-96 w-96 rounded-full bg-primary/8 blur-3xl" />
        <div className="pointer-events-none absolute -right-40 bottom-1/4 h-80 w-80 rounded-full bg-accent/8 blur-3xl" />
        <div className="pointer-events-none absolute left-1/2 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-yellow-400/5 blur-3xl" />

        <div className="relative w-full max-w-5xl grid gap-12 lg:grid-cols-2 items-center">
          {/* Left: Value Prop */}
          <div className="space-y-8">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
                <Sparkles className="h-4 w-4" />
                AI-powered school digest
              </div>
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-5xl leading-tight">
                Stop missing important{" "}
                <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
                  school emails
                </span>{" "}
                buried in your inbox
              </h1>
              <p className="mt-4 text-lg leading-relaxed text-muted-foreground max-w-lg">
                50 school emails. 3 apps. 1 group chat. Parently turns the chaos into a calm{" "}
                <strong className="text-foreground">1-minute daily brief</strong> — grouped by child, every morning.
              </p>
            </div>

            {/* CTA */}
            <div className="flex flex-wrap gap-3">
              <Button
                className="h-12 px-6 text-base font-semibold gap-2 shadow-lg shadow-primary/20"
                size="lg"
                onClick={() => signIn("google", { callbackUrl: "/dashboard", prompt: "select_account" })}
              >
                <Mail className="h-5 w-5" />
                Start free with Google
              </Button>
              <Button
                variant="outline"
                className="h-12 px-6 text-base font-semibold gap-2"
                size="lg"
                onClick={() => setShowSampleDigest(true)}
              >
                See a sample digest
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              30 free digests. No credit card required.
            </p>

            {/* Feature pills */}
            <div className="flex flex-wrap gap-2">
              {[
                { emoji: "📧", label: "Gmail" },
                { emoji: "📄", label: "PDFs" },
                { emoji: "📁", label: "Google Drive" },
                { emoji: "📅", label: "School Calendar" },
                { emoji: "🌐", label: "School Website" },
                { emoji: "🔍", label: "Search History" },
              ].map((f) => (
                <div
                  key={f.label}
                  className="flex items-center gap-1.5 rounded-full border border-border/60 bg-card px-3.5 py-2 text-sm font-medium text-muted-foreground shadow-sm transition-all duration-300 hover:bg-primary/10 hover:text-primary hover:border-primary/20"
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
      <section className="border-t border-border/50 bg-card/50 py-20 px-4">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-12">
            <Badge variant="outline" className="mb-4 text-xs">How it works</Badge>
            <h2 className="text-3xl font-bold tracking-tight mb-3">Set up in under 2 minutes</h2>
            <p className="text-muted-foreground text-lg">No third-party accounts. No complicated setup.</p>
          </div>
          <div className="grid gap-8 sm:grid-cols-3">
            {[
              {
                step: "1",
                emoji: "📧",
                title: "Connect Gmail",
                desc: "Sign in with your Google account and grant read-only Gmail access. Parently never stores your emails.",
              },
              {
                step: "2",
                emoji: "🤖",
                title: "AI reads school emails",
                desc: "Our AI scans for school emails, calendars, PDFs, and announcements — filtering out everything that isn't school-related.",
              },
              {
                step: "3",
                emoji: "☕",
                title: "Get your daily digest",
                desc: "Every morning you receive a calm 1-minute brief with events, action items, and announcements grouped by child.",
              },
            ].map((item) => (
              <div key={item.step} className="relative text-center space-y-4">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-3xl shadow-sm">
                  {item.emoji}
                </div>
                <div className="absolute top-5 left-1/2 hidden sm:block">
                </div>
                <div className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  {item.step}
                </div>
                <h3 className="font-bold text-lg">{item.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-12 rounded-xl border border-primary/10 bg-primary/5 p-5 text-center">
            <p className="text-sm text-muted-foreground">
              <span className="text-lg mr-1">🧠</span>
              <strong className="text-foreground">Smart email parsing:</strong> Parently automatically detects and extracts school info from <strong>ClassDojo</strong>, <strong>Brightwheel</strong>, <strong>Skyward</strong>, and <strong>Kumon</strong> emails — combined with your school&apos;s public district calendar, website, and other feeds.
            </p>
          </div>
        </div>
      </section>

      {/* Feature highlights */}
      <section className="py-20 px-4">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-12">
            <Badge variant="outline" className="mb-4 text-xs">Features</Badge>
            <h2 className="text-3xl font-bold tracking-tight mb-3">Everything you need, nothing you don&apos;t</h2>
            <p className="text-muted-foreground text-lg">Built specifically for busy parents managing multiple kids and schools.</p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: "☕",
                title: "Daily morning digest",
                desc: "A calm, structured overview of school communications arrives every morning at your preferred time.",
              },
              {
                icon: "👧",
                title: "Per-child dashboard",
                desc: "Each child gets their own view with upcoming events, action items, and digest history.",
              },
              {
                icon: "🔍",
                title: "Search digest history",
                desc: "Instantly find any email, event, or announcement from past digests by keyword or child.",
              },
              {
                icon: "🎯",
                title: "Priority rules",
                desc: "Teach Parently what matters most — always flag emails from the principal, never notify for fundraisers.",
              },
              {
                icon: "📅",
                title: "Auto-discover calendar",
                desc: "Parently automatically finds your school's calendar, ICS feeds, and PDF schedules. No manual setup.",
              },
              {
                icon: "🔔",
                title: "Urgent alerts",
                desc: "Get notified immediately when something truly needs your attention — permission slips, school closures.",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="group rounded-xl border border-border/60 bg-card p-5 space-y-3 hover:border-primary/30 hover:shadow-md hover:shadow-primary/5 transition-all duration-200"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-2xl group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <h3 className="font-semibold">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials / Social proof */}
      <section className="border-t border-border/50 bg-card/50 py-20 px-4">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-12">
            <Badge variant="outline" className="mb-4 text-xs">What parents say</Badge>
            <h2 className="text-3xl font-bold tracking-tight mb-3">Parents love having one place for everything</h2>
          </div>
          <div className="grid gap-5 sm:grid-cols-3">
            {[
              {
                quote: "I used to dread Monday mornings because I&apos;d forgotten something from school emails over the weekend. Now I just check my Parently digest with my coffee.",
                name: "Sarah M.",
                role: "Mom of 2, Austin TX",
                stars: 5,
              },
              {
                quote: "My kids go to different schools. Keeping track of both was a nightmare. Parently organizes everything by child automatically — it&apos;s exactly what I needed.",
                name: "James K.",
                role: "Dad of 3, Chicago IL",
                stars: 5,
              },
              {
                quote: "The permission slip reminder saved me twice already. I had no idea the AI could pull that kind of detail out of a newsletter PDF.",
                name: "Priya R.",
                role: "Mom of 1, Seattle WA",
                stars: 5,
              },
            ].map((t, idx) => (
              <div key={idx} className="rounded-xl border border-border/60 bg-card p-5 space-y-4">
                <div className="flex gap-0.5">
                  {Array.from({ length: t.stars }).map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed italic">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div>
                  <p className="text-sm font-semibold">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-center text-xs text-muted-foreground mt-6">
            Testimonials are illustrative. Parently is in active development.
          </p>
        </div>
      </section>

      {/* Pricing callout */}
      <section className="py-20 px-4">
        <div className="mx-auto max-w-2xl text-center space-y-6">
          <Badge variant="outline" className="text-xs">Pricing</Badge>
          <h2 className="text-3xl font-bold tracking-tight">Simple, honest pricing</h2>
          <div className="grid gap-4 sm:grid-cols-2 text-left">
            <div className="rounded-xl border border-border/60 bg-card p-6 space-y-4">
              <div>
                <p className="text-lg font-bold">Free</p>
                <p className="text-3xl font-bold mt-1">$0</p>
                <p className="text-xs text-muted-foreground mt-1">forever</p>
              </div>
              <ul className="space-y-2 text-sm">
                {["30 free digests", "All sources (Gmail, Drive, Calendar)", "Per-child dashboard", "Search history"].map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => signIn("google", { callbackUrl: "/dashboard", prompt: "select_account" })}
              >
                Start free
              </Button>
            </div>
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-6 space-y-4 relative overflow-hidden">
              <div className="absolute top-3 right-3">
                <Badge className="text-xs bg-primary">Most popular</Badge>
              </div>
              <div>
                <p className="text-lg font-bold">Premium</p>
                <p className="text-3xl font-bold mt-1">$3<span className="text-base font-normal text-muted-foreground">/mo</span></p>
                <p className="text-xs text-muted-foreground mt-1">cancel anytime</p>
              </div>
              <ul className="space-y-2 text-sm">
                {["Unlimited daily digests", "Full digest history (1 year)", "Priority rules & custom tags", "Email delivery", "Early access to new features"].map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                className="w-full gap-2 shadow-md shadow-primary/20"
                onClick={() => signIn("google", { callbackUrl: "/dashboard", prompt: "select_account" })}
              >
                <Sparkles className="h-4 w-4" />
                Get Premium
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-border/50 bg-card/50 py-20 px-4">
        <div className="mx-auto max-w-2xl">
          <div className="text-center mb-10">
            <Badge variant="outline" className="mb-4 text-xs">FAQ</Badge>
            <h2 className="text-3xl font-bold tracking-tight">Frequently asked questions</h2>
          </div>
          <div className="space-y-3">
            {[
              {
                q: "What is Parently?",
                a: "Parently is an AI-powered daily digest for busy parents. It consolidates school emails, calendars, documents, and announcements into a calm 1-minute morning brief — grouped by child.",
              },
              {
                q: "How does school discovery work?",
                a: "Just enter your child's school name and city. Parently uses AI + web crawling to automatically find the school website, calendar page, ICS feeds, and PDF schedules. No third-party API keys needed.",
              },
              {
                q: "What email platforms does it support?",
                a: "Gmail. We also auto-discover your school's public calendar and website. Emails from ClassDojo, Brightwheel, Skyward, and Kumon are automatically parsed — no extra setup needed.",
              },
              {
                q: "Can I search my digest history?",
                a: "Yes. Parently includes full-text search across all your past digests. Search by keyword, event name, or filter by child to find anything instantly.",
              },
              {
                q: "What are priority rules?",
                a: "Priority rules let you teach Parently what matters most to you. For example: 'If sender contains principal → always important' or 'If subject contains fundraiser → never notify'. Parently applies these rules when generating each digest.",
              },
              {
                q: "Is my data secure?",
                a: "We use encrypted connections, never store raw credentials, and your Gmail data is only processed to generate your personal digest. We never sell or share your information.",
              },
            ].map((faq, i) => (
              <details key={i} className="group rounded-xl border border-border/60 bg-card">
                <summary className="flex cursor-pointer items-center justify-between p-4 font-medium text-sm">
                  {faq.q}
                  <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180 shrink-0 ml-2" />
                </summary>
                <div className="px-4 pb-4 text-sm text-muted-foreground leading-relaxed">
                  {faq.a}
                </div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-20 px-4 text-center">
        <div className="mx-auto max-w-xl space-y-6">
          <h2 className="text-3xl font-bold tracking-tight">Ready to reclaim your mornings?</h2>
          <p className="text-muted-foreground text-lg">
            Join parents who start their day with a calm 1-minute school brief instead of inbox anxiety.
          </p>
          <Button
            className="h-12 px-8 text-base font-semibold gap-2 shadow-lg shadow-primary/20"
            size="lg"
            onClick={() => signIn("google", { callbackUrl: "/dashboard", prompt: "select_account" })}
          >
            <Mail className="h-5 w-5" />
            Get started free — takes 2 minutes
          </Button>
          <p className="text-xs text-muted-foreground">30 free digests. No credit card required.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 py-8 px-4">
        <div className="mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="text-xl">🏠</span>
            <span className="font-semibold text-foreground">Parently</span>
            <span>&mdash; Made with ❤️ for busy parents</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="/support" className="underline hover:text-foreground">Support</a>
            <a href="/privacy" className="underline hover:text-foreground">Privacy</a>
            <a href="/terms" className="underline hover:text-foreground">Terms</a>
            <span>&copy; {new Date().getFullYear()} Parently</span>
          </div>
        </div>
      </footer>

      <SampleDigestModal open={showSampleDigest} onClose={() => setShowSampleDigest(false)} />
    </div>
  )
}
