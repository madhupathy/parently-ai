import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";

export async function POST() {
  const res = await backendFetch("/api/auth/onboarding-complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
