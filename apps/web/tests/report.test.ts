import { describe, expect, it } from "vitest";
import { toJsonReport, toMarkdownReport } from "../src/lib/report";
import type { AuditReport } from "../src/lib/audit/types";

const report: AuditReport = {
  job_id: "job",
  verdict: "WARN",
  claim: "Claim with test@example.com",
  summary: "Bearer abcdefghijklmnopqrstuvwxyz123456",
  scores: { primary_metric: "ndcg@10", system: 0.8, baseline: 0.5, improvement: 0.3 },
  checks: [{ id: "c", status: "pass", severity: "low", message: "ok", evidence: {} }],
  dataset_quality: {
    row_count: 2,
    corpus_document_count: 2,
    relevant_id_count: 2,
    covered_relevant_id_count: 2,
    coverage_ratio: 1,
    duplicate_query_count: 0,
    duplicate_id_count: 0,
    missing_relevant_ids_count: 0,
    empty_query_count: 0,
    issues: [],
  },
  reproducibility: {
    dataset_hash: "d",
    system_output_hash: "s",
    baseline_output_hash: "b",
    config_hash: "c",
    seed: 1,
    system_version: "v",
    dataset_version: "v",
    timestamp_recorded: "2026-06-26T00:00:00.000Z",
    audit_engine_version: "0.1.0",
  },
  created_at: "2026-06-26T00:00:00.000Z",
};

describe("report generation", () => {
  it("redacts JSON reports", () => {
    expect(JSON.stringify(toJsonReport(report))).not.toContain("test@example.com");
  });

  it("renders markdown reports", () => {
    const markdown = toMarkdownReport(report);
    expect(markdown).toContain("# falsify-eval audit report");
    expect(markdown).toContain("## Dataset quality");
    expect(markdown).toContain("| Check | Status | Severity | Message |");
    expect(markdown).not.toContain("abcdefghijklmnopqrstuvwxyz");
  });
});
