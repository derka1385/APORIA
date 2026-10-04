import { describe, expect, it } from "vitest";
import { BM25, tokenize } from "../bm25";

describe("tokenize", () => {
  it("drops stopwords and short tokens, applies the same light stemming to queries and documents", () => {
    expect(tokenize("The objections of a loving God")).toEqual(["objection", "lov", "god"]);
    expect(tokenize("objection objections")).toEqual(["objection", "objection"]);
    expect(tokenize("believe believes")).toEqual(["believe", "believe"]);
  });
});

describe("BM25", () => {
  const docs = [
    "A perfectly loving God would not permit nonresistant nonbelief.",
    "Bananas are rich in potassium.",
    "Divine hiddenness may serve the good of free choice.",
  ];
  const ix = new BM25(docs);

  it("ranks the matching document first and ignores non-matches", () => {
    const hits = ix.search("loving God nonbelief");
    expect(hits[0].index).toBe(0);
    expect(hits.find((h) => h.index === 1)).toBeUndefined();
  });

  it("returns nothing for stopword-only or empty queries", () => {
    expect(ix.search("the and of")).toEqual([]);
    expect(new BM25([]).search("god")).toEqual([]);
  });
});
