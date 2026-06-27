import { createHash, randomUUID } from "node:crypto";
import { buildBm25Baseline } from "./bm25";
import { runAudit } from "./engine";
import { datasetQualityReport } from "./quality";
import type { AuditReport } from "./types";
import { parseClaimConfig, parseCorpus, parseDataset, parseJsonOrJsonl, parseJsonOrYaml, parseOutputs } from "@/lib/security";

export type AuditRunTexts = {
  datasetText: string;
  datasetName: string;
  systemText: string;
  systemName: string;
  baselineText?: string;
  baselineName?: string;
  corpusText?: string;
  corpusName?: string;
  configText: string;
  configName: string;
  jobId?: string;
  createdAt?: string;
};

export type AuditRunResult = {
  report: AuditReport;
  generatedBaselineText: string;
  storedBaselineText: string;
  corpusText?: string;
};

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

export function runAuditFromTexts(input: AuditRunTexts): AuditRunResult {
  if (!input.baselineText && !input.corpusText) throw new Error("Missing baseline or corpus.");

  const dataset = parseDataset(parseJsonOrJsonl(input.datasetText, input.datasetName));
  const systemOutputs = parseOutputs(parseJsonOrJsonl(input.systemText, input.systemName));
  const corpus = input.corpusText ? parseCorpus(parseJsonOrJsonl(input.corpusText, input.corpusName ?? "corpus.json")) : undefined;
  const baselineOutputs = corpus
    ? buildBm25Baseline(dataset, corpus)
    : parseOutputs(parseJsonOrJsonl(input.baselineText ?? "", input.baselineName ?? "baseline.json"));
  const generatedBaselineText = JSON.stringify(baselineOutputs, null, 2);
  const storedBaselineText = corpus ? generatedBaselineText : input.baselineText ?? "";
  const config = parseClaimConfig(parseJsonOrYaml(input.configText, input.configName));
  const quality = datasetQualityReport(dataset, corpus);

  const report = runAudit({
    jobId: input.jobId ?? randomUUID(),
    dataset,
    systemOutputs,
    baselineOutputs,
    corpus,
    datasetQuality: quality,
    config,
    hashes: {
      dataset_hash: sha256(input.datasetText),
      system_output_hash: sha256(input.systemText),
      baseline_output_hash: sha256(storedBaselineText),
      corpus_hash: input.corpusText ? sha256(input.corpusText) : undefined,
      config_hash: sha256(input.configText),
    },
    createdAt: input.createdAt ?? new Date().toISOString(),
  });

  return {
    report,
    generatedBaselineText,
    storedBaselineText,
    corpusText: input.corpusText,
  };
}
