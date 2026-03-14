import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function GET(req: NextRequest, { params }: { params: { childId: string } }) {
  const res = await backendFetch(`/api/search-profiles/${params.childId}`, { method: "GET" })
  return NextResponse.json(await res.json(), { status: res.status })
}

export async function PUT(req: NextRequest, { params }: { params: { childId: string } }) {
  const body = await req.json()
  const res = await backendFetch(`/api/search-profiles/${params.childId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  })
  return NextResponse.json(await res.json(), { status: res.status })
}

export async function DELETE(req: NextRequest, { params }: { params: { childId: string } }) {
  const res = await backendFetch(`/api/search-profiles/${params.childId}`, { method: "DELETE" })
  return NextResponse.json(await res.json(), { status: res.status })
}
