import type { TopicInfo, TopicsFile } from "../types";
import { fetchJSON, setTopicPrefix } from "./data";

// Which topic's data the site shows. Chosen by ?topic=<slug> (shareable) or remembered for the session;
// only topics that have been run and exported can be shown. Resolved once, before the first render.
const KEY = "crux-lab-topic";
let current: TopicInfo | null = null;
let all: TopicsFile | null = null;

function remembered(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export async function bootTopic(): Promise<void> {
  const requested = new URLSearchParams(window.location.search).get("topic") ?? remembered();
  try {
    all = await fetchJSON<TopicsFile>("topics.json");
  } catch {
    all = null; // older export without topics.json: the default data at data/ is used
    return;
  }
  const ready = all.topics.filter((t) => t.status === "ready");
  current =
    ready.find((t) => t.slug === requested) ?? ready.find((t) => t.slug === all!.default) ?? ready[0] ?? null;
  if (current) {
    setTopicPrefix(current.data);
    try {
      sessionStorage.setItem(KEY, current.slug); // a shared ?topic= link keeps its topic across reloads
    } catch {
      /* storage unavailable: the URL parameter still works for this load */
    }
  }
}

export function currentTopic(): TopicInfo | null {
  return current;
}

export function topicsFile(): TopicsFile | null {
  return all;
}

/** Switch the whole site to another topic (reloads, so every page reads that topic's files). */
export function switchTopic(slug: string) {
  try {
    sessionStorage.setItem(KEY, slug);
  } catch {
    /* private mode: the ?topic= parameter still carries it */
  }
  window.location.assign(`${import.meta.env.BASE_URL}?topic=${encodeURIComponent(slug)}`);
}
