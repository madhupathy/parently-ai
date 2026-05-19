import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const qs = searchParams.toString()
  const res = await backendFetch(`/api/search/digests${qs ? `?${qs}` : ""}`, { method: "GET" })
  return NextResponse.json(await res.json(), { status: res.status })
}
