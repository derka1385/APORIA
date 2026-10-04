import { useEffect, useState } from "react";

// Every file the site reads lives under public/data and is written by crux_lab/export.py.
// VITE_DATA_DIR lets the site share a host with other data (APORIA serves its own docs/data/).
const BASE = `${import.meta.env.BASE_URL}${import.meta.env.VITE_DATA_DIR ?? "data"}/`;

export class MissingDataError extends Error {
  path: string;
  constructor(path: string) {
    super(`data/${path} has not been exported`);
    this.path = path;
  }
}

const cache = new Map<string, Promise<unknown>>();

// Topic data lives in a sub-folder (e.g. "topics/fine-tuning/"); the default topic sits at data/ itself.
// Set once at boot (src/lib/topics.ts); switching topic reloads the app. topics.json is always site-wide.
let TOPIC_PREFIX = "";
const SITE_WIDE = new Set(["topics.json"]);
export function setTopicPrefix(prefix: string) {
  TOPIC_PREFIX = prefix;
}
const url = (path: string) => BASE + (SITE_WIDE.has(path) ? "" : TOPIC_PREFIX) + path;

async function get(path: string): Promise<Response> {
  const r = await fetch(url(path));
  const ct = r.headers.get("content-type") ?? "";
  // An SPA fallback answers missing files with index.html; treat that as missing too.
  if (!r.ok || ct.includes("text/html")) throw new MissingDataError(path);
  return r;
}

export function fetchJSON<T>(path: string): Promise<T> {
  const key = url(path);
  let p = cache.get(key);
  if (!p) {
    p = get(path).then(async (r) => {
      try {
        return await r.json();
      } catch {
        throw new MissingDataError(path);
      }
    });
    p.catch(() => cache.delete(key));
    cache.set(key, p);
  }
  return p as Promise<T>;
}

export async function fetchText(path: string): Promise<string> {
  const r = await get(path);
  return r.text();
}

export type Load<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "missing"; path: string }
  | { status: "error"; error: string };

export function useJSON<T>(path: string | null): Load<T> {
  const [state, setState] = useState<{ path: string | null; load: Load<T> }>({
    path: null,
    load: { status: "loading" },
  });
  useEffect(() => {
    if (!path) return;
    let alive = true;
    fetchJSON<T>(path).then(
      (data) => alive && setState({ path, load: { status: "ready", data } }),
      (e: unknown) =>
        alive &&
        setState({
          path,
          load: e instanceof MissingDataError ? { status: "missing", path } : { status: "error", error: String(e) },
        }),
    );
    return () => {
      alive = false;
    };
  }, [path]);
  if (!path || state.path !== path) return { status: "loading" };
  return state.load;
}

export function dataUrl(path: string): string {
  return BASE + path;
}
