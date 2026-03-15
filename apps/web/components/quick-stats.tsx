"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Calendar, Users, CheckCircle2, Zap } from "lucide-react"

function useCountUp(target: number, duration: number = 800) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (target === 0) return
    const steps = 20
    const increment = target / steps
    const interval = duration / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= target) {
        setCount(target)
        clearInterval(timer)
      } else {
        setCount(Math.floor(current))
      }
    }, interval)
    return () => clearInterval(timer)
  }, [target, duration])
  return count
}

export function QuickStats() {
  const [digestsRemaining, setDigestsRemaining] = useState<number | null>(null)
  const [isPremium, setIsPremium] = useState(false)
  const [childrenCount, setChildrenCount] = useState(0)

  useEffect(() => {
    const loadStats = () => {
      fetch("/api/billing/status", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        console.debug("[quick-stats] billing response", data)
        if (data.ok) {
          setDigestsRemaining(data.digests_remaining)
          setIsPremium(data.premium_active)
        }
      })
      .catch((err) => {
        console.error("[quick-stats] billing fetch failed", err)
      })

      fetch("/api/children", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        console.debug("[quick-stats] children response", data)
        if (data.ok) setChildrenCount(data.children?.length || 0)
      })
      .catch((err) => {
        console.error("[quick-stats] children fetch failed", err)
      })
    }

    loadStats()
    const onChildrenUpdated = () => loadStats()
    const onFocus = () => loadStats()
    window.addEventListener("parently:children-updated", onChildrenUpdated)
    window.addEventListener("focus", onFocus)
    return () => {
      window.removeEventListener("parently:children-updated", onChildrenUpdated)
      window.removeEventListener("focus", onFocus)
    }
  }, [])

  const events = useCountUp(4)
  const kids = useCountUp(childrenCount)
  const digests = useCountUp(digestsRemaining ?? 0)

  const stats = [
    {
      label: "Upcoming Events",
      value: String(events),
      emoji: "📅",
      icon: Calendar,
      gradient: "from-purple-500/15 via-purple-500/5 to-transparent",
      iconBg: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
      border: "border-purple-200/50 dark:border-purple-800/30",
    },
    {
      label: "Children",
      value: String(kids),
      emoji: "👶",
      icon: Users,
      gradient: "from-pink-500/15 via-pink-500/5 to-transparent",
      iconBg: "bg-pink-500/10 text-pink-600 dark:text-pink-400",
      border: "border-pink-200/50 dark:border-pink-800/30",
    },
    {
      label: isPremium ? "Plan" : "Digests Left",
      value: isPremium ? "Premium" : String(digests),
      emoji: isPremium ? "⚡" : "✨",
      icon: isPremium ? Zap : CheckCircle2,
      gradient: isPremium
        ? "from-yellow-500/15 via-orange-500/5 to-transparent"
        : "from-emerald-500/15 via-emerald-500/5 to-transparent",
      iconBg: isPremium
        ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
        : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
      border: isPremium
        ? "border-yellow-200/50 dark:border-yellow-800/30"
        : "border-emerald-200/50 dark:border-emerald-800/30",
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {stats.map((stat) => (
        <Card
          key={stat.label}
          className={`relative overflow-hidden bg-gradient-to-br ${stat.gradient} border ${stat.border} p-5 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5`}
        >
          <div className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${stat.iconBg}`}>
              <span className="text-xl">{stat.emoji}</span>
            </div>
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">{stat.label}</p>
              <p className="text-[2rem] font-bold tabular-nums text-foreground leading-none">
                {stat.value}
              </p>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
