"use client"

import { useEffect, useState } from "react"
import {
  Settings,
  Menu,
  Moon,
  Sun,
  LogOut,
  Zap,
  CreditCard,
  Bell,
  Home,
  FileText,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useTheme } from "next-themes"
import { signOut } from "next-auth/react"
import Link from "next/link"
import { UserMenu } from "@/components/UserMenu"
import { NotificationCenter } from "@/components/notification-center"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

/* ── Component ───────────────────────────────── */

export function Header() {
  const { setTheme, theme } = useTheme()

  const [plan, setPlan] = useState<string | null>(null)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  // Load billing plan badge
  useEffect(() => {
    fetch("/api/billing/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) setPlan(data.premium_active ? "PREMIUM" : "FREE")
      })
      .catch(() => {})
  }, [])

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <Link href="/" className="flex items-center gap-2">
              <span className="text-2xl" role="img" aria-label="Parently">🏠</span>
              <span className="text-xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
                  Parently
                </span>
              </span>
              {plan && (
                <Badge
                  variant={plan === "PREMIUM" ? "default" : "secondary"}
                  className={`text-[10px] px-1.5 py-0 h-5 ${
                    plan === "PREMIUM"
                      ? "bg-gradient-to-r from-yellow-500 to-orange-500 text-white border-0"
                      : ""
                  }`}
                >
                  {plan === "PREMIUM" && <Zap className="h-2.5 w-2.5 mr-0.5" />}
                  {plan}
                </Badge>
              )}
            </Link>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard">Dashboard</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/pricing">Pricing</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/settings">Settings</Link>
            </Button>
          </nav>

          <div className="flex items-center gap-2">
            {/* Theme toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>

            {/* Notification center */}
            <NotificationCenter />

            <UserMenu />
          </div>
        </div>
      </div>

      {/* Mobile side-nav drawer */}
      <Dialog open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <DialogContent className="left-0 top-0 h-dvh w-[82vw] max-w-[22rem] translate-x-0 translate-y-0 rounded-none border-r border-l-0 border-y-0 p-0 sm:max-w-[22rem]">
          <DialogHeader className="border-b border-border/60 px-5 py-4">
            <DialogTitle className="text-base">Menu</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col p-3">
            <Button variant="ghost" className="justify-start gap-2" asChild>
              <Link href="/dashboard" onClick={() => setMobileNavOpen(false)}>
                <Home className="h-4 w-4" />
                Home
              </Link>
            </Button>
            <Button variant="ghost" className="justify-start gap-2" asChild>
              <Link href="/digest" onClick={() => setMobileNavOpen(false)}>
                <FileText className="h-4 w-4" />
                Digest
              </Link>
            </Button>
            <Button variant="ghost" className="justify-start gap-2" asChild>
              <Link href="/alerts" onClick={() => setMobileNavOpen(false)}>
                <Bell className="h-4 w-4" />
                Alerts
              </Link>
            </Button>
            <Button variant="ghost" className="justify-start gap-2" asChild>
              <Link href="/settings" onClick={() => setMobileNavOpen(false)}>
                <Settings className="h-4 w-4" />
                Settings
              </Link>
            </Button>
            <Button variant="ghost" className="justify-start gap-2" asChild>
              <Link href="/settings?tab=billing" onClick={() => setMobileNavOpen(false)}>
                <CreditCard className="h-4 w-4" />
                Billing
              </Link>
            </Button>
            <div className="my-2 border-t border-border/60" />
            <Button
              variant="ghost"
              className="justify-start gap-2 text-destructive hover:text-destructive"
              onClick={() => {
                setMobileNavOpen(false)
                signOut({ callbackUrl: "/" })
              }}
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </header>
  )
}
