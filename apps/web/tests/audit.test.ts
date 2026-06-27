import { describe, expect, it } from "vitest";
import { buildBm25Baseline, bm25Score } from "../src/lib/audit/bm25";
import { bootstrapCi, duplicateQueryCheck, leakageCheck, runAudit } from "../src/lib/audit/engine";
import { metricScore } from "../src/lib/audit/metrics";
import { datasetQualityReport } from "../src/lib/audit/quality";
import type { AuditInput, DatasetRow, OutputRow } from "../src/lib/audit/types";

function rows(n = 40): DatasetRow[] {
  return Array.from({ length: n }, (_, index) => ({
    id: `q${index}`,
    query: `question ${index}`,
    expected_answer: `answer ${index}`,
    relevant_ids: [`doc${index}`],
    difficulty: index % 2 === 0 ? "easy" : "hard",
    source: index % 2 === 0 ? "a" : "b",
  }));
}

function outputs(dataset: DatasetRow[], good: boolean): OutputRow[] {
  return dataset.map((row, index) => ({
    id: row.id,
    answer: good ? row.expected_answer : "wrong",
    retrieved_ids: good ? [row.relevant_ids?.[0] ?? "", `junk${index}`] : [`junk${index}`, row.relevant_ids?.[0] ?? ""],
  }));
}

function input(systemGood = true): AuditInput {
  const dataset = rows();
  return {
    jobId: "job-1",
    dataset,
    systemOutputs: outputs(dataset, systemGood),
    baselineOutputs: outputs(dataset, false),
    config: {
      claim: "System A beats BM25",
      primary_metric: "ndcg@1",
      minimum_effect_size: 0.03,
      alpha: 0.05,
      seed: 42,
      system_name: "System A",
      baseline_name: "BM25",
      system_version: "test",
      dataset_version: "test",
      checks: [],
    },
    hashes: {
      dataset_hash: "d",
      system_output_hash: "s",
      baseline_output_hash: "b",
      config_hash: "c",
    },
    createdAt: "2026-06-26T00:00:00.000Z",
  };
}

describe("audit metrics", () => {
  it("calculates recall, precision, ndcg, and exact match", () => {
    const row = { id: "q1", query: "q", expected_answer: "The Answer", relevant_ids: ["a", "b"] };
    const output = { id: "q1", answer: "the answer", retrieved_ids: ["a", "x", "b"] };
    expect(metricScore(row, output, "exact_match")).toBe(1);
    expect(metricScore(row, output, "recall@3")).toBe(1);
    expect(metricScore(row, output, "precision@2")).toBe(0.5);
    expect(metricScore(row, output, "ndcg@3")).toBeGreaterThan(0.8);
  });

  it("bootstrap CI is deterministic with a seed", () => {
    expect(bootstrapCi([1, 0, 1, 1, 0], 7)).toEqual(bootstrapCi([1, 0, 1, 1, 0], 7));
  });

  it("runs shuffled label null test and returns a non-pass when labels do not matter", () => {
    const audit = input(false);
    const report = runAudit(audit);
    const shuffled = report.checks.find((item) => item.id === "shuffled_labels");
    expect(shuffled?.status).toBe("fail");
  });

  it("detects duplicate queries", () => {
    const check = duplicateQueryCheck([{ id: "1", query: "same" }, { id: "2", query: "same" }]);
    expect(check.status).toBe("warn");
  });

  it("detects leakage by dataset ID overlap", () => {
    const check = leakageCheck([{ id: "q1", query: "x", relevant_ids: ["d1"] }], [{ id: "q1", retrieved_ids: ["q1"] }]);
    expect(check.status).toBe("fail");
  });

  it("fails verdict when improvement is noise", () => {
    const report = runAudit(input(false));
    expect(report.verdict).toBe("FAIL");
  });

  it("emits the required report schema shape", () => {
    const report = runAudit(input(true));
    expect(report).toMatchObject({
      job_id: "job-1",
      claim: "System A beats BM25",
      scores: { primary_metric: "ndcg@1" },
      reproducibility: {
        dataset_hash: "d",
        system_output_hash: "s",
        baseline_output_hash: "b",
        config_hash: "c",
        seed: 42,
        audit_engine_version: "0.1.0",
      },
    });
    expect(["PASS", "WARN", "FAIL"]).toContain(report.verdict);
    expect(report.checks.length).toBeGreaterThan(5);
    expect(report.dataset_quality.row_count).toBe(40);
  });

  it("ranks corpus documents with BM25", () => {
    const corpus = [
      { id: "doc-a", text: "electrical safety lockout tagout machine isolation" },
      { id: "doc-b", text: "payroll invoice accounting ledger" },
    ];
    const baseline = buildBm25Baseline([{ id: "q1", query: "machine safety isolation", relevant_ids: ["doc-a"] }], corpus, 2);
    expect(baseline[0].retrieved_ids?.[0]).toBe("doc-a");
    expect(bm25Score("machine safety", corpus[0].text, corpus.map((doc) => doc.text))).toBeGreaterThan(0);
  });

  it("reports dataset quality and corpus coverage", () => {
    const quality = datasetQualityReport([
      { id: "q1", query: "same", relevant_ids: ["doc-a"] },
      { id: "q2", query: "same", relevant_ids: ["missing"] },
      { id: "q2", query: "other", relevant_ids: [] },
    ], [{ id: "doc-a", text: "text" }]);

    expect(quality.duplicate_query_count).toBe(2);
    expect(quality.duplicate_id_count).toBe(2);
    expect(quality.coverage_ratio).toBe(0.5);
    expect(quality.issues.map((item) => item.id)).toContain("missing_relevant_ids");
  });
});
