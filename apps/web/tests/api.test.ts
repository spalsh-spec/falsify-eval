import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { POST } from "../src/app/api/audits/route";
import { POST as COMPARE } from "../src/app/api/compare/route";

let storageDir = "";

function jsonFile(name: string, value: unknown): File {
  return new File([JSON.stringify(value)], name, { type: "application/json" });
}

beforeEach(async () => {
  storageDir = await fs.mkdtemp(path.join(os.tmpdir(), "falsify-audit-test-"));
  process.env.AUDIT_STORAGE_DIR = storageDir;
});

afterEach(async () => {
  delete process.env.AUDIT_STORAGE_DIR;
  await fs.rm(storageDir, { recursive: true, force: true });
});

describe("audit API", () => {
  it("accepts multipart uploads and builds BM25 when corpus is provided", async () => {
    const dataset = [
      { id: "q1", query: "machine safety isolation", expected_answer: "lockout", relevant_ids: ["doc-a"] },
      { id: "q2", query: "invoice ledger", expected_answer: "accounting", relevant_ids: ["doc-b"] },
    ];
    const system = [
      { id: "q1", answer: "lockout", retrieved_ids: ["doc-a"] },
      { id: "q2", answer: "accounting", retrieved_ids: ["doc-b"] },
    ];
    const corpus = [
      { id: "doc-a", text: "machine safety isolation lockout tagout" },
      { id: "doc-b", text: "invoice ledger accounting payment" },
    ];
    const form = new FormData();
    form.set("dataset", jsonFile("dataset.json", dataset));
    form.set("system", jsonFile("system.json", system));
    form.set("corpus", jsonFile("corpus.json", corpus));
    form.set("config", JSON.stringify({
      claim: "System beats BM25",
      primary_metric: "ndcg@1",
      minimum_effect_size: 0.01,
      alpha: 0.05,
      seed: 7,
      system_name: "System",
      baseline_name: "BM25",
      checks: [],
    }));

    const response = await POST(new NextRequest("http://localhost/api/audits", { method: "POST", body: form }));
    const payload = await response.json();

    expect(response.status).toBe(201);
    expect(payload.job.report.dataset_quality.corpus_document_count).toBe(2);
    expect(payload.job.report.checks.find((item: { id: string }) => item.id === "lexical_baseline")?.status).toBe("pass");
    expect(payload.job.report.reproducibility.corpus_hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it("accepts multipart uploads with baseline and no corpus", async () => {
    const form = new FormData();
    form.set("dataset", jsonFile("dataset.json", [{ id: "q1", query: "machine safety", relevant_ids: ["doc-a"] }]));
    form.set("system", jsonFile("system.json", [{ id: "q1", retrieved_ids: ["doc-a"] }]));
    form.set("baseline", jsonFile("baseline.json", [{ id: "q1", retrieved_ids: ["doc-b"] }]));
    form.set("config", JSON.stringify({
      claim: "System beats uploaded baseline",
      primary_metric: "ndcg@1",
      minimum_effect_size: 0.01,
      alpha: 0.05,
      seed: 7,
      system_name: "System",
      baseline_name: "Uploaded baseline",
      checks: [],
    }));

    const response = await POST(new NextRequest("http://localhost/api/audits", { method: "POST", body: form }));
    const payload = await response.json();

    expect(response.status).toBe(201);
    expect(payload.job.report.checks.find((item: { id: string }) => item.id === "lexical_baseline")?.status).toBe("not_run");
    expect(payload.job.report.scores.improvement).toBe(1);
  });

  it("compares two uploaded system runs", async () => {
    const form = new FormData();
    form.set("dataset", jsonFile("dataset.json", [{ id: "q1", query: "machine safety", relevant_ids: ["doc-a"] }]));
    form.set("left_system", jsonFile("left.json", [{ id: "q1", retrieved_ids: ["doc-b", "doc-a"] }]));
    form.set("right_system", jsonFile("right.json", [{ id: "q1", retrieved_ids: ["doc-a"] }]));
    form.set("baseline", jsonFile("baseline.json", [{ id: "q1", retrieved_ids: ["doc-b"] }]));
    form.set("config", JSON.stringify({
      claim: "Right beats left",
      primary_metric: "ndcg@1",
      minimum_effect_size: 0.01,
      alpha: 0.05,
      seed: 7,
      system_name: "System",
      baseline_name: "Uploaded baseline",
      checks: [],
    }));

    const response = await COMPARE(new NextRequest("http://localhost/api/compare", { method: "POST", body: form }));
    const payload = await response.json();

    expect(response.status).toBe(201);
    expect(payload.comparison.delta.improvement).toBeGreaterThan(0);
  });

  it("rejects audits without baseline or corpus", async () => {
    const form = new FormData();
    form.set("dataset", jsonFile("dataset.json", [{ id: "q1", query: "q", relevant_ids: ["d"] }]));
    form.set("system", jsonFile("system.json", [{ id: "q1", retrieved_ids: ["d"] }]));
    form.set("config", JSON.stringify({ claim: "x", primary_metric: "ndcg@1", system_name: "s", baseline_name: "b" }));

    const response = await POST(new NextRequest("http://localhost/api/audits", { method: "POST", body: form }));
    const payload = await response.json();

    expect(response.status).toBe(400);
    expect(payload.error).toMatch(/baseline or corpus/);
  });
});
