import type { CorpusDocument, DatasetRow, OutputRow } from "./types";

const K1 = 1.5;
const B = 0.75;

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/i)
    .filter((token) => token.length > 1);
}

type IndexedDocument = {
  doc: CorpusDocument;
  termCounts: Map<string, number>;
  length: number;
};

export function bm25Score(query: string, document: string, corpus: string[]): number {
  const queryTerms = [...new Set(tokenize(query))];
  const documents = corpus.map((text) => tokenize(text));
  const docTerms = tokenize(document);
  const docTermCounts = new Map<string, number>();
  for (const token of docTerms) docTermCounts.set(token, (docTermCounts.get(token) ?? 0) + 1);
  const averageLength = documents.reduce((sum, tokens) => sum + tokens.length, 0) / Math.max(1, documents.length);

  return queryTerms.reduce((score, term) => {
    const documentFrequency = documents.filter((tokens) => tokens.includes(term)).length;
    if (documentFrequency === 0) return score;
    const idf = Math.log(1 + (documents.length - documentFrequency + 0.5) / (documentFrequency + 0.5));
    const frequency = docTermCounts.get(term) ?? 0;
    if (frequency === 0) return score;
    const denominator = frequency + K1 * (1 - B + B * (docTerms.length / Math.max(1, averageLength)));
    return score + idf * ((frequency * (K1 + 1)) / denominator);
  }, 0);
}

export function buildBm25Baseline(dataset: DatasetRow[], corpus: CorpusDocument[], k = 10): OutputRow[] {
  const indexed: IndexedDocument[] = corpus.map((doc) => {
    const tokens = tokenize(`${doc.title ?? ""} ${doc.text}`);
    const termCounts = new Map<string, number>();
    for (const token of tokens) termCounts.set(token, (termCounts.get(token) ?? 0) + 1);
    return { doc, termCounts, length: tokens.length };
  });
  const averageLength = indexed.reduce((sum, item) => sum + item.length, 0) / Math.max(1, indexed.length);
  const documentFrequency = new Map<string, number>();
  for (const item of indexed) {
    for (const term of item.termCounts.keys()) documentFrequency.set(term, (documentFrequency.get(term) ?? 0) + 1);
  }

  return dataset.map((row) => {
    const queryTerms = [...new Set(tokenize(row.query))];
    const ranked = indexed
      .map((item) => {
        const score = queryTerms.reduce((total, term) => {
          const frequency = item.termCounts.get(term) ?? 0;
          if (frequency === 0) return total;
          const df = documentFrequency.get(term) ?? 0;
          const idf = Math.log(1 + (indexed.length - df + 0.5) / (df + 0.5));
          const denominator = frequency + K1 * (1 - B + B * (item.length / Math.max(1, averageLength)));
          return total + idf * ((frequency * (K1 + 1)) / denominator);
        }, 0);
        return { id: item.doc.id, score };
      })
      .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
      .slice(0, k);

    return {
      id: row.id,
      retrieved_ids: ranked.map((item) => item.id),
      score: ranked[0]?.score ?? 0,
    };
  });
}
