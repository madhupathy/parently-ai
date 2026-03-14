import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export async function GET(
  req: NextRequest,
  { params }: { params: { jobId: string } }
) {
  const res = await backendFetch(`/api/sources/discover/${params.jobId}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
