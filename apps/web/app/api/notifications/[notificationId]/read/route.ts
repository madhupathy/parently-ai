import { NextRequest, NextResponse } from "next/server"
import { backendFetch } from "@/lib/api"

export async function POST(req: NextRequest, { params }: { params: { notificationId: string } }) {
  const res = await backendFetch(`/api/notifications/${params.notificationId}/read`, { method: "POST" })
  return NextResponse.json(await res.json(), { status: res.status })
}
