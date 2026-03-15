"use client"

import { usePathname } from "next/navigation"
import Link from "next/link"
import { Home, Settings, FileText, Bell } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/digest", label: "Digest", icon: FileText },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border/50 bg-card/95 backdrop-blur-lg supports-[backdrop-filter]:bg-card/80 md:hidden">
      <div className="mx-auto flex h-16 max-w-lg items-center justify-around px-2">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : item.href === "/alerts"
                ? pathname === "/alerts" || pathname === "/notifications"
                : pathname === item.href || pathname.startsWith(`${item.href}/`)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex flex-col items-center justify-center gap-1 rounded-xl px-3 py-2 text-xs transition-all duration-200",
                "min-w-[4rem] active:scale-90",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {isActive && (
                <span className="absolute -top-0.5 left-1/2 h-1 w-8 -translate-x-1/2 rounded-full bg-gradient-to-r from-primary to-accent" />
              )}
              <div className={cn(
                "flex h-8 w-8 items-center justify-center rounded-xl transition-colors",
                isActive && "bg-primary/10"
              )}>
                <item.icon
                  className={cn(
                    "h-5 w-5 transition-colors",
                    isActive && "text-primary"
                  )}
                />
              </div>
              <span className={cn("font-medium", isActive && "font-bold")}>{item.label}</span>
            </Link>
          )
        })}
      </div>
      {/* Safe area padding for phones with home indicators */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  )
}
