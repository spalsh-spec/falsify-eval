import { NextRequest, NextResponse } from "next/server";
import { compareAuditReports, type ComparisonMode } from "@/lib/audit/comparison";
import { runAuditFromTexts } from "@/lib/audit/session";
import { validateUploadMeta } from "@/lib/security";

export const runtime = "nodejs";

function optionalFile(form: FormData, name: string): File | null {
  const file = form.get(name);
  if (!(file instanceof File) || file.size === 0) return null;
  validateUploadMeta(file);
  return file;
}

async function requiredFile(form: FormData, name: string): Promise<File> {
  const file = optionalFile(form, name);
  if (!file) throw new Error(`Missing file: ${name}`);
  return file;
}

export async function POST(request: NextRequest) {
  try {
    const form = await request.formData();
    const datasetFile = await requiredFile(form, "dataset");
    const leftFile = await requiredFile(form, "left_system");
    const rightFile = await requiredFile(form, "right_system");
    const baselineFile = optionalFile(form, "baseline");
    const corpusFile = optionalFile(form, "corpus");
    if (!baselineFile && !corpusFile) throw new Error("Missing file: baseline or corpus");
    const configText = String(form.get("config") ?? "");
    if (!configText.trim()) throw new Error("Missing claim config.");

    const [datasetText, leftText, rightText, baselineText, corpusText] = await Promise.all([
      datasetFile.text(),
      leftFile.text(),
      rightFile.text(),
      baselineFile?.text() ?? Promise.resolve(""),
      corpusFile?.text() ?? Promise.resolve(""),
    ]);
    const shared = {
      datasetText,
      datasetName: datasetFile.name,
      baselineText: baselineText || undefined,
      baselineName: baselineFile?.name,
      corpusText: corpusText || undefined,
      corpusName: corpusFile?.name,
      configText,
      configName: "claim config",
    };
    const left = runAuditFromTexts({ ...shared, systemText: leftText, systemName: leftFile.name }).report;
    const right = runAuditFromTexts({ ...shared, systemText: rightText, systemName: rightFile.name }).report;
    const comparison = compareAuditReports(left, right, {
      mode: (String(form.get("mode") ?? "system_v1_vs_v2") as ComparisonMode),
      leftLabel: String(form.get("left_label") ?? "left"),
      rightLabel: String(form.get("right_label") ?? "right"),
    });

    return NextResponse.json({ comparison, left, right }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Comparison failed." }, { status: 400 });
  }
}
