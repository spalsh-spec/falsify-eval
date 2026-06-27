import type { AuditReport, Verdict } from "./types";

export type ComparisonMode = "baseline_vs_system" | "system_v1_vs_v2" | "prompt_a_vs_b";

export type ComparisonReport = {
  mode: ComparisonMode;
  left_label: string;
  right_label: string;
  primary_metric: string;
  left: {
    verdict: Verdict;
    system_score: number;
    baseline_score: number;
    improvement: number;
  };
  right: {
    verdict: Verdict;
    system_score: number;
    baseline_score: number;
    improvement: number;
  };
  delta: {
    system_score: number;
    improvement: number;
    pass_checks: number;
    fail_checks: number;
  };
  summary: string;
};

function count(report: AuditReport, status: "pass" | "fail"): number {
  return report.checks.filter((item) => item.status === status).length;
}

export function compareAuditReports(
  left: AuditReport,
  right: AuditReport,
  options: { mode: ComparisonMode; leftLabel: string; rightLabel: string },
): ComparisonReport {
  if (left.scores.primary_metric !== right.scores.primary_metric) {
    throw new Error("Cannot compare audits with different primary metrics.");
  }

  const systemDelta = right.scores.system - left.scores.system;
  const improvementDelta = right.scores.improvement - left.scores.improvement;
  const passDelta = count(right, "pass") - count(left, "pass");
  const failDelta = count(right, "fail") - count(left, "fail");
  const better = improvementDelta > 0 ? options.rightLabel : improvementDelta < 0 ? options.leftLabel : "Neither run";

  return {
    mode: options.mode,
    left_label: options.leftLabel,
    right_label: options.rightLabel,
    primary_metric: left.scores.primary_metric,
    left: {
      verdict: left.verdict,
      system_score: left.scores.system,
      baseline_score: left.scores.baseline,
      improvement: left.scores.improvement,
    },
    right: {
      verdict: right.verdict,
      system_score: right.scores.system,
      baseline_score: right.scores.baseline,
      improvement: right.scores.improvement,
    },
    delta: {
      system_score: systemDelta,
      improvement: improvementDelta,
      pass_checks: passDelta,
      fail_checks: failDelta,
    },
    summary: `${better} leads on ${left.scores.primary_metric} by ${Math.abs(improvementDelta).toFixed(4)} improvement delta.`,
  };
}
