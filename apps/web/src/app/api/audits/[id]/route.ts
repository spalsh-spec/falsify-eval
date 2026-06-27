import { NextRequest, NextResponse } from "next/server";
import { rateLimit } from "@/lib/rate-limit";
import { deleteJob, getJob } from "@/lib/storage";

export const runtime = "nodejs";

type Context = { params: Promise<{ id: string }> };

function clientKey(request: NextRequest): string {
  return request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
}

export async function GET(_request: NextRequest, context: Context) {
  const { id } = await context.params;
  const job = await getJob(id);
  if (!job) return NextResponse.json({ error: "Job not found." }, { status: 404 });
  return NextResponse.json({ job });
}

export async function DELETE(request: NextRequest, context: Context) {
  const limited = rateLimit(`delete:${clientKey(request)}`, 20, 60_000);
  if (!limited.allowed) return NextResponse.json({ error: "Rate limit exceeded." }, { status: 429 });
  const { id } = await context.params;
  const deleted = await deleteJob(id);
  if (!deleted) return NextResponse.json({ error: "Job not found." }, { status: 404 });
  return NextResponse.json({ ok: true });
}
