import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export const dynamic = "force-dynamic"

export async function GET() {
  const res = await backendFetch("/api/children");
  const data = await res.json();
  return NextResponse.json(data, {
    status: res.status,
    headers: {
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    },
  });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await backendFetch("/api/children", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
