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
  const lastSyncKey = useRef<string>("")

  useEffect(() => {
    if (status !== "authenticated" || !session?.user?.email) {
      return
    }

    const provider =
      (session as any).provider ||
      (session as any).jwt?.provider ||
      "google"
    const payload = {
      email: session.user.email,
      name: session.user.name,
      image: session.user.image,
      provider,
      access_token: (session as any).accessToken || null,
      refresh_token: (session as any).refreshToken || null,
      access_token_expires_at: (session as any).accessTokenExpiresAt || null,
      granted_scopes: (session as any).grantedScopes || null,
      token_uri: "https://oauth2.googleapis.com/token",
    }
    const syncKey = JSON.stringify(payload)
    if (lastSyncKey.current === syncKey) return

    lastSyncKey.current = syncKey
    console.info("[use-user-sync] syncing auth session", {
      provider,
      hasAccessToken: Boolean(payload.access_token),
      hasRefreshToken: Boolean(payload.refresh_token),
      scopes: payload.granted_scopes || "",
    })

    fetch("/api/auth/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch((err) => {
      console.error("Failed to sync user to backend:", err)
      lastSyncKey.current = "" // allow retry
    })
  }, [session, status])
}
