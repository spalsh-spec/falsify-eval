import type { CorpusDocument, DatasetQualityIssue, DatasetQualityReport, DatasetRow } from "./types";

function issue(id: string, severity: DatasetQualityIssue["severity"], message: string, evidence: Record<string, unknown>): DatasetQualityIssue {
  return { id, severity, message, evidence };
}

export function datasetQualityReport(dataset: DatasetRow[], corpus: CorpusDocument[] = []): DatasetQualityReport {
  const queryCounts = new Map<string, number>();
  const idCounts = new Map<string, number>();
  const corpusIds = new Set(corpus.map((doc) => doc.id));
  const relevantIds = new Set<string>();
  let missingRelevantIds = 0;
  let emptyQueryCount = 0;

  for (const row of dataset) {
    const normalizedQuery = row.query.toLowerCase().replace(/\s+/g, " ").trim();
    queryCounts.set(normalizedQuery, (queryCounts.get(normalizedQuery) ?? 0) + 1);
    idCounts.set(row.id, (idCounts.get(row.id) ?? 0) + 1);
    if (!normalizedQuery) emptyQueryCount += 1;
    if (!row.relevant_ids || row.relevant_ids.length === 0) missingRelevantIds += 1;
    for (const id of row.relevant_ids ?? []) relevantIds.add(id);
  }

  const duplicateQueryCount = [...queryCounts.values()].filter((count) => count > 1).reduce((sum, count) => sum + count, 0);
  const duplicateIdCount = [...idCounts.values()].filter((count) => count > 1).reduce((sum, count) => sum + count, 0);
  const coveredRelevantIdCount = [...relevantIds].filter((id) => corpusIds.has(id)).length;
  const coverageRatio = relevantIds.size === 0 ? 0 : coveredRelevantIdCount / relevantIds.size;
  const issues: DatasetQualityIssue[] = [];

  if (duplicateIdCount > 0) issues.push(issue("duplicate_ids", "high", "Dataset has duplicate row IDs.", { duplicate_id_rows: duplicateIdCount }));
  if (duplicateQueryCount > 0) issues.push(issue("duplicate_queries", "medium", "Dataset has duplicate queries.", { duplicate_query_rows: duplicateQueryCount }));
  if (missingRelevantIds > 0) issues.push(issue("missing_relevant_ids", "high", "Some rows do not define relevant document IDs.", { rows: missingRelevantIds }));
  if (emptyQueryCount > 0) issues.push(issue("empty_queries", "high", "Some rows have empty queries.", { rows: emptyQueryCount }));
  if (corpus.length > 0 && coverageRatio < 1) {
    issues.push(issue("corpus_coverage", "medium", "Corpus does not cover every relevant document ID.", {
      relevant_id_count: relevantIds.size,
      covered_relevant_id_count: coveredRelevantIdCount,
      coverage_ratio: coverageRatio,
    }));
  }

  return {
    row_count: dataset.length,
    corpus_document_count: corpus.length,
    relevant_id_count: relevantIds.size,
    covered_relevant_id_count: coveredRelevantIdCount,
    coverage_ratio: coverageRatio,
    duplicate_query_count: duplicateQueryCount,
    duplicate_id_count: duplicateIdCount,
    missing_relevant_ids_count: missingRelevantIds,
    empty_query_count: emptyQueryCount,
    issues,
  };
}
