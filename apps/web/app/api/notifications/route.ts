import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const params = searchParams.toString()
  const res = await backendFetch(`/api/notifications${params ? `?${params}` : ""}`, { method: "GET" })
  return NextResponse.json(await res.json(), { status: res.status })
}
