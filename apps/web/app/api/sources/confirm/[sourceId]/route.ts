import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function POST(
  _req: NextRequest,
  { params }: { params: { sourceId: string } }
) {
  const res = await backendFetch(`/api/sources/${params.sourceId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
