import { SignJWT } from "jose"
import { auth } from "@/auth"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

/**
 * Mint a short-lived HS256 JWT containing the user's email/name/provider.
 * The Python backend decodes this with the same NEXTAUTH_SECRET.
 */
async function mintBackendJWT(): Promise<string | null> {
  const session = await auth()
  if (!session?.user?.email) return null

  const secret = new TextEncoder().encode(process.env.NEXTAUTH_SECRET || "dev-nextauth-secret")

  const token = await new SignJWT({
    email: session.user.email,
    name: session.user.name || "",
    provider: (session as any).provider || "google",
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("1h")
    .sign(secret)

  return token
}

/**
 * Server-side fetch to the backend with JWT Authorization header.
 */
export async function backendFetch(path: string, options: RequestInit = {}) {
  const jwt = await mintBackendJWT()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  }
  if (jwt) {
    headers["Authorization"] = `Bearer ${jwt}`
  }

  const url = `${BACKEND_URL}${path}`
  return fetch(url, {
    ...options,
    headers,
    cache: "no-store",
  })
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await backendFetch(path, options)

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.detail?.message || body?.detail || `API error ${res.status}`)
  }

  return res.json()
}

export async function apiGet(path: string) {
  return apiFetch(path, { method: "GET" })
}

export async function apiPost(path: string, body?: unknown) {
  return apiFetch(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  })
}
