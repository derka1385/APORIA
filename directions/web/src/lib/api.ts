// Live mode is optional. Static replay of exported files is the default and needs no API.
const raw = import.meta.env.VITE_API_URL;
export const API_URL: string | null = raw ? raw.replace(/\/+$/, "") : null;

export interface PriorArtHit {
  claim_id: string;
  text: string;
  score: number;
  title?: string;
  paper_id?: string;
  [k: string]: unknown;
}

export async function livePriorArt(q: string): Promise<{ records_searched: number; hits: PriorArtHit[] }> {
  if (!API_URL) throw new Error("live API not configured");
  const r = await fetch(`${API_URL}/api/prior-art?q=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error(`prior-art API answered ${r.status}`);
  return r.json();
}

export function liveRunURL(targetId: string): string | null {
  return API_URL ? `${API_URL}/api/run?target=${encodeURIComponent(targetId)}` : null;
}
