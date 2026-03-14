import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  }

  try {
    const res = await backendFetch("/api/integrations/status")

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Backend unreachable" },
      { status: 502 }
    )
  }
}
