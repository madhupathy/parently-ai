import { NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export const dynamic = "force-dynamic"

export async function GET() {
  const res = await backendFetch("/api/setup/status", { method: "GET" })
  const data = await res.json()
  return NextResponse.json(data, {
    status: res.status,
    headers: {
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    },
  })
}
