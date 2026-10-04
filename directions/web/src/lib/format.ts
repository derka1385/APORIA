// Display vocabulary only. No data values live here.

export function num(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

export function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)}%`;
}

export function when(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export const SPEAKER_LABEL: Record<string, string> = {
  defender_a: "Defender A",
  defender_b: "Defender B",
  attacker: "Objector",
  referee: "Referee",
};

export const PHASE_LABEL: Record<string, string> = {
  prescreen: "pre-screen",
  reply: "reply",
  rejoinder: "rejoinder",
  close: "closing reply",
  label: "label",
};

const AGENT_LABEL: Record<string, string> = {
  blind_thought_experimenter: "Blind Thought-Experimenter",
  hidden_premise_attacker: "Hidden-Premise Attacker",
  tradition_lens: "Tradition Lens",
  naive_questioner: "Naive Questioner",
  "naive_questioner+sharpener": "Naive Questioner, sharpened",
  defender_a: "Defender A",
  defender_b: "Defender B",
  referee: "Referee",
  extractor: "Extractor",
  formalizer: "Formalizer",
  reranker: "Prior-Art Reranker",
  generators: "Objection generators",
};

export function agentLabel(agent: string | null | undefined): string {
  if (!agent) return "—";
  if (AGENT_LABEL[agent]) return AGENT_LABEL[agent];
  const s = agent.replace(/[_+]/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function speakerLabel(s: string): string {
  return SPEAKER_LABEL[s] ?? agentLabel(s);
}

/** The part of a claim/objection id after the paper prefix: "W72.c006" -> "c006", "W72.arg1.mp" -> "arg1.mp". */
export function shortId(id: string): string {
  const i = id.indexOf(".");
  return i >= 0 ? id.slice(i + 1) : id;
}

export function excerpt(text: string | null | undefined, max = 280): string {
  if (!text) return "";
  const t = text.trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  const sp = cut.lastIndexOf(" ");
  return `${cut.slice(0, sp > max * 0.6 ? sp : max)}…`;
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const SMALL_WORDS = new Set(["a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "nor", "of", "on", "or", "the", "to", "upon", "via"]);

/** Some source titles arrive in all capitals; set those in title case for reading. Others are left as given. */
export function displayTitle(t: string | null | undefined): string {
  if (!t) return "";
  if (/\p{Ll}/u.test(t)) return t;
  let first = true;
  return t
    .toLowerCase()
    .split(/(\s+)/)
    .map((w) => {
      if (/^\s+$/.test(w) || !w) return w;
      const keepSmall = !first && SMALL_WORDS.has(w);
      first = false;
      return keepSmall ? w : w.charAt(0).toUpperCase() + w.slice(1);
    })
    .join("");
}
