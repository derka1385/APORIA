// The discovery loop, drawn as a ring. Stage names are the method's vocabulary, not data.
export const STAGES: { name: string; note: string }[] = [
  { name: "corpus", note: "papers and abstracts" },
  { name: "argument graph", note: "premises, quotes, formal skeleton" },
  { name: "objections", note: "blind agents, one premise each" },
  { name: "gauntlet", note: "two defenders, one referee" },
  { name: "prior-art check", note: "has this move been made?" },
  { name: "Director", note: "plain code picks the next trial" },
  { name: "brief", note: "for a human philosopher" },
];

export function LoopRing({ className = "" }: { className?: string }) {
  const cx = 250;
  const cy = 230;
  const r = 150;
  const n = STAGES.length;
  const ang = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
  const pt = (a: number, rr = r) => [cx + rr * Math.cos(a), cy + rr * Math.sin(a)] as const;
  const gap = 0.16;
  return (
    <svg
      viewBox="-10 25 530 395"
      className={className}
      role="img"
      aria-labelledby="loop-title loop-desc"
    >
      <title id="loop-title">The Crux Lab discovery loop</title>
      <desc id="loop-desc">{STAGES.map((s) => s.name).join(", then ")}, then back to the corpus.</desc>
      <defs>
        <marker id="loop-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="#F4F1E9" strokeWidth="1.4" />
        </marker>
      </defs>
      <circle cx={cx} cy={cy} r={r - 34} fill="none" stroke="#353B42" strokeWidth="1" strokeDasharray="2 5" />
      {STAGES.map((_, i) => {
        const [x1, y1] = pt(ang(i) + gap);
        const [x2, y2] = pt(ang(i + 1) - gap);
        return (
          <path
            key={`arc-${i}`}
            d={`M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`}
            fill="none"
            stroke="#F4F1E9"
            strokeWidth="1.1"
            markerEnd="url(#loop-arrow)"
          />
        );
      })}
      {STAGES.map((s, i) => {
        const a = ang(i);
        const [x, y] = pt(a);
        const [lx, ly] = pt(a, r + 22);
        const c = Math.cos(a);
        const anchor = Math.abs(c) < 0.2 ? "middle" : c > 0 ? "start" : "end";
        const dy = Math.sin(a) < -0.9 ? -12 : Math.sin(a) > 0.6 ? 14 : 0;
        const accent = s.name === "gauntlet";
        return (
          <g key={s.name}>
            <circle cx={x} cy={y} r={accent ? 7 : 5} fill={accent ? "#F4F1E9" : "#121416"} stroke="#F4F1E9" strokeWidth="1.4" />
            <text x={lx} y={ly + dy} textAnchor={anchor} dominantBaseline="middle" fontFamily="Newsreader, Georgia, serif" fontSize="17" fill="#F4F1E9">
              {s.name}
            </text>
          </g>
        );
      })}
      <text x={cx} y={cy - 6} textAnchor="middle" fontFamily="Newsreader, Georgia, serif" fontStyle="italic" fontSize="17" fill="#F4F1E9">
        in philosophy,
      </text>
      <text x={cx} y={cy + 16} textAnchor="middle" fontFamily="Newsreader, Georgia, serif" fontStyle="italic" fontSize="17" fill="#F4F1E9">
        the debate is the experiment
      </text>
    </svg>
  );
}
