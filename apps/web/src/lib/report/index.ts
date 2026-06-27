import { redactSecrets, redactedJson } from "@/lib/security";
import type { AuditReport } from "@/lib/audit/types";

export function toJsonReport(report: AuditReport): AuditReport {
  return redactedJson(report);
}

export function toMarkdownReport(report: AuditReport): string {
  const safe = toJsonReport(report);
  const checks = safe.checks
    .map((item) => `| ${item.id} | ${item.status} | ${item.severity} | ${item.message.replace(/\|/g, "\\|")} |`)
    .join("\n");
  const qualityIssues = safe.dataset_quality.issues.length > 0
    ? safe.dataset_quality.issues.map((item) => `| ${item.id} | ${item.severity} | ${item.message.replace(/\|/g, "\\|")} |`).join("\n")
    : "| none | low | No dataset quality issues found. |";

  return redactSecrets(`# falsify-eval audit report

## Verdict
${safe.verdict}

## Claim
${safe.claim}

## Summary
${safe.summary}

## Scores
| Metric | System | Baseline | Improvement |
|---|---:|---:|---:|
| ${safe.scores.primary_metric} | ${safe.scores.system.toFixed(6)} | ${safe.scores.baseline.toFixed(6)} | ${safe.scores.improvement.toFixed(6)} |

## Dataset quality
| Rows | Corpus docs | Relevant IDs | Covered relevant IDs | Coverage |
|---:|---:|---:|---:|---:|
| ${safe.dataset_quality.row_count} | ${safe.dataset_quality.corpus_document_count} | ${safe.dataset_quality.relevant_id_count} | ${safe.dataset_quality.covered_relevant_id_count} | ${safe.dataset_quality.coverage_ratio.toFixed(3)} |

| Issue | Severity | Message |
|---|---|---|
${qualityIssues}

## Evidence
| Check | Status | Severity | Message |
|---|---|---|---|
${checks}

## Reproducibility
- dataset_hash: ${safe.reproducibility.dataset_hash}
- system_output_hash: ${safe.reproducibility.system_output_hash}
- baseline_output_hash: ${safe.reproducibility.baseline_output_hash}
- config_hash: ${safe.reproducibility.config_hash}
- seed: ${safe.reproducibility.seed}
- system_version: ${safe.reproducibility.system_version}
- dataset_version: ${safe.reproducibility.dataset_version}
- timestamp_recorded: ${safe.reproducibility.timestamp_recorded}
- audit_engine_version: ${safe.reproducibility.audit_engine_version}
`);
}
