import { NextResponse } from "next/server"
import { auth } from "@/auth"
import { backendFetch } from "@/lib/api"

export async function POST() {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  }

  try {
    const res = await backendFetch("/api/billing/create-checkout-session", {
      method: "POST",
    })
    const data = await res.json().catch(() => ({}))
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Backend unreachable" },
      { status: 502 }
    )
  }
}
