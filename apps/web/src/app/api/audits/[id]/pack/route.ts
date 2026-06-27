import { NextRequest, NextResponse } from "next/server";
import { createAuditPack } from "@/lib/audit/pack";
import { getJob, readStoredRaw } from "@/lib/storage";

export const runtime = "nodejs";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) return NextResponse.json({ error: "Audit not found." }, { status: 404 });
  const raw = await readStoredRaw(job);
  const pack = createAuditPack({
    report: job.report,
    markdown: job.markdown,
    configText: raw.configText,
    datasetText: raw.datasetText,
    systemText: raw.systemText,
    baselineText: raw.baselineText,
    corpusText: raw.corpusText,
  });
  return NextResponse.json(pack, {
    headers: {
      "content-disposition": `attachment; filename="${pack.name}.json"`,
    },
  });
}
