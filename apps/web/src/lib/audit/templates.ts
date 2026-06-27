import type { ClaimConfig, PrimaryMetric } from "./types";

export type AuditTemplateId = "rag_search" | "support_docs_qa" | "sanskrit_retrieval" | "academic_retrieval";

export type AuditTemplate = {
  id: AuditTemplateId;
  label: string;
  description: string;
  config: ClaimConfig;
};

export const AUDIT_TEMPLATES: AuditTemplate[] = [
  {
    id: "rag_search",
    label: "RAG search",
    description: "Top-k retrieval audit for a general RAG search system.",
    config: baseConfig("RAG system beats BM25 on retrieval quality", "ndcg@5", "RAG system", "BM25"),
  },
  {
    id: "support_docs_qa",
    label: "Support docs QA",
    description: "Support knowledge-base retrieval before answer generation.",
    config: baseConfig("Support retriever beats BM25 on documented answers", "recall@5", "Support retriever", "BM25"),
  },
  {
    id: "sanskrit_retrieval",
    label: "Sanskrit retrieval",
    description: "Lexical and source-grounded retrieval for Sanskrit passages.",
    config: baseConfig("Sanskrit retriever beats BM25 on source retrieval", "ndcg@10", "Sanskrit retriever", "BM25"),
  },
  {
    id: "academic_retrieval",
    label: "Academic retrieval",
    description: "Paper, claim, or citation retrieval over academic corpora.",
    config: baseConfig("Academic retriever beats BM25 on evidence retrieval", "precision@10", "Academic retriever", "BM25"),
  },
];

function baseConfig(claim: string, metric: PrimaryMetric, systemName: string, baselineName: string): ClaimConfig {
  return {
    claim,
    primary_metric: metric,
    minimum_effect_size: 0.03,
    alpha: 0.05,
    seed: 42,
    system_name: systemName,
    baseline_name: baselineName,
    system_version: "local",
    dataset_version: "local",
    checks: ["bootstrap_ci", "shuffled_labels", "random_baseline", "lexical_baseline", "dataset_quality"],
  };
}

export function getAuditTemplate(id: string): AuditTemplate {
  const template = AUDIT_TEMPLATES.find((item) => item.id === id);
  if (!template) throw new Error(`Unknown template: ${id}`);
  return template;
}

export function templateToYaml(template: AuditTemplate): string {
  const config = template.config;
  return [
    `claim: ${config.claim}`,
    `primary_metric: ${config.primary_metric}`,
    `minimum_effect_size: ${config.minimum_effect_size}`,
    `alpha: ${config.alpha}`,
    `seed: ${config.seed}`,
    `system_name: ${config.system_name}`,
    `baseline_name: ${config.baseline_name}`,
    `system_version: ${config.system_version ?? "local"}`,
    `dataset_version: ${config.dataset_version ?? "local"}`,
    "checks:",
    ...config.checks.map((item) => `  - ${item}`),
    "",
  ].join("\n");
}
