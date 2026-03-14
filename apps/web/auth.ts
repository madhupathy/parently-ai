import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Apple from "next-auth/providers/apple"
import type { Provider } from "next-auth/providers"

const providers: Provider[] = [
  Google({
    clientId: process.env.GOOGLE_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    authorization: {
      params: {
        scope: "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly",
        access_type: "offline",
        prompt: "select_account",
      },
    },
  }),
]

if (process.env.APPLE_CLIENT_ID && process.env.APPLE_CLIENT_SECRET) {
  providers.push(
    Apple({
      clientId: process.env.APPLE_CLIENT_ID,
      clientSecret: process.env.APPLE_CLIENT_SECRET,
    })
  )
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers,
  callbacks: {
    async jwt({ token, account, profile }) {
      const t = token as any
      if (account) {
        t.accessToken = account.access_token
        t.refreshToken = account.refresh_token
        t.provider = account.provider
      }
      return t
    },
    async session({ session, token }) {
      const t = token as any
      ;(session as any).accessToken = t.accessToken
      ;(session as any).provider = t.provider
      ;(session as any).jwt = t
      return session
    },
  },
  pages: {
    signIn: "/",
  },
  secret: process.env.NEXTAUTH_SECRET,
})

/**
 * Helper to get the raw JWT string for Authorization header to the backend.
 * NextAuth v5 stores the JWT in the session cookie; we use the `jwt` callback
 * token which is already a signed HS256 JWT via NEXTAUTH_SECRET.
 */
export { auth as getSession }
