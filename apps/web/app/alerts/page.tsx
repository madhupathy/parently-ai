"use client"

import { useCallback, useEffect, useState } from "react"
import { Bell, CheckCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface NotificationItem {
  id: number
  digest_id: number | null
  type: string
  title: string
  body: string | null
  is_read: boolean
  created_at: string
}

function getRelativeTime(dateStr: string) {
  const created = new Date(dateStr).getTime()
  const minutes = Math.floor((Date.now() - created) / 60000)
  if (minutes < 1) return "Just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function AlertsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/notifications?limit=50")
      const data = await res.json()
      if (data.ok) {
        setNotifications(data.notifications || [])
        setUnreadCount(data.unread_count || 0)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAlerts()
  }, [loadAlerts])

  const markAllRead = async () => {
    await fetch("/api/notifications/mark-all-read", { method: "POST" })
    setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })))
    setUnreadCount(0)
  }

  const markRead = async (id: number) => {
    await fetch(`/api/notifications/${id}/read`, { method: "POST" })
    setNotifications((prev) =>
      prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
    )
    setUnreadCount((count) => Math.max(0, count - 1))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Alerts</h1>
          <p className="text-muted-foreground">All notifications for your account.</p>
        </div>
        <Button variant="outline" size="sm" onClick={markAllRead} disabled={unreadCount === 0}>
          <CheckCheck className="mr-1.5 h-4 w-4" />
          Mark all read
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Notifications{" "}
            {unreadCount > 0 && (
              <Badge variant="secondary" className="ml-2">
                {unreadCount} unread
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading alerts...</p>
          ) : notifications.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/70 py-8 text-center">
              <Bell className="mx-auto mb-2 h-6 w-6 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No alerts yet.</p>
            </div>
          ) : (
            notifications.map((item) => (
              <button
                key={item.id}
                onClick={() => !item.is_read && markRead(item.id)}
                className="w-full rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-muted/30"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className={`text-sm ${item.is_read ? "text-muted-foreground" : "font-semibold"}`}>
                    {item.title}
                  </p>
                  {!item.is_read && <span className="mt-1 h-2 w-2 rounded-full bg-primary" />}
                </div>
                {item.body && <p className="mt-1 text-xs text-muted-foreground">{item.body}</p>}
                <p className="mt-1 text-[11px] text-muted-foreground">{getRelativeTime(item.created_at)}</p>
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
