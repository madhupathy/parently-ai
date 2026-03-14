import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest) {
  const res = await backendFetch("/api/notifications/unread-count", { method: "GET" })
  return NextResponse.json(await res.json(), { status: res.status })
}
