import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export async function GET(
  req: NextRequest,
  { params }: { params: { childId: string } }
) {
  const res = await backendFetch(`/api/sources/${params.childId}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
