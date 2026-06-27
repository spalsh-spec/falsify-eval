export function createRng(seed: number): () => number {
  let state = (seed >>> 0) || 1;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

export function sampleIndex(rng: () => number, length: number): number {
  return Math.min(length - 1, Math.floor(rng() * length));
}

export function shuffle<T>(items: readonly T[], seed: number): T[] {
  const out = [...items];
  const rng = createRng(seed);
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rng() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
