import fs from "node:fs/promises";
import path from "node:path";
import { compareAuditReports, type ComparisonMode } from "../lib/audit/comparison";
import { createAuditPack } from "../lib/audit/pack";
import { runAuditFromTexts } from "../lib/audit/session";
import { AUDIT_TEMPLATES, getAuditTemplate, templateToYaml } from "../lib/audit/templates";
import { toMarkdownReport } from "../lib/report";
import { redactedJson } from "../lib/security";

type Command = "run" | "compare" | "template";

type CliOptions = {
  command: Command;
  dataset?: string;
  system?: string;
  rightSystem?: string;
  baseline?: string;
  corpus?: string;
  config?: string;
  out?: string;
  packOut?: string;
  leftReport?: string;
  rightReport?: string;
  mode?: ComparisonMode;
  leftLabel?: string;
  rightLabel?: string;
  template?: string;
};

function usage(): string {
  return [
    "Usage:",
    "  falsify-audit run --dataset data.jsonl --system system.jsonl --baseline baseline.jsonl --config claim.yaml --out report.json",
    "  falsify-audit run --dataset data.jsonl --system system.jsonl --corpus corpus.jsonl --config claim.yaml --out report.json --pack-out audit-pack",
    "  falsify-audit compare --dataset data.jsonl --system left.jsonl --right-system right.jsonl --baseline baseline.jsonl --config claim.yaml --out comparison.json",
    "  falsify-audit compare --left-report left.json --right-report right.json --mode system_v1_vs_v2 --out comparison.json",
    "  falsify-audit template --template rag_search --out claim.yaml",
    `Templates: ${AUDIT_TEMPLATES.map((item) => item.id).join(", ")}`,
  ].join("\n");
}

function parseArgs(argv: string[]): CliOptions {
  const [rawCommand, ...rest] = argv;
  if (rawCommand !== "run" && rawCommand !== "compare" && rawCommand !== "template") throw new Error(usage());
  const command = rawCommand;
  const values = new Map<string, string>();

  for (let index = 0; index < rest.length; index += 2) {
    const key = rest[index];
    const value = rest[index + 1];
    if (!key?.startsWith("--") || !value || value.startsWith("--")) throw new Error(usage());
    values.set(key.slice(2), value);
  }

  const options: CliOptions = {
    command,
    dataset: values.get("dataset"),
    system: values.get("system"),
    rightSystem: values.get("right-system"),
    baseline: values.get("baseline"),
    corpus: values.get("corpus"),
    config: values.get("config"),
    out: values.get("out"),
    packOut: values.get("pack-out"),
    leftReport: values.get("left-report"),
    rightReport: values.get("right-report"),
    mode: values.get("mode") as ComparisonMode | undefined,
    leftLabel: values.get("left-label"),
    rightLabel: values.get("right-label"),
    template: values.get("template"),
  };

  if (command === "template") {
    if (!options.template) throw new Error(`Missing --template.\n${usage()}`);
    return options;
  }

  if (command === "run") {
    for (const key of ["dataset", "system", "config", "out"] as const) {
      if (!options[key]) throw new Error(`Missing --${key}.\n${usage()}`);
    }
    if (!options.baseline && !options.corpus) throw new Error(`Missing --baseline or --corpus.\n${usage()}`);
  }

  if (command === "compare") {
    if (!options.out) throw new Error(`Missing --out.\n${usage()}`);
    if (!options.leftReport || !options.rightReport) {
      for (const key of ["dataset", "system", "rightSystem", "config"] as const) {
        if (!options[key]) throw new Error(`Missing --${key === "rightSystem" ? "right-system" : key}.\n${usage()}`);
      }
      if (!options.baseline && !options.corpus) throw new Error(`Missing --baseline or --corpus.\n${usage()}`);
    }
  }

  return options;
}

function extensionOf(filename: string): string {
  const ext = path.extname(filename).toLowerCase();
  return ext === ".jsonl" ? ".jsonl" : ".json";
}

async function readText(filename: string): Promise<string> {
  return fs.readFile(filename, "utf8");
}

async function writeJson(filename: string, value: unknown): Promise<void> {
  await fs.mkdir(path.dirname(path.resolve(filename)), { recursive: true });
  await fs.writeFile(filename, `${JSON.stringify(redactedJson(value), null, 2)}\n`, { mode: 0o600 });
}

async function writePack(dirname: string, pack: ReturnType<typeof createAuditPack>): Promise<void> {
  const root = path.resolve(dirname);
  await Promise.all(pack.files.map(async (file) => {
    const target = path.resolve(root, file.path);
    if (!target.startsWith(root)) throw new Error("Refusing to write outside pack directory.");
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, file.content, { mode: 0o600 });
  }));
}

async function loadAuditTexts(options: CliOptions, systemPath: string) {
  const [datasetText, systemText, baselineText, corpusText, configText] = await Promise.all([
    readText(options.dataset ?? ""),
    readText(systemPath),
    options.baseline ? readText(options.baseline) : Promise.resolve(""),
    options.corpus ? readText(options.corpus) : Promise.resolve(""),
    readText(options.config ?? ""),
  ]);

  return { datasetText, systemText, baselineText, corpusText, configText };
}

async function runCommand(options: CliOptions): Promise<void> {
  const texts = await loadAuditTexts(options, options.system ?? "");
  const audit = runAuditFromTexts({
    datasetText: texts.datasetText,
    datasetName: extensionOf(options.dataset ?? "dataset.json"),
    systemText: texts.systemText,
    systemName: extensionOf(options.system ?? "system.json"),
    baselineText: texts.baselineText || undefined,
    baselineName: extensionOf(options.baseline ?? "baseline.json"),
    corpusText: texts.corpusText || undefined,
    corpusName: extensionOf(options.corpus ?? "corpus.json"),
    configText: texts.configText,
    configName: options.config ?? "claim.yaml",
  });

  await writeJson(options.out ?? "", audit.report);
  if (options.packOut) {
    await writePack(options.packOut, createAuditPack({
      report: redactedJson(audit.report),
      markdown: toMarkdownReport(audit.report),
      configText: texts.configText,
      datasetText: texts.datasetText,
      systemText: texts.systemText,
      baselineText: audit.storedBaselineText,
      corpusText: texts.corpusText || undefined,
    }));
  }
  process.stdout.write(`${audit.report.verdict} ${audit.report.scores.improvement.toFixed(6)} ${options.out}\n`);
}

async function reportFromRunOptions(options: CliOptions, systemPath: string) {
  const texts = await loadAuditTexts(options, systemPath);
  return runAuditFromTexts({
    datasetText: texts.datasetText,
    datasetName: extensionOf(options.dataset ?? "dataset.json"),
    systemText: texts.systemText,
    systemName: extensionOf(systemPath),
    baselineText: texts.baselineText || undefined,
    baselineName: extensionOf(options.baseline ?? "baseline.json"),
    corpusText: texts.corpusText || undefined,
    corpusName: extensionOf(options.corpus ?? "corpus.json"),
    configText: texts.configText,
    configName: options.config ?? "claim.yaml",
  }).report;
}

async function compareCommand(options: CliOptions): Promise<void> {
  const leftReport = options.leftReport
    ? JSON.parse(await readText(options.leftReport))
    : await reportFromRunOptions(options, options.system ?? "");
  const rightReport = options.rightReport
    ? JSON.parse(await readText(options.rightReport))
    : await reportFromRunOptions(options, options.rightSystem ?? "");

  const comparison = compareAuditReports(leftReport, rightReport, {
    mode: options.mode ?? "system_v1_vs_v2",
    leftLabel: options.leftLabel ?? "left",
    rightLabel: options.rightLabel ?? "right",
  });
  await writeJson(options.out ?? "", comparison);
  process.stdout.write(`${comparison.summary} ${options.out}\n`);
}

async function templateCommand(options: CliOptions): Promise<void> {
  const content = templateToYaml(getAuditTemplate(options.template ?? ""));
  if (!options.out) {
    process.stdout.write(content);
    return;
  }
  await fs.mkdir(path.dirname(path.resolve(options.out)), { recursive: true });
  await fs.writeFile(options.out, content, { mode: 0o600 });
  process.stdout.write(`${options.template} ${options.out}\n`);
}

async function main(argv: string[]): Promise<void> {
  const options = parseArgs(argv);
  if (options.command === "template") return templateCommand(options);
  if (options.command === "compare") return compareCommand(options);
  return runCommand(options);
}

main(process.argv.slice(2)).catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : "Audit failed."}\n`);
  process.exit(1);
});
