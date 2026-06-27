import type { DatasetRow, OutputRow, PrimaryMetric } from "./types";

export function parseMetric(metric: PrimaryMetric): { name: string; k?: number } {
  const [name, rawK] = metric.split("@");
  return { name, k: rawK ? Number(rawK) : undefined };
}

export function normalizeText(value: string | undefined): string {
  return (value ?? "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function exactMatch(row: DatasetRow, output: OutputRow): number {
  if (!row.expected_answer || !output.answer) return 0;
  return normalizeText(row.expected_answer) === normalizeText(output.answer) ? 1 : 0;
}

export function metricScore(row: DatasetRow, output: OutputRow, metric: PrimaryMetric): number {
  const { name, k } = parseMetric(metric);
  const relevant = new Set(row.relevant_ids ?? []);
  const retrieved = output.retrieved_ids ?? [];

  if (name === "exact_match") return exactMatch(row, output);
  if (name === "accuracy") {
    if (row.expected_answer && output.answer) return exactMatch(row, output);
    return retrieved[0] && relevant.has(retrieved[0]) ? 1 : 0;
  }

  const limit = Math.max(1, k ?? 10);
  const top = retrieved.slice(0, limit);
  if (relevant.size === 0) return 0;

  if (name === "recall") {
    const hits = top.filter((id) => relevant.has(id)).length;
    return hits / relevant.size;
  }

  if (name === "precision") {
    if (top.length === 0) return 0;
    const hits = top.filter((id) => relevant.has(id)).length;
    return hits / limit;
  }

  if (name === "ndcg") {
    const dcg = top.reduce((sum, id, index) => {
      return sum + (relevant.has(id) ? 1 / Math.log2(index + 2) : 0);
    }, 0);
    const idealHits = Math.min(relevant.size, limit);
    const idcg = Array.from({ length: idealHits }).reduce<number>((sum, _, index) => {
      return sum + 1 / Math.log2(index + 2);
    }, 0);
    return idcg === 0 ? 0 : dcg / idcg;
  }

  return 0;
}

export function pairedScores(
  dataset: DatasetRow[],
  outputs: OutputRow[],
  metric: PrimaryMetric,
): number[] {
  const byId = new Map(outputs.map((row) => [row.id, row]));
  return dataset.map((row) => metricScore(row, byId.get(row.id) ?? { id: row.id }, metric));
}

export function mean(values: readonly number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function variance(values: readonly number[]): number {
  if (values.length < 2) return 0;
  const m = mean(values);
  return values.reduce((sum, value) => sum + (value - m) ** 2, 0) / (values.length - 1);
}
