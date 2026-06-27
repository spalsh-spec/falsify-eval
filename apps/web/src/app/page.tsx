"use client";

import { useEffect, useMemo, useState } from "react";
import { AUDIT_TEMPLATES, templateToYaml } from "@/lib/audit/templates";
import type { ComparisonMode, ComparisonReport } from "@/lib/audit/comparison";
import type { AuditReport } from "@/lib/audit/types";

type JobView = {
  id: string;
  status: "passed" | "warned" | "failed";
  report: AuditReport;
  markdown: string;
  createdAt: string;
};

type UiState = "idle" | "loading" | "running" | "success" | "error";

const sampleConfigText = `claim: System A beats BM25 on this RAG benchmark
primary_metric: ndcg@3
minimum_effect_size: 0.03
alpha: 0.05
seed: 42
system_name: System A
baseline_name: BM25
system_version: demo
dataset_version: demo
checks:
  - bootstrap_ci
  - shuffled_labels
  - random_baseline
  - duplicate_detection
  - subset_stability
  - leakage_check
`;

const sampleDataset = Array.from({ length: 35 }, (_, index) => ({
  id: `q${index + 1}`,
  query: `Question ${index + 1}`,
  expected_answer: `answer ${index + 1}`,
  relevant_ids: [`doc${index + 1}`],
  difficulty: index % 3 === 0 ? "hard" : index % 2 === 0 ? "medium" : "easy",
  source: index % 2 === 0 ? "benchmark-a" : "benchmark-b",
}));

const sampleSystem = sampleDataset.map((row) => ({
  id: row.id,
  answer: row.expected_answer,
  retrieved_ids: [row.relevant_ids[0], "distractor-a", "distractor-b"],
  score: 0.9,
}));

const sampleSystemV2 = sampleDataset.map((row) => ({
  id: row.id,
  answer: row.expected_answer,
  retrieved_ids: row.id.endsWith("1")
    ? [`lexical-trap-${row.id}`, row.relevant_ids[0], "distractor-a"]
    : [row.relevant_ids[0], `lexical-trap-${row.id}`, "distractor-a"],
  score: 0.82,
}));

const sampleCorpus = sampleDataset.flatMap((row) => [
  { id: row.relevant_ids[0], text: `${row.query} ${row.expected_answer} supporting passage`, title: `Relevant ${row.id}` },
  { id: `lexical-trap-${row.id}`, text: `${row.query} ${row.query} keyword-heavy distractor without the answer`, title: `Lexical trap ${row.id}` },
  { id: `distractor-${row.id}`, text: `Unrelated background text for ${row.id}`, title: `Distractor ${row.id}` },
]);

const sampleBaseline = sampleDataset.map((row) => ({
  id: row.id,
  answer: "wrong answer",
  retrieved_ids: ["distractor-a", row.relevant_ids[0], "distractor-b"],
  score: 0.45,
}));

const inputSteps = [
  ["Dataset", "Questions and answer key"],
  ["System", "Output from the system being tested"],
  ["Baseline", "Comparison output, unless corpus is loaded"],
  ["Corpus", "Optional docs for BM25 baseline"],
] as const;

function jsonFile(name: string, value: unknown) {
  return new File([JSON.stringify(value, null, 2)], name, { type: "application/json" });
}

function statusClass(value?: string) {
  if (value === "PASS" || value === "passed" || value === "pass" || value === "success") return "status-pass";
  if (value === "FAIL" || value === "failed" || value === "fail" || value === "error") return "status-fail";
  return "status-warn";
}

function verdictLabel(report: AuditReport | undefined, uiState: UiState) {
  if (uiState === "running") return "RUNNING";
  return report?.verdict ?? "READY";
}

function formatScore(value: number | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "-";
}

function FilePicker({
  index,
  label,
  helper,
  file,
  onChange,
}: {
  index: number;
  label: string;
  helper: string;
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  return (
    <label className={`file-card ${file ? "is-loaded" : ""}`}>
      <span className="file-card-top">
        <span className="step-index">{index}</span>
        <span>
          <span className="file-title">{label}</span>
          <span className="file-helper">{helper}</span>
        </span>
        <span className={`file-state ${file ? "loaded" : ""}`}>{file ? "Loaded" : "Needed"}</span>
      </span>
      <input
        className="file-input focus-ring"
        type="file"
        accept=".json,.jsonl,application/json,text/plain"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      <span className="file-name">{file?.name ?? "JSON or JSONL"}</span>
    </label>
  );
}

function MetricCard({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "accent" | "danger" }) {
  return (
    <div className={`metric-card ${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
    </div>
  );
}

export default function Home() {
  const [dataset, setDataset] = useState<File | null>(null);
  const [system, setSystem] = useState<File | null>(null);
  const [baseline, setBaseline] = useState<File | null>(null);
  const [corpus, setCorpus] = useState<File | null>(null);
  const [leftSystem, setLeftSystem] = useState<File | null>(null);
  const [rightSystem, setRightSystem] = useState<File | null>(null);
  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>("system_v1_vs_v2");
  const [comparison, setComparison] = useState<ComparisonReport | null>(null);
  const [config, setConfig] = useState(sampleConfigText);
  const [job, setJob] = useState<JobView | null>(null);
  const [uiState, setUiState] = useState<UiState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);

  const report = job?.report;
  const readyCount = [dataset, system, baseline || corpus].filter(Boolean).length;
  const canRun = useMemo(() => Boolean(dataset && system && (baseline || corpus) && config.trim()), [dataset, system, baseline, corpus, config]);
  const passCount = report?.checks.filter((check) => check.status === "pass").length ?? 0;
  const warnCount = report?.checks.filter((check) => check.status === "warn" || check.status === "not_run").length ?? 0;
  const failCount = report?.checks.filter((check) => check.status === "fail").length ?? 0;

  useEffect(() => {
    let active = true;
    async function loadLatest() {
      const response = await fetch("/api/audits");
      if (!response.ok) return;
      const payload = await response.json();
      if (active && payload.job) setJob(payload.job);
    }
    loadLatest().catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  async function submitAudit(files?: { dataset: File; system: File; baseline?: File | null; corpus?: File | null; config: string }) {
    const auditDataset = files?.dataset ?? dataset;
    const auditSystem = files?.system ?? system;
    const auditBaseline = files?.baseline ?? baseline;
    const auditCorpus = files?.corpus ?? corpus;
    const auditConfig = files?.config ?? config;

    if (!auditDataset || !auditSystem || (!auditBaseline && !auditCorpus) || !auditConfig.trim()) {
      setError("Load dataset, system output, baseline or corpus, and config first.");
      setUiState("error");
      return;
    }

    setError(null);
    setUiState("running");
    const body = new FormData();
    body.set("dataset", auditDataset);
    body.set("system", auditSystem);
    if (auditBaseline) body.set("baseline", auditBaseline);
    if (auditCorpus) body.set("corpus", auditCorpus);
    body.set("config", auditConfig);

    try {
      const response = await fetch("/api/audits", { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error ?? "Audit failed.");
      setJob(payload.job);
      setUiState("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Audit failed.");
      setUiState("error");
    }
  }

  async function submitComparison(files?: { dataset: File; leftSystem: File; rightSystem: File; baseline?: File | null; corpus?: File | null; config: string }) {
    const compareDataset = files?.dataset ?? dataset;
    const compareLeft = files?.leftSystem ?? leftSystem;
    const compareRight = files?.rightSystem ?? rightSystem;
    const compareBaseline = files?.baseline ?? baseline;
    const compareCorpus = files?.corpus ?? corpus;
    const compareConfig = files?.config ?? config;

    if (!compareDataset || !compareLeft || !compareRight || (!compareBaseline && !compareCorpus) || !compareConfig.trim()) {
      setError("Load dataset, two systems, baseline or corpus, and config first.");
      setUiState("error");
      return;
    }

    setError(null);
    setUiState("running");
    const body = new FormData();
    body.set("dataset", compareDataset);
    body.set("left_system", compareLeft);
    body.set("right_system", compareRight);
    if (compareBaseline) body.set("baseline", compareBaseline);
    if (compareCorpus) body.set("corpus", compareCorpus);
    body.set("config", compareConfig);
    body.set("mode", comparisonMode);
    body.set("left_label", comparisonMode === "prompt_a_vs_b" ? "prompt A" : "left");
    body.set("right_label", comparisonMode === "prompt_a_vs_b" ? "prompt B" : "right");

    try {
      const response = await fetch("/api/compare", { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error ?? "Comparison failed.");
      setComparison(payload.comparison);
      setUiState("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Comparison failed.");
      setUiState("error");
    }
  }

  function loadSampleFiles() {
    setDataset(jsonFile("sample-dataset.json", sampleDataset));
    setSystem(jsonFile("sample-system.json", sampleSystem));
    setBaseline(jsonFile("sample-baseline.json", sampleBaseline));
    setCorpus(jsonFile("sample-corpus.json", sampleCorpus));
    setLeftSystem(jsonFile("sample-system-v1.json", sampleSystemV2));
    setRightSystem(jsonFile("sample-system-v2.json", sampleSystem));
    setConfig(sampleConfigText);
    setError(null);
    setUiState("idle");
  }

  async function runSampleAudit() {
    const sampleFiles = {
      dataset: jsonFile("sample-dataset.json", sampleDataset),
      system: jsonFile("sample-system.json", sampleSystem),
      baseline: null,
      corpus: jsonFile("sample-corpus.json", sampleCorpus),
      config: sampleConfigText,
    };
    setDataset(sampleFiles.dataset);
    setSystem(sampleFiles.system);
    setBaseline(sampleFiles.baseline);
    setCorpus(sampleFiles.corpus);
    setConfig(sampleFiles.config);
    await submitAudit(sampleFiles);
  }

  async function runSampleComparison() {
    const sampleFiles = {
      dataset: jsonFile("sample-dataset.json", sampleDataset),
      leftSystem: jsonFile("sample-system-v1.json", sampleSystemV2),
      rightSystem: jsonFile("sample-system-v2.json", sampleSystem),
      baseline: null,
      corpus: jsonFile("sample-corpus.json", sampleCorpus),
      config: sampleConfigText,
    };
    setDataset(sampleFiles.dataset);
    setLeftSystem(sampleFiles.leftSystem);
    setRightSystem(sampleFiles.rightSystem);
    setBaseline(sampleFiles.baseline);
    setCorpus(sampleFiles.corpus);
    setConfig(sampleFiles.config);
    await submitComparison(sampleFiles);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">falsify-eval audit workbench</p>
          <h1>Audit benchmark claims before you trust them.</h1>
          <p className="scope-note">Best for retrieval, ranking, and RAG retrieval-side audits.</p>
        </div>
        <div className="topbar-actions">
          <button className="ghost-button focus-ring" type="button" onClick={() => setShowGuide(true)}>
            Guide
          </button>
          <span className={`status-pill ${statusClass(report?.verdict ?? uiState)}`}>{verdictLabel(report, uiState)}</span>
        </div>
      </header>

      <section className="command-strip">
        <div>
          <p>Ready inputs</p>
          <strong>{readyCount}/3</strong>
        </div>
        <div>
          <p>Primary metric</p>
          <strong>{report?.scores.primary_metric ?? "ndcg@3"}</strong>
        </div>
        <div>
          <p>Latest delta</p>
          <strong>{formatScore(report?.scores.improvement)}</strong>
        </div>
        <button className="sample-button focus-ring" type="button" onClick={runSampleAudit} disabled={uiState === "running"}>
          Try sample audit
        </button>
      </section>

      <div className="workbench-grid">
        <section className="panel input-panel">
          <div className="panel-heading">
            <p className="eyebrow">01 Inputs</p>
            <button className="small-button focus-ring" type="button" onClick={loadSampleFiles}>
              Load sample
            </button>
          </div>
          <div className="file-stack">
            {inputSteps.map(([label, helper], index) => (
              <FilePicker
                key={label}
                index={index + 1}
                label={label}
                helper={helper}
                file={index === 0 ? dataset : index === 1 ? system : index === 2 ? baseline : corpus}
                onChange={index === 0 ? setDataset : index === 1 ? setSystem : index === 2 ? setBaseline : setCorpus}
              />
            ))}
          </div>
        </section>

        <section className="panel config-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">02 Claim config</p>
              <h2>JSON or YAML</h2>
            </div>
            <span className="mini-chip">local only</span>
          </div>
          <textarea
            className="config-editor focus-ring"
            value={config}
            onChange={(event) => setConfig(event.target.value)}
            spellCheck={false}
          />
          <div className="template-grid">
            {AUDIT_TEMPLATES.map((template) => (
              <button
                className="small-button focus-ring"
                key={template.id}
                type="button"
                onClick={() => setConfig(templateToYaml(template))}
              >
                {template.label}
              </button>
            ))}
          </div>
          <div className="run-row">
            <button
              className="primary-button focus-ring"
              type="button"
              disabled={!canRun || uiState === "running"}
              onClick={() => submitAudit()}
            >
              {uiState === "running" ? "Running audit" : "Run audit"}
            </button>
            <button className="ghost-button focus-ring" type="button" disabled={uiState === "running"} onClick={runSampleAudit}>
              Use sample
            </button>
          </div>
          {error ? <p className="error-box">{error}</p> : null}
        </section>

        <section className="panel report-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">03 Report</p>
              <h2>Verdict and evidence</h2>
            </div>
            {job ? (
              <div className="export-row">
                <a className="small-button focus-ring" href={`/api/audits/${job.id}/json`}>
                  JSON
                </a>
                <a className="small-button focus-ring" href={`/api/audits/${job.id}/markdown`}>
                  Markdown
                </a>
                <a className="small-button focus-ring" href={`/api/audits/${job.id}/pack`}>
                  Pack
                </a>
              </div>
            ) : null}
          </div>

          {!report ? (
            <div className="empty-report">
              <div className="signal-bars" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <h2>No audit report yet</h2>
              <p>Run the sample or load your own files. The result appears here with verdict, score delta, and the checks that made the call.</p>
            </div>
          ) : (
            <div className="report-content">
              <div className={`verdict-card ${statusClass(report.verdict)}`}>
                <div>
                  <p className="eyebrow">Verdict</p>
                  <strong>{report.verdict}</strong>
                </div>
                <p>{report.summary}</p>
              </div>

              <div className="metric-grid">
                <MetricCard label="Metric" value={report.scores.primary_metric} />
                <MetricCard label="System" value={formatScore(report.scores.system)} tone="accent" />
                <MetricCard label="Baseline" value={formatScore(report.scores.baseline)} />
                <MetricCard label="Delta" value={formatScore(report.scores.improvement)} tone={report.scores.improvement < 0 ? "danger" : "accent"} />
              </div>

              <div className="metric-grid compact">
                <MetricCard label="Pass" value={String(passCount)} tone="accent" />
                <MetricCard label="Warn" value={String(warnCount)} />
                <MetricCard label="Fail" value={String(failCount)} tone="danger" />
              </div>

              <div className="metric-grid compact">
                <MetricCard label="Rows" value={String(report.dataset_quality.row_count)} />
                <MetricCard label="Corpus docs" value={String(report.dataset_quality.corpus_document_count)} />
                <MetricCard label="Coverage" value={formatScore(report.dataset_quality.coverage_ratio)} tone="accent" />
              </div>

              <div className="evidence-table">
                <div className="table-title">
                  <strong>Evidence checks</strong>
                  <span>{report.checks.length} total</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Check</th>
                        <th>Status</th>
                        <th>Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.checks.map((check) => (
                        <tr key={check.id}>
                          <td className="check-id">{check.id}</td>
                          <td>
                            <span className={`status-pill small ${statusClass(check.status)}`}>{check.status}</span>
                          </td>
                          <td>{check.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="comparison-band panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">04 Compare</p>
            <h2>Run comparison</h2>
          </div>
          <button className="small-button focus-ring" type="button" onClick={runSampleComparison} disabled={uiState === "running"}>
            Sample compare
          </button>
        </div>
        <div className="compare-grid">
          <label className="select-row">
            <span>Mode</span>
            <select className="focus-ring" value={comparisonMode} onChange={(event) => setComparisonMode(event.target.value as ComparisonMode)}>
              <option value="baseline_vs_system">baseline vs system</option>
              <option value="system_v1_vs_v2">system v1 vs v2</option>
              <option value="prompt_a_vs_b">prompt A vs B</option>
            </select>
          </label>
          <FilePicker index={1} label="Left system" helper="v1, prompt A, or baseline-like run" file={leftSystem} onChange={setLeftSystem} />
          <FilePicker index={2} label="Right system" helper="v2, prompt B, or candidate run" file={rightSystem} onChange={setRightSystem} />
          <button className="primary-button focus-ring" type="button" disabled={uiState === "running"} onClick={() => submitComparison()}>
            Compare runs
          </button>
        </div>
        {comparison ? (
          <div className="metric-grid compact compare-result">
            <MetricCard label="Metric" value={comparison.primary_metric} />
            <MetricCard label="Left improvement" value={formatScore(comparison.left.improvement)} />
            <MetricCard label="Right improvement" value={formatScore(comparison.right.improvement)} tone="accent" />
            <MetricCard label="Delta" value={formatScore(comparison.delta.improvement)} tone={comparison.delta.improvement < 0 ? "danger" : "accent"} />
          </div>
        ) : null}
      </section>

      {showGuide ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="guide-modal">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Quick guide</p>
                <h2>Run one audit</h2>
              </div>
              <button className="small-button focus-ring" type="button" onClick={() => setShowGuide(false)}>
                Close
              </button>
            </div>
            <ol className="guide-list">
              <li>Load dataset, system output, and either baseline output or a corpus for BM25.</li>
              <li>Set the claim config in JSON or YAML.</li>
              <li>Run the audit and read the verdict first.</li>
              <li>Use the evidence table to see which checks passed, warned, failed, or were not run.</li>
              <li>Export JSON for automation or Markdown for a readable report.</li>
            </ol>
          </div>
        </div>
      ) : null}
    </main>
  );
}
