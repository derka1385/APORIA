import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { fetchJSON, MissingDataError } from "../lib/data";
import { recordFor } from "../lib/ids";
import type { Claim, ClaimsFile, CorpusRecord } from "../types";
import { Code, Label } from "./ui";

type Target =
  | { kind: "claim"; id: string; local?: Claim }
  | { kind: "record"; paperId: string; quote?: string; title?: string; recordId?: string };

interface DrawerApi {
  openClaim: (id: string, local?: Claim) => void;
  openRecord: (paperId: string, extra?: { quote?: string; title?: string; recordId?: string }) => void;
}

const Ctx = createContext<DrawerApi>({ openClaim: () => {}, openRecord: () => {} });

export function useDrawer(): DrawerApi {
  return useContext(Ctx);
}

export function DrawerProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<Target | null>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const openClaim = useCallback((id: string, local?: Claim) => {
    returnFocus.current = document.activeElement as HTMLElement | null;
    setTarget({ kind: "claim", id, local });
  }, []);
  const openRecord = useCallback((paperId: string, extra?: { quote?: string; title?: string; recordId?: string }) => {
    returnFocus.current = document.activeElement as HTMLElement | null;
    setTarget({ kind: "record", paperId, ...extra });
  }, []);
  const close = useCallback(() => {
    setTarget(null);
    returnFocus.current?.focus?.();
  }, []);
  const api = useMemo(() => ({ openClaim, openRecord }), [openClaim, openRecord]);
  return (
    <Ctx.Provider value={api}>
      {children}
      {target ? <Drawer key={target.kind === "claim" ? `c:${target.id}` : `r:${target.paperId}:${target.recordId ?? ""}`} target={target} onClose={close} /> : null}
    </Ctx.Provider>
  );
}

function Drawer({ target, onClose }: { target: Target; onClose: () => void }) {
  const closeBtn = useRef<HTMLButtonElement>(null);
  const [records, setRecords] = useState<Record<string, CorpusRecord> | null | "missing">(null);
  const [claim, setClaim] = useState<Claim | null | "missing" | "loading">(
    target.kind === "claim" ? target.local ?? "loading" : null,
  );

  useEffect(() => {
    closeBtn.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    let alive = true;
    fetchJSON<Record<string, CorpusRecord>>("records.json").then(
      (r) => alive && setRecords(r),
      () => alive && setRecords("missing"),
    );
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (target.kind !== "claim" || target.local) return;
    let alive = true;
    fetchJSON<ClaimsFile>("claims.json").then(
      (f) => alive && setClaim(f.claims.find((c) => c.id === target.id) ?? "missing"),
      (e) => alive && setClaim(e instanceof MissingDataError ? "missing" : "missing"),
    );
    return () => {
      alive = false;
    };
  }, [target]);

  const recs = records && records !== "missing" ? records : undefined;
  const paperKey =
    target.kind === "record"
      ? target.paperId
      : claim && typeof claim === "object"
        ? claim.paper_id
        : target.id;
  const record = recordFor(paperKey, recs) ?? (target.kind === "claim" ? recordFor(target.id, recs) : undefined);

  return (
    <div className="fixed inset-0 z-50 no-print" role="presentation">
      <div className="absolute inset-0 bg-ink/25" onClick={onClose} aria-hidden />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        className="absolute right-0 top-0 flex h-full w-full max-w-[34rem] flex-col border-l border-ink bg-paper shadow-[-8px_0_24px_rgba(31,27,22,0.12)]"
      >
        <div className="flex items-center justify-between border-b border-rule px-5 py-3">
          <Label>
            <span id="drawer-title">{target.kind === "claim" ? "Corpus claim" : "Corpus record"}</span>
          </Label>
          <button ref={closeBtn} className="btn btn-quiet" onClick={onClose}>
            Close <span className="text-ink-faint">esc</span>
          </button>
        </div>
        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          {target.kind === "claim" ? <ClaimBody id={target.id} claim={claim} /> : null}
          {target.kind === "record" && (target.quote || target.recordId) ? (
            <div className="space-y-2">
              {target.recordId ? (
                <div className="font-mono text-[0.75rem] text-ink-soft">record {target.recordId}</div>
              ) : null}
              {target.quote ? (
                <blockquote className="border-l-2 border-ink pl-3 italic leading-relaxed">“{target.quote}”</blockquote>
              ) : null}
            </div>
          ) : null}
          <RecordBody record={record} loading={records === null} fallbackTitle={target.kind === "record" ? target.title : undefined} />
        </div>
      </aside>
    </div>
  );
}

function ClaimBody({ id, claim }: { id: string; claim: Claim | null | "missing" | "loading" }) {
  if (claim === "loading" || claim === null)
    return <p className="font-mono text-sm text-ink-soft">Looking up {id}…</p>;
  if (claim === "missing")
    return (
      <div className="space-y-2">
        <div className="font-mono text-[0.8rem]">{id}</div>
        <p className="text-ink-soft">
          This id is not among the exported corpus claims. If it was cited in a trial it may have been struck by
          the Referee as unverifiable.
        </p>
      </div>
    );
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 font-mono text-[0.75rem] text-ink-soft">
        <span className="text-ink">{claim.id}</span>
        <span>· {claim.kind}</span>
        <span>· {claim.level === "fulltext" ? "from full text" : claim.level === "abstract" ? "from abstract" : "generated by the lab"}</span>
      </div>
      <p className="text-[1.08rem] leading-relaxed">{claim.text}</p>
      {claim.quote ? (
        <div>
          <Label className="mb-1">Verbatim quote from the source</Label>
          <blockquote className="border-l-2 border-ink pl-3 italic leading-relaxed">“{claim.quote}”</blockquote>
        </div>
      ) : claim.level === "generated" ? (
        <p className="text-[0.9rem] text-ink-soft">No quote: this premise was produced by the lab, not extracted from a paper.</p>
      ) : null}
    </div>
  );
}

function RecordBody({ record, loading, fallbackTitle }: { record?: CorpusRecord; loading: boolean; fallbackTitle?: string }) {
  if (loading) return <p className="font-mono text-sm text-ink-soft">Loading records…</p>;
  if (!record)
    return (
      <div className="border-t border-rule pt-4">
        <Label className="mb-1">Source record</Label>
        {fallbackTitle ? <p className="font-medium">{fallbackTitle}</p> : null}
        <p className="text-[0.92rem] text-ink-soft">
          No matching record in <Code>records.json</Code> (live search results and records outside the exported corpus
          are not included).
        </p>
      </div>
    );
  return (
    <div className="space-y-2 border-t border-rule pt-4">
      <Label>Source record</Label>
      <p className="text-[1.1rem] font-medium leading-snug">{record.title || "(untitled record)"}</p>
      <p className="text-[0.92rem] text-ink-soft">
        {[record.authors?.slice(0, 4).join(", "), record.year, record.venue].filter(Boolean).join(" · ")}
      </p>
      <div className="flex flex-wrap gap-x-3 font-mono text-[0.72rem] text-ink-faint">
        <span>{record.id}</span>
        {record.source ? <span>source: {record.source}</span> : null}
        {record.fresh ? <span>fresh{record.published ? `, published ${record.published}` : ""}</span> : null}
      </div>
      {record.url ? (
        <a className="link inline-block text-[0.95rem]" href={record.url} target="_blank" rel="noreferrer">
          Open the record ↗
        </a>
      ) : null}
      {record.abstract ? (
        <details className="pt-1">
          <summary className="cursor-pointer text-[0.92rem] text-ink-soft">Abstract</summary>
          <p className="mt-2 text-[0.95rem] leading-relaxed">{record.abstract}</p>
        </details>
      ) : null}
    </div>
  );
}
