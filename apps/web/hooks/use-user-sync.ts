"use client"

import { useEffect, useRef } from "react"
import { useSession } from "next-auth/react"

/**
 * Syncs the NextAuth session user to the backend on login.
 * Calls POST /api/auth/sync once per session to ensure the
 * backend has a matching User row.
 */
export function useUserSync() {
  const { data: session, status } = useSession()
  const synced = useRef(false)

  useEffect(() => {
    if (status !== "authenticated" || !session?.user?.email || synced.current) {
      return
    }

    synced.current = true

    fetch("/api/auth/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: session.user.email,
        name: session.user.name,
        image: session.user.image,
        provider: (session as any).provider || "google",
        access_token: (session as any).accessToken || null,
        refresh_token: (session as any).refreshToken || null,
        access_token_expires_at: (session as any).accessTokenExpiresAt || null,
        granted_scopes: (session as any).grantedScopes || null,
        token_uri: "https://oauth2.googleapis.com/token",
      }),
    }).catch((err) => {
      console.error("Failed to sync user to backend:", err)
      synced.current = false // allow retry
    })
  }, [session, status])
}
