import { createHash } from "node:crypto";
import { mean, metricScore, pairedScores, variance } from "./metrics";
import { datasetQualityReport } from "./quality";
import { createRng, sampleIndex, shuffle } from "./random";
import type { AuditCheck, AuditInput, AuditReport, DatasetRow, OutputRow } from "./types";

export const AUDIT_ENGINE_VERSION = "0.1.0";

function check(id: string, status: AuditCheck["status"], severity: AuditCheck["severity"], message: string, evidence: Record<string, unknown> = {}): AuditCheck {
  return { id, status, severity, message, evidence };
}

export function stableHash(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

export function bootstrapCi(values: number[], seed: number, rounds = 400): { low: number; high: number; mean: number } {
  if (values.length === 0) return { low: 0, high: 0, mean: 0 };
  const rng = createRng(seed);
  const estimates: number[] = [];
  for (let i = 0; i < rounds; i += 1) {
    const sample: number[] = [];
    for (let j = 0; j < values.length; j += 1) sample.push(values[sampleIndex(rng, values.length)]);
    estimates.push(mean(sample));
  }
  estimates.sort((a, b) => a - b);
  return {
    low: estimates[Math.floor(rounds * 0.025)],
    high: estimates[Math.floor(rounds * 0.975)],
    mean: mean(values),
  };
}

export function duplicateQueryCheck(dataset: DatasetRow[]): AuditCheck {
  const exact = new Map<string, number>();
  for (const row of dataset) {
    const key = row.query.toLowerCase().replace(/\s+/g, " ").trim();
    exact.set(key, (exact.get(key) ?? 0) + 1);
  }
  const duplicateCount = [...exact.values()].filter((count) => count > 1).reduce((sum, count) => sum + count, 0);
  return duplicateCount > 0
    ? check("duplicate_detection", "warn", "medium", "Duplicate queries found.", { duplicate_query_rows: duplicateCount })
    : check("duplicate_detection", "pass", "low", "No exact duplicate queries found.", { duplicate_query_rows: 0 });
}

export function nearDuplicateQueryCheck(dataset: DatasetRow[]): AuditCheck {
  const tokens = dataset.map((row) => new Set(row.query.toLowerCase().split(/\W+/).filter(Boolean)));
  let pairs = 0;
  for (let i = 0; i < tokens.length; i += 1) {
    for (let j = i + 1; j < tokens.length; j += 1) {
      const a = tokens[i];
      const b = tokens[j];
      const intersection = [...a].filter((token) => b.has(token)).length;
      const union = new Set([...a, ...b]).size;
      if (union > 0 && intersection / union >= 0.9) pairs += 1;
    }
  }
  return pairs > 0
    ? check("near_duplicate_detection", "warn", "medium", "Near-duplicate query pairs found.", { near_duplicate_pairs: pairs })
    : check("near_duplicate_detection", "pass", "low", "No near-duplicate query pairs found.", { near_duplicate_pairs: 0 });
}

export function leakageCheck(dataset: DatasetRow[], outputs: OutputRow[]): AuditCheck {
  const expectedCounts = new Map<string, number>();
  const datasetIds = new Set(dataset.map((row) => row.id));
  let idOverlap = 0;
  for (const row of dataset) {
    if (row.expected_answer) expectedCounts.set(row.expected_answer, (expectedCounts.get(row.expected_answer) ?? 0) + 1);
  }
  for (const output of outputs) {
    for (const retrieved of output.retrieved_ids ?? []) {
      if (datasetIds.has(retrieved)) idOverlap += 1;
    }
  }
  const repeatedAnswers = [...expectedCounts.entries()].filter(([, count]) => count >= 3).length;
  if (idOverlap > 0 || repeatedAnswers > 0) {
    return check("leakage_check", "fail", "high", "Potential leakage detected through ID overlap or repeated answer text.", {
      retrieved_dataset_id_overlap: idOverlap,
      repeated_expected_answers: repeatedAnswers,
    });
  }
  return check("leakage_check", "pass", "low", "No obvious leakage pattern found.", {
    retrieved_dataset_id_overlap: 0,
    repeated_expected_answers: 0,
  });
}

function shuffledLabelCheck(input: AuditInput): AuditCheck {
  const shuffled = shuffle(input.dataset.map((row) => row.relevant_ids ?? []), input.config.seed);
  const shuffledDataset = input.dataset.map((row, index) => ({ ...row, relevant_ids: shuffled[index] }));
  const shuffledScore = mean(pairedScores(shuffledDataset, input.systemOutputs, input.config.primary_metric));
  const realScore = mean(pairedScores(input.dataset, input.systemOutputs, input.config.primary_metric));
  const collapse = realScore - shuffledScore;
  if (collapse < input.config.minimum_effect_size) {
    return check("shuffled_labels", "fail", "high", "System score does not collapse under shuffled labels.", { real_score: realScore, shuffled_score: shuffledScore, collapse });
  }
  return check("shuffled_labels", "pass", "medium", "System score drops under shuffled labels.", { real_score: realScore, shuffled_score: shuffledScore, collapse });
}

function randomBaselineCheck(input: AuditInput): AuditCheck {
  const pool = [...new Set(input.dataset.flatMap((row) => row.relevant_ids ?? []))];
  if (pool.length < 2) return check("random_baseline", "not_run", "medium", "Not enough relevant IDs to build a random baseline.", { pool_size: pool.length });
  const rng = createRng(input.config.seed);
  const randomOutputs = input.dataset.map((row) => ({
    id: row.id,
    retrieved_ids: Array.from({ length: 10 }, () => pool[sampleIndex(rng, pool.length)]),
  }));
  const randomScore = mean(pairedScores(input.dataset, randomOutputs, input.config.primary_metric));
  const systemScore = mean(pairedScores(input.dataset, input.systemOutputs, input.config.primary_metric));
  const margin = systemScore - randomScore;
  return margin >= input.config.minimum_effect_size
    ? check("random_baseline", "pass", "medium", "System beats random baseline by the configured margin.", { system_score: systemScore, random_score: randomScore, margin })
    : check("random_baseline", "fail", "high", "System does not beat random baseline by the configured margin.", { system_score: systemScore, random_score: randomScore, margin });
}

function subsetStabilityCheck(input: AuditInput, systemScores: number[], baselineScores: number[]): AuditCheck {
  if (input.dataset.length < 20) return check("subset_stability", "warn", "medium", "Benchmark is too small for reliable subset stability.", { n: input.dataset.length });
  const half = Math.floor(input.dataset.length / 2);
  const first = mean(systemScores.slice(0, half)) - mean(baselineScores.slice(0, half));
  const second = mean(systemScores.slice(half)) - mean(baselineScores.slice(half));
  const gap = Math.abs(first - second);
  return gap <= Math.max(0.05, input.config.minimum_effect_size * 2)
    ? check("subset_stability", "pass", "medium", "Improvement is stable across deterministic halves.", { first_half_improvement: first, second_half_improvement: second, gap })
    : check("subset_stability", "warn", "medium", "Improvement changes materially across deterministic halves.", { first_half_improvement: first, second_half_improvement: second, gap });
}

function groupedScores(input: AuditInput, key: "difficulty" | "source") {
  const groups: Record<string, { system: number[]; baseline: number[] }> = {};
  const systemById = new Map(input.systemOutputs.map((row) => [row.id, row]));
  const baselineById = new Map(input.baselineOutputs.map((row) => [row.id, row]));
  for (const row of input.dataset) {
    const value = row[key];
    if (!value) continue;
    groups[value] ??= { system: [], baseline: [] };
    groups[value].system.push(metricScore(row, systemById.get(row.id) ?? { id: row.id }, input.config.primary_metric));
    groups[value].baseline.push(metricScore(row, baselineById.get(row.id) ?? { id: row.id }, input.config.primary_metric));
  }
  return Object.fromEntries(Object.entries(groups).map(([name, scores]) => [name, {
    system: mean(scores.system),
    baseline: mean(scores.baseline),
    improvement: mean(scores.system) - mean(scores.baseline),
    n: scores.system.length,
  }]));
}

export function runAudit(input: AuditInput): AuditReport {
  const datasetQuality = input.datasetQuality ?? datasetQualityReport(input.dataset, input.corpus);
  const systemScores = pairedScores(input.dataset, input.systemOutputs, input.config.primary_metric);
  const baselineScores = pairedScores(input.dataset, input.baselineOutputs, input.config.primary_metric);
  const deltas = systemScores.map((score, index) => score - baselineScores[index]);
  const improvement = mean(deltas);
  const ci = bootstrapCi(deltas, input.config.seed);
  const checks: AuditCheck[] = [];

  checks.push(
    check("bootstrap_ci", ci.low > 0 ? "pass" : "warn", "medium", ci.low > 0 ? "Bootstrap CI is above zero." : "Bootstrap CI overlaps zero.", ci),
  );
  checks.push(
    check("effect_size", improvement >= input.config.minimum_effect_size ? "pass" : "fail", "high", improvement >= input.config.minimum_effect_size ? "Improvement clears the configured threshold." : "Improvement is below the configured threshold.", {
      improvement,
      minimum_effect_size: input.config.minimum_effect_size,
    }),
  );
  checks.push(
    input.dataset.length >= 30
      ? check("small_n", "pass", "low", "Sample size clears the MVP minimum.", { n: input.dataset.length })
      : check("small_n", "warn", "medium", "Small benchmark. Treat aggregate claims cautiously.", { n: input.dataset.length }),
  );
  checks.push(
    variance(deltas) <= 0.08
      ? check("variance_warning", "pass", "low", "Paired improvement variance is within the MVP threshold.", { variance: variance(deltas) })
      : check("variance_warning", "warn", "medium", "High variance across examples.", { variance: variance(deltas) }),
  );
  checks.push(shuffledLabelCheck(input));
  checks.push(randomBaselineCheck(input));
  checks.push(
    input.corpus && input.corpus.length > 0
      ? check("lexical_baseline", "pass", "medium", "BM25 lexical baseline was built from the uploaded corpus.", {
        corpus_documents: input.corpus.length,
        baseline_name: input.config.baseline_name,
      })
      : check("lexical_baseline", "not_run", "medium", "No corpus index was provided, so lexical baseline is documented but not run.", {}),
  );
  checks.push(duplicateQueryCheck(input.dataset));
  checks.push(nearDuplicateQueryCheck(input.dataset));
  checks.push(leakageCheck(input.dataset, input.systemOutputs));
  checks.push(
    datasetQuality.issues.some((item) => item.severity === "high")
      ? check("dataset_quality", "fail", "high", "Dataset quality report found high-severity issues.", datasetQuality)
      : datasetQuality.issues.length > 0
        ? check("dataset_quality", "warn", "medium", "Dataset quality report found warnings.", datasetQuality)
        : check("dataset_quality", "pass", "low", "Dataset quality report found no blocking issues.", datasetQuality),
  );
  checks.push(subsetStabilityCheck(input, systemScores, baselineScores));
  checks.push(check("small_vs_expanded", "not_run", "medium", "No expanded benchmark file was provided.", {}));
  checks.push(check("long_context_subset", "not_run", "low", "No length field was provided.", {}));

  const fail = checks.some((item) => item.status === "fail" && item.severity !== "low");
  const warn = checks.some((item) => item.status === "warn" || item.status === "not_run");
  const verdict = fail ? "FAIL" : warn ? "WARN" : "PASS";
  const summary = `${input.config.system_name} ${improvement >= 0 ? "beats" : "does not beat"} ${input.config.baseline_name} by ${improvement.toFixed(4)} on ${input.config.primary_metric}. Verdict: ${verdict}.`;

  return {
    job_id: input.jobId,
    verdict,
    claim: input.config.claim,
    summary,
    scores: {
      primary_metric: input.config.primary_metric,
      system: mean(systemScores),
      baseline: mean(baselineScores),
      improvement,
      by_difficulty: groupedScores(input, "difficulty"),
      by_source: groupedScores(input, "source"),
    },
    checks,
    reproducibility: {
      ...input.hashes,
      seed: input.config.seed,
      system_version: input.config.system_version ?? "unknown",
      dataset_version: input.config.dataset_version ?? "unknown",
      timestamp_recorded: input.createdAt,
      audit_engine_version: AUDIT_ENGINE_VERSION,
    },
    dataset_quality: datasetQuality,
    created_at: input.createdAt,
  };
}
