import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"
import { backendFetch } from "@/lib/api"

export async function POST(req: NextRequest) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 })
  }

  try {
    const refresh = req.nextUrl.searchParams.get("refresh") === "true"
    const path = refresh ? "/api/digest/run?refresh=true" : "/api/digest/run"

    const res = await backendFetch(path, {
      method: "POST",
    })

    const body = await res.json()
    return NextResponse.json(body, { status: res.status })
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Backend unreachable" },
      { status: 502 }
    )
  }
}
