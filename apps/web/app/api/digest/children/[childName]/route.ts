import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest, { params }: { params: { childName: string } }) {
  const { searchParams } = req.nextUrl
  const qs = searchParams.toString()
  const encodedName = encodeURIComponent(params.childName)
  const res = await backendFetch(
    `/api/digest/children/${encodedName}${qs ? `?${qs}` : ""}`,
    { method: "GET" }
  )
  return NextResponse.json(await res.json(), { status: res.status })
}
