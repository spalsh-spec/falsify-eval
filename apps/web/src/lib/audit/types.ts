export type Verdict = "PASS" | "WARN" | "FAIL";
export type CheckStatus = "pass" | "warn" | "fail" | "not_run";
export type Severity = "low" | "medium" | "high";
export type PrimaryMetric =
  | "accuracy"
  | "exact_match"
  | `recall@${number}`
  | `precision@${number}`
  | `ndcg@${number}`;

export type DatasetRow = {
  id: string;
  query: string;
  expected_answer?: string;
  relevant_ids?: string[];
  difficulty?: string;
  source?: string;
  [key: string]: unknown;
};

export type CorpusDocument = {
  id: string;
  text: string;
  title?: string;
  [key: string]: unknown;
};

export type OutputRow = {
  id: string;
  answer?: string;
  retrieved_ids?: string[];
  score?: number;
  [key: string]: unknown;
};

export type ClaimConfig = {
  claim: string;
  primary_metric: PrimaryMetric;
  minimum_effect_size: number;
  alpha: number;
  seed: number;
  system_name: string;
  baseline_name: string;
  system_version?: string;
  dataset_version?: string;
  checks: string[];
};

export type AuditInput = {
  jobId: string;
  dataset: DatasetRow[];
  systemOutputs: OutputRow[];
  baselineOutputs: OutputRow[];
  corpus?: CorpusDocument[];
  datasetQuality?: DatasetQualityReport;
  config: ClaimConfig;
  hashes: {
    dataset_hash: string;
    system_output_hash: string;
    baseline_output_hash: string;
    corpus_hash?: string;
    config_hash: string;
  };
  createdAt: string;
};

export type DatasetQualityIssue = {
  id: string;
  severity: Severity;
  message: string;
  evidence: Record<string, unknown>;
};

export type DatasetQualityReport = {
  row_count: number;
  corpus_document_count: number;
  relevant_id_count: number;
  covered_relevant_id_count: number;
  coverage_ratio: number;
  duplicate_query_count: number;
  duplicate_id_count: number;
  missing_relevant_ids_count: number;
  empty_query_count: number;
  issues: DatasetQualityIssue[];
};

export type AuditCheck = {
  id: string;
  status: CheckStatus;
  severity: Severity;
  message: string;
  evidence: Record<string, unknown>;
};

export type AuditScores = {
  primary_metric: string;
  system: number;
  baseline: number;
  improvement: number;
  by_difficulty?: Record<string, { system: number; baseline: number; improvement: number; n: number }>;
  by_source?: Record<string, { system: number; baseline: number; improvement: number; n: number }>;
};

export type AuditReport = {
  job_id: string;
  verdict: Verdict;
  claim: string;
  summary: string;
  scores: AuditScores;
  checks: AuditCheck[];
  reproducibility: {
    dataset_hash: string;
    system_output_hash: string;
    baseline_output_hash: string;
    corpus_hash?: string;
    config_hash: string;
    seed: number;
    system_version: string;
    dataset_version: string;
    timestamp_recorded: string;
    audit_engine_version: string;
  };
  dataset_quality: DatasetQualityReport;
  created_at: string;
};
