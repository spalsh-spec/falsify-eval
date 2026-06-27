import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { runAuditFromTexts } from "@/lib/audit/session";
import { extensionOf, validateUploadMeta } from "@/lib/security";
import { rateLimit } from "@/lib/rate-limit";
import { latestJob, markdownFor, privateRawPath, saveJob, statusFromVerdict, storeRaw } from "@/lib/storage";

export const runtime = "nodejs";

function clientKey(request: NextRequest): string {
  return request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
}

async function requiredFile(form: FormData, name: string): Promise<File> {
  const file = form.get(name);
  if (!(file instanceof File)) throw new Error(`Missing file: ${name}`);
  validateUploadMeta(file);
  return file;
}

function optionalFile(form: FormData, name: string): File | null {
  const file = form.get(name);
  if (!(file instanceof File) || file.size === 0) return null;
  validateUploadMeta(file);
  return file;
}

export async function GET() {
  const job = await latestJob();
  return NextResponse.json({ job });
}

export async function POST(request: NextRequest) {
  const limited = rateLimit(`audit:${clientKey(request)}`, 12, 60_000);
  if (!limited.allowed) {
    return NextResponse.json({ error: "Rate limit exceeded.", reset_at: limited.resetAt }, { status: 429 });
  }

  try {
    const form = await request.formData();
    const datasetFile = await requiredFile(form, "dataset");
    const systemFile = await requiredFile(form, "system");
    const corpusFile = optionalFile(form, "corpus");
    const baselineFile = optionalFile(form, "baseline");
    if (!baselineFile && !corpusFile) throw new Error("Missing file: baseline or corpus");
    const configText = String(form.get("config") ?? "");
    if (!configText.trim()) throw new Error("Missing claim config.");

    const [datasetText, systemText, baselineUploadText, corpusText] = await Promise.all([
      datasetFile.text(),
      systemFile.text(),
      baselineFile?.text() ?? Promise.resolve(""),
      corpusFile?.text() ?? Promise.resolve(""),
    ]);

    const jobId = randomUUID();
    const createdAt = new Date().toISOString();
    const audit = runAuditFromTexts({
      jobId,
      createdAt,
      datasetText,
      datasetName: datasetFile.name,
      systemText,
      systemName: systemFile.name,
      baselineText: baselineUploadText || undefined,
      baselineName: baselineFile?.name,
      corpusText: corpusText || undefined,
      corpusName: corpusFile?.name,
      configText,
      configName: "claim config",
    });
    const report = audit.report;

    const rawPaths = {
      dataset: privateRawPath(jobId, "dataset", extensionOf(datasetFile.name)),
      system: privateRawPath(jobId, "system", extensionOf(systemFile.name)),
      baseline: privateRawPath(jobId, "baseline", extensionOf(baselineFile?.name ?? "baseline.json")),
      corpus: corpusFile ? privateRawPath(jobId, "corpus", extensionOf(corpusFile.name)) : undefined,
      config: privateRawPath(jobId, "config", ".json"),
    };

    const writes = [
      storeRaw(rawPaths.dataset, datasetText),
      storeRaw(rawPaths.system, systemText),
      storeRaw(rawPaths.baseline, audit.storedBaselineText),
      storeRaw(rawPaths.config, configText),
    ];
    if (rawPaths.corpus) writes.push(storeRaw(rawPaths.corpus, corpusText));
    await Promise.all(writes);

    const markdown = markdownFor(report);
    await saveJob({
      id: jobId,
      status: statusFromVerdict(report.verdict),
      report,
      markdown,
      rawPaths,
      createdAt,
    });

    return NextResponse.json({ job: { id: jobId, status: statusFromVerdict(report.verdict), report, markdown, createdAt } }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Audit failed." }, { status: 400 });
  }
}
