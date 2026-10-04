// Small client-side BM25 (Okapi) for "Has this move been made?" in static mode.

const STOPWORDS = new Set(
  (
    "a about above after again against all also am an and any are as at be because been before being below " +
    "between both but by can could did do does doing down during each either else ever every few for from " +
    "further had has have having he her here hers herself him himself his how however i if in into is it its " +
    "itself just may me might more most must my myself neither no nor not now of off on once one only or other " +
    "ought our ours ourselves out over own same shall she should so some such than that the their theirs them " +
    "themselves then there these they this those through thus to too under until up upon us very was we were " +
    "what when where whether which while who whom whose why will with within without would yet you your yours " +
    "yourself yourselves s t don isn doesn wasn aren weren cannot"
  ).split(/\s+/),
);

/** Very light suffix stripping so "objections"/"objection" and "believes"/"believe" meet. */
function stem(w: string): string {
  if (w.length > 5 && w.endsWith("ies")) return `${w.slice(0, -3)}y`;
  if (w.length > 5 && w.endsWith("ing")) return w.slice(0, -3);
  if (w.length > 4 && w.endsWith("ed")) return w.slice(0, -2);
  if (w.length > 4 && w.endsWith("es") && !w.endsWith("ses")) return w.slice(0, -1);
  if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss") && !w.endsWith("us") && !w.endsWith("is")) return w.slice(0, -1);
  return w;
}

export function tokenize(text: string): string[] {
  const out: string[] = [];
  for (const raw of text.toLowerCase().normalize("NFKD").split(/[^\p{L}\p{N}]+/u)) {
    if (!raw || raw.length < 2 || STOPWORDS.has(raw)) continue;
    out.push(stem(raw));
  }
  return out;
}

export interface BM25Hit {
  index: number;
  score: number;
}

export class BM25 {
  private readonly k1: number;
  private readonly b: number;
  private readonly docLen: number[] = [];
  private readonly tf: Map<string, number>[] = [];
  private readonly df = new Map<string, number>();
  private avgdl = 0;
  readonly size: number;

  constructor(docs: string[], k1 = 1.5, b = 0.75) {
    this.k1 = k1;
    this.b = b;
    let total = 0;
    for (const d of docs) {
      const toks = tokenize(d);
      const m = new Map<string, number>();
      for (const t of toks) m.set(t, (m.get(t) ?? 0) + 1);
      for (const t of m.keys()) this.df.set(t, (this.df.get(t) ?? 0) + 1);
      this.tf.push(m);
      this.docLen.push(toks.length);
      total += toks.length;
    }
    this.size = docs.length;
    this.avgdl = docs.length ? total / docs.length : 0;
  }

  private idf(term: string): number {
    const n = this.df.get(term) ?? 0;
    return Math.log(1 + (this.size - n + 0.5) / (n + 0.5));
  }

  search(query: string, k = 10): BM25Hit[] {
    const terms = [...new Set(tokenize(query))];
    if (!terms.length || !this.size) return [];
    const scores: BM25Hit[] = [];
    for (let i = 0; i < this.size; i++) {
      const m = this.tf[i];
      let s = 0;
      for (const t of terms) {
        const f = m.get(t);
        if (!f) continue;
        const norm = this.k1 * (1 - this.b + (this.b * this.docLen[i]) / (this.avgdl || 1));
        s += this.idf(t) * ((f * (this.k1 + 1)) / (f + norm));
      }
      if (s > 0) scores.push({ index: i, score: s });
    }
    scores.sort((a, b) => b.score - a.score);
    return scores.slice(0, k);
  }
}
