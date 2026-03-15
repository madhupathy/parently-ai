import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export async function GET() {
  const res = await backendFetch("/api/auth/me");
  const raw = await res.text();
  try {
    const data = JSON.parse(raw);
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      {
        ok: false,
        error: "backend_non_json_response",
        message: raw?.slice(0, 500) || "Backend returned non-JSON payload",
      },
      { status: res.status || 502 }
    );
  }
}
