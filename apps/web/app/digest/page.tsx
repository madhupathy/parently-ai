"use client"

import { DailyDigest } from "@/components/daily-digest"

export default function DigestPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Digest</h1>
        <p className="text-muted-foreground">
          Review today&apos;s digest and your recent digest history.
        </p>
      </div>
      <DailyDigest />
    </div>
  )
}
