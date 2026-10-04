import type { Novelty, NoveltyStatus } from "../types";

/** What a novelty check that could not be completed says instead of a score. */
export const NOT_ASSESSED = "Not assessed";

const REASON: Record<Exclude<NoveltyStatus, "assessed">, string> = {
  no_candidates: "No eligible literature candidates were available for this check.",
  rerank_failed: "The literature assessment could not be completed. Retry the check.",
  retrieval_failed: "The literature assessment could not be completed. Retry the check.",
};

type NoveltyLike = Pick<Novelty, "novelty"> & { status?: NoveltyStatus | string; reason?: string };

/** A novelty value that may be used as a score: a completed check with a number. Old exports carry no status;
 * their numbers were screened when exporting (crux_lab/export.py normalize_run), so a number alone counts. */
export function assessedNovelty(n: NoveltyLike | null | undefined): number | null {
  if (!n || n.novelty === null || n.novelty === undefined || Number.isNaN(n.novelty)) return null;
  if (n.status && n.status !== "assessed") return null;
  return n.novelty;
}

export function notAssessedReason(n: NoveltyLike | null | undefined): string {
  if (n?.reason) return n.reason;
  const s = n?.status as keyof typeof REASON | undefined;
  return (s && REASON[s]) || "The literature assessment could not be completed. Retry the check.";
}

/** "Defender B" for "defender_b". */
function defenderName(id: string): string {
  return id === "defender_a" ? "Defender A" : id === "defender_b" ? "Defender B" : id;
}

/** The sentence a failed trial shows. */
export function trialFailure(t: { error?: string | null; missing_labels?: string[] }): string {
  const m = t.missing_labels ?? [];
  if (m.length)
    return m.length > 1
      ? `Trial incomplete: the referee assessments for ${m.map(defenderName).join(" and ")} are unavailable.`
      : `Trial incomplete: the referee assessment for ${defenderName(m[0])} is unavailable.`;
  return `Trial failed${t.error ? `: ${t.error}` : "."}`;
}
