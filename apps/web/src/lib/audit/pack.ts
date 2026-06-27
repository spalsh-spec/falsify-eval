import type { AuditReport } from "./types";

export type AuditPackFile = {
  path: string;
  content: string;
};

export type AuditPack = {
  name: string;
  created_at: string;
  files: AuditPackFile[];
};

export type AuditPackInput = {
  report: AuditReport;
  markdown: string;
  configText: string;
  datasetText: string;
  systemText: string;
  baselineText: string;
  corpusText?: string;
};

export function createInputsLock(input: AuditPackInput): Record<string, unknown> {
  return {
    job_id: input.report.job_id,
    created_at: input.report.created_at,
    primary_metric: input.report.scores.primary_metric,
    hashes: input.report.reproducibility,
    inputs: {
      dataset: "inputs/dataset.json",
      system: "inputs/system.json",
      baseline: "inputs/baseline.json",
      corpus: input.corpusText ? "inputs/corpus.json" : null,
      config: "config.yaml",
    },
  };
}

export function createAuditPack(input: AuditPackInput): AuditPack {
  const files: AuditPackFile[] = [
    { path: "report.md", content: input.markdown },
    { path: "report.json", content: `${JSON.stringify(input.report, null, 2)}\n` },
    { path: "inputs.lock.json", content: `${JSON.stringify(createInputsLock(input), null, 2)}\n` },
    { path: "config.yaml", content: input.configText },
    { path: "hashes.json", content: `${JSON.stringify(input.report.reproducibility, null, 2)}\n` },
    { path: "inputs/dataset.json", content: input.datasetText },
    { path: "inputs/system.json", content: input.systemText },
    { path: "inputs/baseline.json", content: input.baselineText },
  ];
  if (input.corpusText) files.push({ path: "inputs/corpus.json", content: input.corpusText });

  return {
    name: `falsify-audit-pack-${input.report.job_id}`,
    created_at: new Date().toISOString(),
    files,
  };
}
