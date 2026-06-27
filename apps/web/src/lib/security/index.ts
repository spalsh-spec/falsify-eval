import { z } from "zod";
import { JSON_SCHEMA, load } from "js-yaml";
import type { ClaimConfig, CorpusDocument, DatasetRow, OutputRow } from "@/lib/audit/types";

export const DEFAULT_MAX_UPLOAD_BYTES = Number(process.env.AUDIT_MAX_UPLOAD_BYTES ?? 10 * 1024 * 1024);
const ALLOWED_EXTENSIONS = new Set([".json", ".jsonl"]);
const ALLOWED_MIME = new Set(["application/json", "application/x-ndjson", "text/plain", ""]);

export const datasetRowSchema = z.object({
  id: z.string().min(1),
  query: z.string().min(1),
  expected_answer: z.string().optional(),
  relevant_ids: z.array(z.string()).optional().default([]),
  difficulty: z.string().optional(),
  source: z.string().optional(),
}).passthrough();

export const outputRowSchema = z.object({
  id: z.string().min(1),
  answer: z.string().optional(),
  retrieved_ids: z.array(z.string()).optional().default([]),
  score: z.number().optional(),
}).passthrough();

export const corpusDocumentSchema = z.object({
  id: z.string().min(1),
  text: z.string().min(1),
  title: z.string().optional(),
}).passthrough();

export const claimConfigSchema = z.object({
  claim: z.string().min(1),
  primary_metric: z.union([
    z.literal("accuracy"),
    z.literal("exact_match"),
    z.string().regex(/^(recall|precision|ndcg)@\d+$/),
  ]),
  minimum_effect_size: z.number().min(0).max(1).default(0.03),
  alpha: z.number().min(0.001).max(0.5).default(0.05),
  seed: z.number().int().nonnegative().default(42),
  system_name: z.string().min(1).default("System"),
  baseline_name: z.string().min(1).default("Baseline"),
  system_version: z.string().optional().default("unknown"),
  dataset_version: z.string().optional().default("unknown"),
  checks: z.array(z.string()).default([]),
});

export function extensionOf(name: string): string {
  const clean = name.toLowerCase();
  const index = clean.lastIndexOf(".");
  return index >= 0 ? clean.slice(index) : "";
}

export function assertSafeFilename(name: string): void {
  if (name.includes("/") || name.includes("\\") || name.includes("..") || name.includes("\0")) {
    throw new Error("Unsafe filename rejected.");
  }
}

export function validateUploadMeta(file: { name: string; size: number; type?: string }, maxBytes = DEFAULT_MAX_UPLOAD_BYTES): void {
  assertSafeFilename(file.name);
  if (file.size > maxBytes) throw new Error(`File exceeds max size of ${maxBytes} bytes.`);
  if (!ALLOWED_EXTENSIONS.has(extensionOf(file.name))) throw new Error("Only .json and .jsonl files are accepted.");
  if (!ALLOWED_MIME.has(file.type ?? "")) throw new Error("Unsupported MIME type.");
}

export function parseJsonOrJsonl(text: string, filename: string): unknown {
  const ext = extensionOf(filename);
  try {
    if (ext === ".jsonl") {
      return text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => JSON.parse(line));
    }
    return JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON in ${filename}.`);
  }
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function normalizeDatasetRow(value: unknown, index: number): unknown {
  if (!value || typeof value !== "object") return value;
  const row = value as Record<string, unknown>;
  const query = row.query ?? row.question ?? row.input ?? row.prompt;
  const answer = row.expected_answer ?? row.answer ?? row.ground_truth ?? row.ground_truth_answer ?? (Array.isArray(row.ground_truths) ? row.ground_truths[0] : undefined);
  const contextIds = stringArray(row.relevant_ids ?? row.relevant_doc_ids ?? row.gold_doc_ids ?? row.document_ids ?? row.context_ids);
  const contextDocs = stringArray(row.contexts ?? row.documents).map((_, docIndex) => `${String(row.id ?? row.query_id ?? `q${index + 1}`)}-ctx${docIndex + 1}`);

  return {
    ...row,
    id: String(row.id ?? row.query_id ?? row.question_id ?? `q${index + 1}`),
    query,
    expected_answer: typeof answer === "string" ? answer : undefined,
    relevant_ids: contextIds.length > 0 ? contextIds : contextDocs,
  };
}

function normalizeOutputRow(value: unknown, index: number): unknown {
  if (!value || typeof value !== "object") return value;
  const row = value as Record<string, unknown>;
  return {
    ...row,
    id: String(row.id ?? row.query_id ?? row.question_id ?? `q${index + 1}`),
    answer: typeof row.answer === "string" ? row.answer : typeof row.response === "string" ? row.response : undefined,
    retrieved_ids: stringArray(row.retrieved_ids ?? row.retrieved_doc_ids ?? row.document_ids ?? row.context_ids),
  };
}

function normalizeCorpusDocument(value: unknown, index: number): unknown {
  if (!value || typeof value !== "object") return value;
  const row = value as Record<string, unknown>;
  return {
    ...row,
    id: String(row.id ?? row.doc_id ?? row.document_id ?? row.source_id ?? `doc${index + 1}`),
    text: row.text ?? row.content ?? row.page_content ?? row.body,
    title: typeof row.title === "string" ? row.title : undefined,
  };
}

export function parseJsonOrYaml(text: string, filename = "config"): unknown {
  try {
    return JSON.parse(text);
  } catch {
    try {
      return load(text, { filename, schema: JSON_SCHEMA });
    } catch {
      throw new Error(`Invalid JSON or YAML in ${filename}.`);
    }
  }
}

export function parseDataset(value: unknown): DatasetRow[] {
  const rows = Array.isArray(value) ? value : z.object({ rows: z.array(z.unknown()) }).parse(value).rows;
  return z.array(datasetRowSchema).min(1).parse(rows.map(normalizeDatasetRow));
}

export function parseOutputs(value: unknown): OutputRow[] {
  const rows = Array.isArray(value) ? value : z.object({ rows: z.array(z.unknown()) }).parse(value).rows;
  return z.array(outputRowSchema).min(1).parse(rows.map(normalizeOutputRow));
}

export function parseCorpus(value: unknown): CorpusDocument[] {
  const rows = Array.isArray(value) ? value : z.object({ rows: z.array(z.unknown()) }).parse(value).rows;
  return z.array(corpusDocumentSchema).min(1).parse(rows.map(normalizeCorpusDocument));
}

export function parseClaimConfig(value: unknown): ClaimConfig {
  return claimConfigSchema.parse(value) as ClaimConfig;
}

export function redactSecrets(input: string): string {
  return input
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[redacted-email]")
    .replace(/(?<![A-Za-z0-9_-])(?:\+?\d[\s().-]*){10,}(?![A-Za-z0-9_-])/g, "[redacted-phone]")
    .replace(/\bBearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, "Bearer [redacted-token]")
    .replace(/\b(?:sk|pk|api|key|token|secret)[_-]?[A-Za-z0-9]{16,}\b/gi, "[redacted-secret]")
    .replace(/\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b/g, "[redacted-token]");
}

export function redactedJson<T>(value: T): T {
  if (typeof value === "string") return redactSecrets(value) as T;
  if (Array.isArray(value)) return value.map((item) => redactedJson(item)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, redactedJson(item)]),
    ) as T;
  }
  return value;
}
