"use client"

import { useCallback, useEffect, useState } from "react"
import {
  Bell,
  Settings,
  Menu,
  Moon,
  Sun,
  LogOut,
  Zap,
  CreditCard,
  CheckCheck,
  User,
  Home,
  FileText,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useTheme } from "next-themes"
import { useSession, signOut } from "next-auth/react"
import Link from "next/link"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

/* ── Types ──────────────────────────────────── */

interface NotificationItem {
  id: number
  digest_id: number | null
  type: string
  title: string
  body: string | null
  is_read: boolean
  created_at: string
}

/* ── Helpers ─────────────────────────────────── */

function timeAgo(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function notifEmoji(type: string) {
  switch (type) {
    case "DIGEST_READY": return "📋"
    case "URGENT_EVENT": return "🚨"
    default: return "🔔"
  }
}

/* ── Component ───────────────────────────────── */

export function Header() {
  const { setTheme, theme } = useTheme()
  const { data: session } = useSession()

  const [plan, setPlan] = useState<string | null>(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [notifOpen, setNotifOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  // Load plan
  useEffect(() => {
    fetch("/api/billing/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) setPlan(data.premium_active ? "PREMIUM" : "FREE")
      })
      .catch(() => {})
  }, [])

  // Poll unread count every 30s
  const fetchUnread = useCallback(async () => {
    try {
      const res = await fetch("/api/notifications/unread-count")
      const data = await res.json()
      if (data.ok) setUnreadCount(data.unread_count)
    } catch { /* silent */ }
  }, [])

  useEffect(() => {
    fetchUnread()
    const interval = setInterval(fetchUnread, 30000)
    return () => clearInterval(interval)
  }, [fetchUnread])

  // Load full list when dropdown opens
  const fetchNotifications = useCallback(async () => {
    try {
      const res = await fetch("/api/notifications?limit=20")
      const data = await res.json()
      if (data.ok) {
        setNotifications(data.notifications)
        setUnreadCount(data.unread_count)
      }
    } catch { /* silent */ }
  }, [])

  const handleBellOpen = (open: boolean) => {
    setNotifOpen(open)
    if (open) fetchNotifications()
  }

  const markRead = async (id: number) => {
    await fetch(`/api/notifications/${id}/read`, { method: "POST" })
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    )
    setUnreadCount((c) => Math.max(0, c - 1))
  }

  const markAllRead = async () => {
    await fetch("/api/notifications/mark-all-read", { method: "POST" })
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    setUnreadCount(0)
  }

  const handleNotifClick = (n: NotificationItem) => {
    if (!n.is_read) markRead(n.id)
  }

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
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>

            {/* ── Bell Notification Dropdown ──── */}
            <DropdownMenu open={notifOpen} onOpenChange={handleBellOpen}>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative">
                  <Bell className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-accent-foreground">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
                <div className="flex items-center justify-between px-3 py-2">
                  <DropdownMenuLabel className="p-0 text-sm">Notifications</DropdownMenuLabel>
                  {unreadCount > 0 && (
                    <button
                      className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                      onClick={(e) => { e.stopPropagation(); markAllRead() }}
                    >
                      <CheckCheck className="h-3 w-3" /> Mark all read
                    </button>
                  )}
                </div>
                <DropdownMenuSeparator />
                {notifications.length === 0 ? (
                  <div className="py-6 text-center text-sm text-muted-foreground">
                    No notifications yet
                  </div>
                ) : (
                  notifications.map((n) => (
                    <DropdownMenuItem
                      key={n.id}
                      className="flex items-start gap-3 px-3 py-2.5 cursor-pointer"
                      onClick={() => handleNotifClick(n)}
                      asChild
                    >
                      <Link href={n.digest_id ? `/dashboard` : "#"}>
                        <span className="text-base mt-0.5">{notifEmoji(n.type)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <p className={`text-sm leading-tight ${n.is_read ? "text-muted-foreground" : "font-semibold text-foreground"}`}>
                              {n.title}
                            </p>
                            {!n.is_read && (
                              <span className="inline-block h-2 w-2 shrink-0 rounded-full bg-accent" />
                            )}
                          </div>
                          {n.body && (
                            <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                              {n.body}
                            </p>
                          )}
                          <p className="text-[10px] text-muted-foreground mt-0.5">
                            {timeAgo(n.created_at)}
                          </p>
                        </div>
                      </Link>
                    </DropdownMenuItem>
                  ))
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* ── User Menu ──────────────────── */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <Avatar className="h-8 w-8">
                    <AvatarImage
                      src={session?.user?.image || ""}
                      alt={session?.user?.name || "User"}
                    />
                    <AvatarFallback>
                      {session?.user?.name?.charAt(0) || "U"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{session?.user?.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {session?.user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/settings?tab=profile">
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/pricing">
                    <CreditCard className="mr-2 h-4 w-4" />
                    Pricing & Plan
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => signOut({ callbackUrl: "/" })}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
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
