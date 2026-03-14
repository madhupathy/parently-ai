import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function POST(req: NextRequest) {
  const res = await backendFetch("/api/notifications/mark-all-read", { method: "POST" })
  return NextResponse.json(await res.json(), { status: res.status })
}
