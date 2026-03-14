import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest, { params }: { params: { digestId: string } }) {
  const res = await backendFetch(`/api/digest/${params.digestId}`, { method: "GET" })
  return NextResponse.json(await res.json(), { status: res.status })
}
