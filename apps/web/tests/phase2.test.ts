import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { describe, expect, it } from "vitest";
import { compareAuditReports } from "../src/lib/audit/comparison";
import { createAuditPack } from "../src/lib/audit/pack";
import { runAuditFromTexts } from "../src/lib/audit/session";
import { AUDIT_TEMPLATES, getAuditTemplate, templateToYaml } from "../src/lib/audit/templates";

const execFileAsync = promisify(execFile);

const datasetText = [
  JSON.stringify({ id: "q1", query: "machine safety isolation", expected_answer: "lockout", relevant_ids: ["doc-a"] }),
  JSON.stringify({ id: "q2", query: "invoice ledger", expected_answer: "accounting", relevant_ids: ["doc-b"] }),
].join("\n");

const leftSystemText = JSON.stringify([
  { id: "q1", retrieved_ids: ["doc-x", "doc-a"] },
  { id: "q2", retrieved_ids: ["doc-b"] },
]);

const rightSystemText = JSON.stringify([
  { id: "q1", retrieved_ids: ["doc-a"] },
  { id: "q2", retrieved_ids: ["doc-b"] },
]);

const baselineText = JSON.stringify([
  { id: "q1", retrieved_ids: ["doc-x"] },
  { id: "q2", retrieved_ids: ["doc-y"] },
]);

const configText = templateToYaml(getAuditTemplate("rag_search"));

function audit(systemText: string) {
  return runAuditFromTexts({
    datasetText,
    datasetName: "dataset.jsonl",
    systemText,
    systemName: "system.json",
    baselineText,
    baselineName: "baseline.json",
    configText,
    configName: "claim.yaml",
    jobId: `job-${systemText.length}`,
    createdAt: "2026-06-27T00:00:00.000Z",
  }).report;
}

describe("phase 2 shared features", () => {
  it("compares two audit runs", () => {
    const comparison = compareAuditReports(audit(leftSystemText), audit(rightSystemText), {
      mode: "system_v1_vs_v2",
      leftLabel: "v1",
      rightLabel: "v2",
    });
    expect(comparison.delta.improvement).toBeGreaterThan(0);
    expect(comparison.summary).toContain("v2");
  });

  it("ships the requested local templates", () => {
    expect(AUDIT_TEMPLATES.map((item) => item.id)).toEqual([
      "rag_search",
      "support_docs_qa",
      "sanskrit_retrieval",
      "academic_retrieval",
    ]);
    expect(templateToYaml(getAuditTemplate("sanskrit_retrieval"))).toContain("Sanskrit retriever");
  });

  it("creates an exportable audit pack with required files", () => {
    const report = audit(rightSystemText);
    const pack = createAuditPack({
      report,
      markdown: "# report\n",
      configText,
      datasetText,
      systemText: rightSystemText,
      baselineText,
    });
    expect(pack.files.map((file) => file.path)).toEqual(expect.arrayContaining([
      "report.md",
      "report.json",
      "inputs.lock.json",
      "config.yaml",
      "hashes.json",
      "inputs/dataset.json",
      "inputs/system.json",
      "inputs/baseline.json",
    ]));
    expect(pack.files.find((file) => file.path === "inputs.lock.json")?.content).toContain("dataset_hash");
  });

  it("keeps CLI and shared runner output aligned", async () => {
    const dir = await fs.mkdtemp(path.join(os.tmpdir(), "falsify-phase2-"));
    try {
      const dataset = path.join(dir, "dataset.jsonl");
      const system = path.join(dir, "system.json");
      const baseline = path.join(dir, "baseline.json");
      const config = path.join(dir, "claim.yaml");
      const out = path.join(dir, "report.json");
      await Promise.all([
        fs.writeFile(dataset, datasetText),
        fs.writeFile(system, rightSystemText),
        fs.writeFile(baseline, baselineText),
        fs.writeFile(config, configText),
      ]);
      const repoRoot = path.resolve(process.cwd(), "../..");
      await execFileAsync("npm", ["run", "build:cli", "--workspace", "apps/web"], { cwd: repoRoot });
      await execFileAsync("node", ["apps/web/dist-cli/falsify-audit.mjs", "run", "--dataset", dataset, "--system", system, "--baseline", baseline, "--config", config, "--out", out], { cwd: repoRoot });
      const cliReport = JSON.parse(await fs.readFile(out, "utf8"));
      expect(cliReport.scores.improvement).toBe(audit(rightSystemText).scores.improvement);
    } finally {
      await fs.rm(dir, { recursive: true, force: true });
    }
  }, 20_000);
});
