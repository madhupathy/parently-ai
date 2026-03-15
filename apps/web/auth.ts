import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Apple from "next-auth/providers/apple"
import Credentials from "next-auth/providers/credentials"
import type { Provider } from "next-auth/providers"

const providers: Provider[] = []

if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
  providers.push(
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          scope: "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly",
          access_type: "offline",
          include_granted_scopes: "true",
          prompt: "consent",
        },
      },
    })
  )
}

if (process.env.APPLE_CLIENT_ID && process.env.APPLE_CLIENT_SECRET) {
  providers.push(
    Apple({
      clientId: process.env.APPLE_CLIENT_ID,
      clientSecret: process.env.APPLE_CLIENT_SECRET,
    })
  )
}

if (providers.length === 0) {
  // Keep auth/session endpoint alive during deploy health checks even if OAuth vars are missing.
  providers.push(
    Credentials({
      id: "bootstrap",
      name: "Bootstrap",
      credentials: {},
      async authorize() {
        return null
      },
    })
  )
}

const trustHost =
  process.env.AUTH_TRUST_HOST === "true" || process.env.NODE_ENV === "production"

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers,
  trustHost,
  callbacks: {
    async jwt({ token, account, profile }) {
      const t = token as any
      if (account) {
        t.accessToken = account.access_token || t.accessToken
        // Google may omit refresh_token on subsequent logins; preserve existing value.
        t.refreshToken = account.refresh_token || t.refreshToken
        t.accessTokenExpiresAt = account.expires_at
        t.provider = account.provider
        t.grantedScopes = account.scope || t.grantedScopes
        console.info("[auth][jwt] account scope update", {
          provider: account.provider,
          scope: account.scope || "",
          hasAccessToken: Boolean(account.access_token),
          hasRefreshToken: Boolean(account.refresh_token),
        })
      }
      return t
    },
    async session({ session, token }) {
      const t = token as any
      ;(session as any).accessToken = t.accessToken
      ;(session as any).refreshToken = t.refreshToken
      ;(session as any).accessTokenExpiresAt = t.accessTokenExpiresAt
      ;(session as any).provider = t.provider
      ;(session as any).grantedScopes = t.grantedScopes
      ;(session as any).jwt = t
      console.info("[auth][session] hydrated session", {
        provider: t.provider || "",
        scopes: t.grantedScopes || "",
        hasAccessToken: Boolean(t.accessToken),
        hasRefreshToken: Boolean(t.refreshToken),
      })
      return session
    },
  },
  pages: {
    signIn: "/",
  },
  secret: process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET || "dev-nextauth-secret",
})

/**
 * Helper to get the raw JWT string for Authorization header to the backend.
 * NextAuth v5 stores the JWT in the session cookie; we use the `jwt` callback
 * token which is already a signed HS256 JWT via NEXTAUTH_SECRET.
 */
export { auth as getSession }
