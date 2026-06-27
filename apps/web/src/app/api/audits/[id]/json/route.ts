import { NextResponse } from "next/server";
import { getJob } from "@/lib/storage";

export const runtime = "nodejs";

type Context = { params: Promise<{ id: string }> };

export async function GET(_request: Request, context: Context) {
  const { id } = await context.params;
  const job = await getJob(id);
  if (!job) return NextResponse.json({ error: "Job not found." }, { status: 404 });
  return new NextResponse(JSON.stringify(job.report, null, 2), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "content-disposition": `attachment; filename="audit-${id}.json"`,
    },
  });
}
