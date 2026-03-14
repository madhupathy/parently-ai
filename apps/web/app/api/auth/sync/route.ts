import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"
import { backendFetch } from "@/lib/api"

export async function POST(req: NextRequest) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  }

  try {
    const body = await req.json()

    const res = await backendFetch("/api/auth/sync", {
      method: "POST",
      body: JSON.stringify(body),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Backend unreachable" },
      { status: 502 }
    )
  }
}
