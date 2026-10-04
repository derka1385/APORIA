// Data contract for web/public/data/*.json, written by crux_lab/export.py.
// Mirrors crux_lab/graph/schema.py. Keep in sync with tests/test_export.py.

export type Outcome = "misreading" | "known_answer" | "rebutted" | "revision_required" | "standing";
export type ClaimKind = "premise" | "conclusion" | "assumption" | "objection" | "reply" | "open_question";

export interface Claim {
  id: string;
  paper_id: string;
  kind: ClaimKind;
  text: string;
  quote: string;
  level: "fulltext" | "abstract" | "generated";
  work?: string; // canonical id of the work (duplicate OpenAlex records of one paper share it)
}

export interface Argument {
  id: string;
  paper_id: string;
  title: string;
  premise_ids: string[];
  conclusion_id: string;
  skeleton: string; // "f1; f2; ... |- c" (premise formulas in premise_ids order)
  atoms: Record<string, string>;
  valid: boolean | null;
  missing_premise: string | null; // "text [formula]"
  missing_premise_id: string | null;
}

export interface Edge {
  src: string;
  dst: string;
  relation: "supports" | "attacks" | "replies_to" | "same_move" | "presupposes";
}

export interface Objection {
  id: string;
  argument_id: string;
  target_premise_id: string;
  kind: string; // thought_experiment | hidden_premise | tradition | naive_sharpened
  text: string;
  agent: string; // blind_thought_experimenter | hidden_premise_attacker | tradition_lens | naive_questioner+sharpener
  model: string;
  family: string;
  depth: number;
  tradition: string | null;
  premise_fails_because: string;
}

export interface NearestMatch {
  record_id: string; // claim id, "abs:<paper_id>" or "live:<paper_id>"
  paper_id: string;
  verdict: "same_move" | "related" | "different";
  similarity: number;
  quote: string;
  title: string;
}

/** "assessed", or why the check could not be completed (crux_lab/lab/novelty.py). Absent on old exports. */
export type NoveltyStatus = "assessed" | "no_candidates" | "rerank_failed" | "retrieval_failed";

export interface Novelty {
  objection_id: string;
  restatements: { paper_vocabulary?: string; plain_english?: string; neighboring_tradition?: string };
  novelty: number | null; // null = not assessed: never a score
  status?: NoveltyStatus;
  reason?: string;
  legacy_novelty?: number; // a stored number the export found to come from a failure path; never shown as a score
  records_searched: number;
  reranked: number;
  live_openalex: string;
  nearest: NearestMatch[];
  matches: NearestMatch[];
}

export interface Turn {
  exchange: number; // 0 = pre-screen, 1 = Defender A exchange, 2 = Defender B exchange
  speaker: "defender_a" | "defender_b" | "attacker" | "referee";
  phase: "prescreen" | "reply" | "rejoinder" | "close" | "label";
  model: string;
  family: string;
  content: string;
  cited_claim_ids: string[];
  struck_claim_ids: string[];
  concedes: boolean;
  revised_premise: string | null;
}

export interface PerDefender {
  outcome: Outcome;
  rationale: string;
  deciding_quote: string;
  revised_premise: string | null;
  verified: string[];
  struck: string[];
  model: string;
  family: string;
}

export interface Trial {
  id: string; // "trial-<objection_id>"
  objection_id: string;
  rounds: Turn[];
  outcome: Outcome | null;
  rationale: string;
  deciding_quote: string;
  cited_claim_ids: string[];
  revised_premise: string | null;
  per_defender: Record<string, PerDefender>;
  status: "ok" | "failed";
  error: string | null;
  missing_labels?: string[]; // defenders the Referee could not label: the trial is incomplete
  legacy_outcome?: Outcome | null; // an outcome stored before the completeness check; not a result
  normalized_at_export?: boolean;
}

export interface QueueRow {
  objection_id: string;
  target_premise_id: string;
  agent: string;
  family: string;
  depth: number;
  S: number;
  N: number;
  C: number;
  E: number;
  priority: number;
}

export interface DirectorStep {
  step: number;
  queue: QueueRow[];
  picked: string[];
  note: string;
}

export type RunEvent =
  | { t: number; type: "run_start"; run_id: string; target: string; argument_id: string }
  | { t: number; type: "objection"; objection: Objection }
  | { t: number; type: "naive_question"; question: string; sharpened: boolean }
  | {
      t: number;
      type: "novelty";
      objection_id: string;
      novelty: number | null;
      status?: NoveltyStatus;
      reason?: string;
      records_searched: number;
      nearest: NearestMatch[];
    }
  | { t: number; type: "queue"; step: number; queue: QueueRow[]; picked: string[] }
  | { t: number; type: "trial_start"; trial_id: string; objection_id: string }
  | { t: number; type: "turn"; turn: Turn; trial_id?: string; objection_id?: string }
  | {
      t: number;
      type: "trial_end";
      trial_id: string;
      objection_id: string;
      outcome: Outcome | null;
      status: string;
      error?: string | null;
      missing_labels?: string[];
    }
  | { t: number; type: "revised_premise"; id: string; text: string; from_trial: string }
  | { t: number; type: "brief"; brief_id: string; objection_id: string }
  | { t: number; type: "run_end"; stop_reason: string };

export interface Target {
  id: string;
  paper_id: string;
  kind: "fresh" | "classic" | "manual";
  title: string;
  authors?: string[];
  year?: number | null;
  published?: string | null;
  url?: string;
  thesis?: string;
  reason: string;
}

export interface Run {
  run_id: string;
  target: Target;
  started_at: string;
  finished_at: string;
  stop_reason: string;
  argument: Argument;
  claims: Record<string, Claim>; // this paper's claims incl. missing premise (".mp") and revised (".rN")
  revised_premises: Record<string, string>;
  dependence: Record<string, number>;
  objections: Objection[];
  novelty: Record<string, Novelty>;
  trials: Trial[];
  director_steps: DirectorStep[];
  briefs: string[];
  naive_questioner: { question?: string; sharpened?: string | null; error?: string }[];
  families_used: string[];
  models: Record<string, string>; // role -> "family:model"
  generators: string[];
  diversity: string;
  events: RunEvent[];
}

export interface RunSummary {
  run_id: string;
  target_id: string;
  kind: string;
  title: string;
  paper_id: string;
  argument_title: string;
  objections: number;
  trials: number;
  outcomes: Partial<Record<Outcome | "failed", number>>;
  briefs: string[];
  families: string[];
  stop_reason: string;
  finished_at: string;
}

export interface Index {
  generated_at: string;
  runs: RunSummary[];
  targets: Target[];
  briefs: number;
  trials: number;
  objections: number;
  headline: { label: string; value: string; source: string }[];
}

export interface LiteratureRef {
  record_id: string;
  paper_id?: string;
  title?: string;
  authors?: string[];
  year?: number | null;
  url?: string;
  verdict?: string;
  similarity?: number;
  quote?: string;
}

export type QualityGrade = "promising" | "needs work" | "not yet defensible";

export interface Assessment {
  grade: QualityGrade;
  overall: number;
  scores: { coherence: number; robustness: number; significance: number; specificity: number };
  reasons?: Record<string, string>;
  strongest_objection?: string;
  reply_available?: boolean;
  what_it_needs?: string;
  summary: string;
  model?: string;
  assessed_at?: string;
}

export interface Revision {
  research_question: string;
  paper_direction: string;
  reply_to_strongest_objection: string;
  what_changed: string;
  narrowed: boolean;
  model?: string;
  revised_at?: string;
  assessment?: Assessment | null;
}

export interface Brief {
  id: string;
  objection_id: string;
  research_question: string;
  argument: {
    id: string;
    title: string;
    paper_id: string;
    paper_title: string;
    premises: { id: string; text: string; quote: string }[];
    missing_premise: { id: string; text: string } | null;
    conclusion: { id: string; text: string };
    skeleton: string;
    valid: boolean | null;
  };
  challenged_premise: { id: string; text: string };
  objection: string;
  strongest_responses: { defender: string; response: string; why_it_failed: string }[];
  closest_literature: LiteratureRef[];
  novelty: number | null; // null only for a diagnostic brief whose novelty was not assessed
  records_searched: number;
  nearest: NearestMatch[];
  open_questions: string[];
  paper_direction: string;
  outcome: Outcome | "";
  assessment?: Assessment | null;
  revision?: Revision | null;
  disclaimer: string;
}

export interface BriefSummary {
  id: string;
  run_id: string | null;
  research_question: string;
  outcome: Outcome | "";
  novelty: number;
  records_searched: number;
  survival: number;
  paper_title: string;
  challenged_premise: { id: string; text: string };
  paper_direction: string;
  score?: number; // lead score: survival x novelty x quality (crux_lab/export.py rank_directions)
  quality?: number | null; // the Assessor's latest overall score / 5; null when not graded
  tier?: number; // 0 = best direction for its target paper, 1 = second, ...
  assessment?: Pick<Assessment, "grade" | "overall" | "scores" | "summary"> | null;
  revision?: {
    research_question: string;
    paper_direction?: string;
    assessment: Pick<Assessment, "grade" | "overall" | "scores" | "summary"> | null;
  } | null;
}

export interface CorpusRecord {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  url: string;
  venue: string | null;
  abstract: string;
  source: string;
  fresh: boolean;
  published: string | null;
}

/** titles.json: slim index used by /atlas (records.json carries the full record). */
export interface TitleRecord {
  id: string;
  title: string;
  year: number | null;
}

export interface ClaimsFile {
  claims: Claim[];
  arguments: Argument[];
  edges: Edge[];
}

export interface ResultsFile {
  e1: E1 | null;
  e2: E2 | null;
  e3: E3 | null;
}

export interface E1 {
  experiment?: string;
  n: number;
  methods: { name: string; recall_at_5: number; hits: number; recall_at_5_strict_record?: number }[];
  unit?: string;
  previous_runs?: { timestamp: string; unit: string; methods: { name: string; recall_at_5: number }[] }[];
  settings: Record<string, unknown>;
  models: Record<string, string>;
  timestamp: string;
  limits: string;
}

export interface E2 {
  experiment?: string;
  n?: number;
  known_answer: {
    n: number;
    labelled_known_answer: number;
    correct_reply_cited: number;
    gold_reply_cited_by_a_defender?: number;
  };
  misreading: { n: number; caught: number };
  items: {
    kind: string;
    source_paper: string;
    outcome: string | null;
    correct: boolean;
    objection?: string;
    objection_paper?: string;
    reply_claims?: string[];
    target?: string;
    cited?: string[];
    status?: string;
  }[];
  settings: Record<string, unknown>;
  models: Record<string, string>;
  timestamp: string;
  limits: string;
}

export interface E3 {
  experiment?: string;
  conditions: {
    name: string;
    n: number;
    distinct_premises: number;
    mean_pairwise_distance: number;
    share_surviving: number | null;
    share_passing_prescreen?: number | null;
    share_novelty_gt_05: number | null; // over completed novelty checks; null if none completed
    novelty_assessed?: number;
    novelty_unavailable?: number;
  }[];
  settings: Record<string, unknown>;
  models: Record<string, string>;
  timestamp: string;
  limits: string;
}

export interface About {
  topic?: { slug: string; name: string; description: string; area: string };
  diversity: string;
  families: string[];
  roles: Record<string, unknown>;
  models: { provider: string; model: string; family: string; ok: boolean }[];
  targets_meta: Record<string, unknown>;
  map_stats: Record<string, unknown>;
  corpus: {
    records: number;
    distinct_works?: number;
    with_abstract: number;
    full_texts: number;
    fresh: number;
    searches?: string[];
    fresh_from?: string;
  };
  method_notes?: string[];
  tracing?: { backend: string; traces: number | null };
}

export const OUTCOME_COLORS: Record<Outcome, string> = {
  misreading: "#808A94",
  known_answer: "#A9C8FF",
  rebutted: "#5FD4C4",
  revision_required: "#E2A85A",
  standing: "#FF6B4F",
};

/** Darker shades for text set in an outcome colour (contrast >= 4.5:1 on paper). */
export const OUTCOME_TEXT_COLORS: Record<Outcome, string> = {
  misreading: "#9AA3AC",
  known_answer: "#A9C8FF",
  rebutted: "#5FD4C4",
  revision_required: "#E2A85A",
  standing: "#FF8A72",
};

export const OUTCOME_LABELS: Record<Outcome, string> = {
  misreading: "Misreading",
  known_answer: "Known answer",
  rebutted: "Rebutted",
  revision_required: "Revision required",
  standing: "Standing",
};

/** topics.json (site-wide): every configured topic, written by crux_lab/export.py on every export. */
export interface TopicConfig {
  slug: string;
  name: string;
  description: string;
  area: string;
  queries: Record<string, string>;
  fresh_from: string;
  fresh_queries: string[];
  relevant: string;
  relevance_levels: string[];
  schools: string[];
}

export interface TopicInfo {
  slug: string;
  name: string;
  description: string;
  area: string;
  default: boolean;
  status: "ready" | "not_run";
  data: string; // "" for the default topic, "topics/<slug>/" otherwise
  counts: { papers: number; objections: number; trials: number; briefs: number; records?: number; works?: number } | null;
  searches: string[];
  schools: string[];
  families?: string[] | null; // model families its runs used (from its about.json)
  lead?: { id: string; question: string; score?: number; outcome: string; novelty: number; quality?: number | null } | null;
  config_path: string;
  commands: string[];
  config: TopicConfig;
}

export interface TopicsFile {
  default: string;
  current_export: string;
  topics: TopicInfo[];
}
