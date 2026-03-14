import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export async function GET() {
  const res = await backendFetch("/api/preferences");
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function PUT(req: NextRequest) {
  const body = await req.json();
  const res = await backendFetch("/api/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
