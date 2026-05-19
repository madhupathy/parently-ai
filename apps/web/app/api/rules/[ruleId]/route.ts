import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function DELETE(_req: NextRequest, { params }: { params: { ruleId: string } }) {
  const res = await backendFetch(`/api/rules/${params.ruleId}`, { method: "DELETE" })
  return NextResponse.json(await res.json(), { status: res.status })
}
