import type { CorpusRecord } from "../types";

/** Claim ids look like "W2072673546.c004" (full text) or "W2072673546.a1" (abstract). */
export function claimPaperShort(claimId: string): string {
  return claimId.split(".", 1)[0];
}

/** Record ids from prior-art search may be "abs:<paper_id>" or "live:<paper_id>". */
export function stripRecordPrefix(recordId: string): string {
  return recordId.replace(/^(abs|live):/, "");
}

/** Find the corpus record a claim id (or paper id) belongs to. Records are keyed by full paper id ("oa:W..."). */
export function recordFor<T = CorpusRecord>(
  idOrPaper: string,
  records: Record<string, T> | undefined,
): T | undefined {
  if (!records) return undefined;
  if (records[idOrPaper]) return records[idOrPaper];
  const stripped = stripRecordPrefix(idOrPaper);
  if (records[stripped]) return records[stripped];
  const short = claimPaperShort(stripped).split(":").pop() ?? stripped;
  for (const key of Object.keys(records)) {
    if (key === short || key.endsWith(`:${short}`)) return records[key];
  }
  return undefined;
}

/** "trial-W72.arg1.oab12cd" -> "W72" (the target paper's short id), used to guess which run holds a trial. */
export function trialPaperShort(trialId: string): string {
  return trialId.replace(/^trial-/, "").split(".", 1)[0];
}

export function paperShort(paperId: string): string {
  return paperId.split(":").pop() ?? paperId;
}
