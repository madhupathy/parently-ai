"use client"

import { useCallback, useEffect, useState } from "react"
import { Bell, CheckCheck, BookOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import Link from "next/link"

/* ─── Types ──────────────────────────────────────────── */

interface NotificationItem {
  id: number
  digest_id: number | null
  type: string
  title: string
  body: string | null
  is_read: boolean
  created_at: string
}

/* ─── Helpers ─────────────────────────────────────────── */

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  const diffMs = Date.now() - d.getTime()
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function notifIcon(type: string) {
  switch (type) {
    case "DIGEST_READY":
      return <BookOpen className="h-4 w-4 text-primary" />
    case "URGENT_EVENT":
      return <Bell className="h-4 w-4 text-destructive" />
    default:
      return <Bell className="h-4 w-4 text-muted-foreground" />
  }
}

/* ─── Component ───────────────────────────────────────── */

interface NotificationCenterProps {
  /** Poll interval in milliseconds (default 30 000). */
  pollInterval?: number
}

export function NotificationCenter({ pollInterval = 30_000 }: NotificationCenterProps) {
  const [open, setOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])

  /* Poll unread count */
  const fetchUnread = useCallback(async () => {
    try {
      const res = await fetch("/api/notifications/unread-count")
      const data = await res.json()
      if (data.ok) setUnreadCount(data.unread_count)
    } catch {
      // ignore network errors during polling
    }
  }, [])

  useEffect(() => {
    fetchUnread()
    const id = setInterval(fetchUnread, pollInterval)
    return () => clearInterval(id)
  }, [fetchUnread, pollInterval])

  /* Load full list when dropdown opens */
  const fetchNotifications = useCallback(async () => {
    try {
      const res = await fetch("/api/notifications?limit=20")
      const data = await res.json()
      if (data.ok) {
        setNotifications(data.notifications)
        setUnreadCount(data.unread_count)
      }
    } catch {
      // ignore
    }
  }, [])

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    if (next) fetchNotifications()
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

  return (
    <DropdownMenu open={open} onOpenChange={handleOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-accent-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
        {/* Header row */}
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

        {/* Notification list */}
        {notifications.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            No notifications yet
          </div>
        ) : (
          notifications.map((n) => (
            <DropdownMenuItem
              key={n.id}
              className="flex items-start gap-3 px-3 py-2.5 cursor-pointer"
              onClick={() => { if (!n.is_read) markRead(n.id) }}
              asChild
            >
              <Link href={n.digest_id ? "/digest" : "#"}>
                <span className="mt-0.5 shrink-0">{notifIcon(n.type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p
                      className={`text-sm leading-tight ${
                        n.is_read ? "text-muted-foreground" : "font-semibold text-foreground"
                      }`}
                    >
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

        <DropdownMenuSeparator />
        <div className="px-3 py-2">
          <Link
            href="/settings?tab=notifications"
            className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setOpen(false)}
          >
            Notification settings →
          </Link>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
