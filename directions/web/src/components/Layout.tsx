import { Suspense, useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { currentTopic } from "../lib/topics";
import { DrawerProvider } from "./drawer";

const NAV: { to: string; label: string }[] = [
  { to: "/topics", label: "Topics" },
  { to: "/briefs", label: "Directions" },
  { to: "/runs", label: "Runs" },
  { to: "/atlas", label: "Atlas" },
  { to: "/results", label: "Results" },
  { to: "/about", label: "About" },
];

/** APORIA's home page: this app is served from <APORIA>/directions/. */
const APORIA_HOME = import.meta.env.BASE_URL.replace(/directions\/?$/, "");

/** APORIA's mark: three open concentric arcs. */
function ApoMark() {
  return (
    <svg viewBox="0 0 128 128" aria-hidden="true" className="h-[22px] w-[22px]">
      <g fill="none" stroke="currentColor" strokeWidth="8">
        <path d="M108.184 45.245 A48 48 0 1 1 64.838 16.007" />
        <path d="M93.875 75.468 A32 32 0 1 1 86.627 41.373" />
        <path d="M70.762 78.501 A16 16 0 1 1 79.998 63.721" />
      </g>
    </svg>
  );
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export function Layout() {
  return (
    <DrawerProvider>
      <ScrollToTop />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:bg-paper focus:px-3 focus:py-2 focus:outline"
      >
        Skip to content
      </a>
      <header className="no-print sticky top-0 z-30 border-b border-rule bg-[rgba(18,20,22,0.92)] backdrop-blur-[6px]">
        <div className="mx-auto flex min-h-14 max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2 sm:px-6">
          <a href={APORIA_HOME} className="flex items-center gap-2.5 font-sans text-[15px] font-semibold tracking-[0.11em] no-underline">
            <ApoMark />
            APORIA
          </a>
          <NavLink to="/" end className="font-mono text-[0.75rem] text-ink-soft no-underline hover:text-ink">
            research directions
          </NavLink>
          {currentTopic() ? (
            <NavLink to="/topics" className="font-mono text-[0.72rem] text-ink-faint underline decoration-rule underline-offset-4 hover:decoration-ink" title="Change topic">
              topic: {currentTopic()!.name}
            </NavLink>
          ) : null}
          <nav aria-label="Main" className="ml-auto">
            <ul className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-[13px]">
              {NAV.map((n) => (
                <li key={n.to}>
                  <NavLink
                    to={n.to}
                    className={({ isActive }) =>
                      `no-underline hover:text-ink ${isActive ? "text-ink underline decoration-ink underline-offset-[6px]" : "text-ink-soft"}`
                    }
                  >
                    {n.label}
                  </NavLink>
                </li>
              ))}
              <li>
                <a href={`${APORIA_HOME}lab/`} className="text-ink-soft no-underline hover:text-ink">
                  Reasoners
                </a>
              </li>
              <li>
                <a href={`${APORIA_HOME}divergence/`} className="text-ink-soft no-underline hover:text-ink">
                  Divergence
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main id="main" className="min-h-[70vh]">
        <Suspense
          fallback={
            <p className="mx-auto max-w-[1400px] px-6 py-10 font-mono text-sm text-ink-soft" aria-live="polite">
              Opening the notebook…
            </p>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <footer className="no-print mt-20 border-t border-rule">
        <div className="mx-auto flex max-w-[1400px] flex-wrap justify-between gap-4 px-4 pb-16 pt-10 font-mono text-[13px] text-ink-faint sm:px-6">
          <p>APORIA · research directions. Every number on this site is read from files the lab generated.</p>
          <p>The Referee labels dialectical status, never the truth of a conclusion.</p>
        </div>
      </footer>
    </DrawerProvider>
  );
}
