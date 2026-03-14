import { auth } from "@/auth"

export default auth((req) => {
  const isLoggedIn = !!req.auth
  const isOnDashboard = req.nextUrl.pathname.startsWith("/dashboard")
  const isOnSettings = req.nextUrl.pathname.startsWith("/settings")
  const isOnDigest = req.nextUrl.pathname.startsWith("/digest")
  const isOnOnboarding = req.nextUrl.pathname.startsWith("/onboarding")
  const isProtected = isOnDashboard || isOnSettings || isOnDigest || isOnOnboarding

  if (isProtected && !isLoggedIn) {
    return Response.redirect(new URL("/", req.nextUrl))
  }

  if (req.nextUrl.pathname === "/" && isLoggedIn) {
    return Response.redirect(new URL("/dashboard", req.nextUrl))
  }
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|icon|apple-icon).*)"],
}
