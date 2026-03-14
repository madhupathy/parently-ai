import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export async function PUT(
  req: NextRequest,
  { params }: { params: { childId: string } }
) {
  const body = await req.json();
  const res = await backendFetch(`/api/children/${params.childId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { childId: string } }
) {
  const res = await backendFetch(`/api/children/${params.childId}`, {
    method: "DELETE",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
