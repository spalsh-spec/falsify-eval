import { describe, expect, it } from "vitest";
import { parseClaimConfig, parseCorpus, parseDataset, parseJsonOrJsonl, parseJsonOrYaml, parseOutputs, redactedJson, redactSecrets, validateUploadMeta } from "../src/lib/security";

describe("security validation", () => {
  it("rejects malicious filenames", () => {
    expect(() => validateUploadMeta({ name: "../secret.json", size: 10, type: "application/json" })).toThrow(/Unsafe/);
  });

  it("rejects oversized files", () => {
    expect(() => validateUploadMeta({ name: "data.json", size: 11, type: "application/json" }, 10)).toThrow(/max size/);
  });

  it("rejects unsupported extensions", () => {
    expect(() => validateUploadMeta({ name: "data.js", size: 10, type: "text/plain" })).toThrow(/Only/);
  });

  it("rejects bad JSON", () => {
    expect(() => parseJsonOrJsonl("{bad", "data.json")).toThrow(/Invalid JSON/);
  });

  it("parses YAML claim configs through the safe config schema", () => {
    const parsed = parseClaimConfig(parseJsonOrYaml(`
claim: System A beats BM25
primary_metric: ndcg@3
minimum_effect_size: 0.03
alpha: 0.05
seed: 42
system_name: System A
baseline_name: BM25
checks:
  - bootstrap_ci
  - shuffled_labels
`, "claim.yaml"));

    expect(parsed.primary_metric).toBe("ndcg@3");
    expect(parsed.checks).toContain("shuffled_labels");
  });

  it("normalizes standard RAG JSONL dataset rows", () => {
    const parsed = parseDataset(parseJsonOrJsonl(
      "{\"question\":\"What is BM25?\",\"ground_truth\":\"A lexical ranker\",\"contexts\":[\"BM25 passage\"]}\n",
      "rag.jsonl",
    ));

    expect(parsed[0]).toMatchObject({
      id: "q1",
      query: "What is BM25?",
      expected_answer: "A lexical ranker",
      relevant_ids: ["q1-ctx1"],
    });
  });

  it("normalizes output and corpus aliases", () => {
    const outputs = parseOutputs([{ query_id: "q1", response: "answer", retrieved_doc_ids: ["doc1"] }]);
    const corpus = parseCorpus([{ doc_id: "doc1", page_content: "BM25 passage" }]);

    expect(outputs[0]).toMatchObject({ id: "q1", answer: "answer", retrieved_ids: ["doc1"] });
    expect(corpus[0]).toMatchObject({ id: "doc1", text: "BM25 passage" });
  });

  it("rejects invalid YAML claim configs", () => {
    expect(() => parseClaimConfig(parseJsonOrYaml("claim: nope\nprimary_metric: !!js/function bad", "claim.yaml"))).toThrow();
  });

  it("redacts obvious secrets", () => {
    const redacted = redactSecrets("Email me at test@example.com with Bearer abcdefghijklmnopqrstuvwxyz123456 or +61 400 000 000");
    expect(redacted).not.toContain("test@example.com");
    expect(redacted).not.toContain("abcdefghijklmnopqrstuvwxyz");
    expect(redacted).not.toContain("+61 400");
  });

  it("redacts JSON without corrupting numeric evidence", () => {
    const value = redactedJson({
      job_id: "b3d80bd9-0abd-4536-9497-e03109052947",
      message: "test@example.com",
      evidence: { random_score: 0.123456, n: 35 },
    });
    expect(value).toEqual({
      job_id: "b3d80bd9-0abd-4536-9497-e03109052947",
      message: "[redacted-email]",
      evidence: { random_score: 0.123456, n: 35 },
    });
  });
});
