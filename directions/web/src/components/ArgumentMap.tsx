import { useCallback, useEffect, useMemo, useState } from "react";
import {
  applyNodeChanges,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  useReactFlow,
  type Edge,
  type Node,
  type NodeChange,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Argument, Claim, Outcome } from "../types";
import { agentLabel, shortId } from "../lib/format";
import { OUTCOME_TEXT_COLORS } from "../types";
import { isOutcome, outcomeColor } from "./ui";

export interface MapObjection {
  id: string;
  target_premise_id: string;
  agent: string;
  family: string;
  outcome?: Outcome | "failed" | null;
  active?: boolean;
  index: number;
}

type PremiseData = {
  id: string;
  text: string;
  formula?: string;
  variant: "premise" | "missing" | "revised" | "conclusion";
};
type ObjectionData = { label: string; color: string; text: string; active: boolean; title: string };
type PremiseNode = Node<PremiseData, "premise">;
type ObjectionNode = Node<ObjectionData, "objection">;

const NODE_W = 190;
const hidden = { opacity: 0, width: 6, height: 6, minWidth: 0, minHeight: 0, border: 0 };

function PremiseBox({ data }: NodeProps<PremiseNode>) {
  const v = data.variant;
  const border =
    v === "missing"
      ? "2px dashed #E2A85A"
      : v === "revised"
        ? "1.5px dotted #E2A85A"
        : v === "conclusion"
          ? "1.5px solid #F4F1E9"
          : "1px solid #4A525B";
  const tag =
    v === "missing" ? "hidden premise" : v === "revised" ? "revised premise" : v === "conclusion" ? "conclusion" : "premise";
  return (
    <div
      className="cursor-pointer rounded-[2px] px-2.5 py-2 text-left"
      style={{ width: v === "conclusion" ? NODE_W + 60 : NODE_W, border, background: v === "conclusion" ? "#1B1F23" : "#1B1F23" }}
      title={data.text}
    >
      <Handle type="target" position={Position.Top} style={hidden} isConnectable={false} />
      <div className="mb-1 flex items-baseline justify-between gap-2 font-mono text-[10px] leading-none">
        <span style={{ color: v === "missing" || v === "revised" ? "#E2A85A" : "#B4BBC2" }}>{tag}</span>
        <span className="text-[#808A94]">
          {shortId(data.id)}
          {data.formula ? ` · ${data.formula}` : ""}
        </span>
      </div>
      <div className="line-clamp-4 font-serif text-[12.5px] leading-[1.3] text-ink">{data.text || "(text not exported)"}</div>
      <Handle type="source" position={Position.Bottom} style={hidden} isConnectable={false} />
    </div>
  );
}

function ObjectionDot({ data }: NodeProps<ObjectionNode>) {
  return (
    <div
      className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full font-serif text-[12px] italic"
      style={{
        // the outcome colour marks the ring; text uses its darker shade (>= 4.5:1), and an active dot is filled
        // with that shade so paper-coloured text stays readable
        border: `1.5px solid ${data.color}`,
        background: data.active ? data.text : "#1B1F23",
        color: data.active ? "#121416" : data.text,
      }}
      title={data.title}
    >
      {data.label}
      <Handle type="source" position={Position.Bottom} style={hidden} isConnectable={false} />
    </div>
  );
}

const nodeTypes = { premise: PremiseBox, objection: ObjectionDot };

export function premiseFormulas(arg: Argument): Record<string, string> {
  const out: Record<string, string> = {};
  const [lhs] = (arg.skeleton || "").split("|-");
  const parts = (lhs || "").split(";").map((s) => s.trim()).filter(Boolean);
  if (parts.length === arg.premise_ids.length) arg.premise_ids.forEach((id, i) => (out[id] = parts[i]));
  const rhs = (arg.skeleton || "").split("|-")[1]?.trim();
  if (rhs) out[arg.conclusion_id] = rhs;
  const m = arg.missing_premise?.match(/\[([^\]]+)\]\s*$/);
  if (m && arg.missing_premise_id) out[arg.missing_premise_id] = m[1];
  return out;
}

export function missingPremiseText(arg: Argument, claims: Record<string, Claim>): string {
  if (arg.missing_premise_id && claims[arg.missing_premise_id]) return claims[arg.missing_premise_id].text;
  return (arg.missing_premise ?? "").replace(/\s*\[[^\]]+\]\s*$/, "");
}

function Refit({ signature }: { signature: string }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const t = window.setTimeout(() => fitView({ padding: 0.12, duration: 250 }), 60);
    return () => window.clearTimeout(t);
  }, [signature, fitView]);
  return null;
}

export function ArgumentMap({
  argument,
  claims,
  revised = [],
  objections = [],
  height = 440,
  maxCols = 3,
  onSelectClaim,
  onSelectObjection,
}: {
  argument: Argument;
  claims: Record<string, Claim>;
  revised?: { id: string; text: string }[];
  objections?: MapObjection[];
  height?: number;
  maxCols?: number;
  onSelectClaim?: (id: string) => void;
  onSelectObjection?: (id: string) => void;
}) {
  const objKey = objections.map((o) => `${o.id}:${o.target_premise_id}:${o.outcome ?? ""}:${o.active ? 1 : 0}:${o.index}`).join("|");
  const revKey = revised.map((r) => r.id).join("|");
  const { nodes, edges } = useMemo(() => {
    const formulas = premiseFormulas(argument);
    const cols: PremiseData[] = argument.premise_ids.map((id) => ({
      id,
      text: claims[id]?.text ?? "",
      formula: formulas[id],
      variant: "premise" as const,
    }));
    if (argument.missing_premise_id || argument.missing_premise) {
      const id = argument.missing_premise_id ?? `${argument.id}.mp`;
      cols.push({ id, text: missingPremiseText(argument, claims), formula: formulas[id], variant: "missing" });
    }
    for (const r of revised) cols.push({ id: r.id, text: r.text, variant: "revised" });

    // Wrapped grid: premises in rows of `cols`, each row with a band above it for objection dots,
    // the conclusion centred below. Edges run behind the (opaque) boxes.
    const n = Math.max(1, cols.length);
    const perRow = Math.max(1, Math.min(maxCols, n));
    const COL = NODE_W + 34;
    const BAND = objections.length ? 64 : 24;
    const ROW = 112 + BAND;
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const xOf: Record<string, number> = {};
    const yOf: Record<string, number> = {};
    cols.forEach((c, i) => {
      const row = Math.floor(i / perRow);
      const inRow = Math.min(perRow, n - row * perRow);
      const offset = ((perRow - inRow) * COL) / 2;
      const x = offset + (i % perRow) * COL;
      const y = row * ROW + BAND;
      xOf[c.id] = x;
      yOf[c.id] = y;
      nodes.push({ id: c.id, type: "premise", position: { x, y }, data: c, draggable: false, connectable: false });
    });
    const rows = Math.ceil(n / perRow);
    const width = perRow * COL - 34;
    nodes.push({
      id: argument.conclusion_id,
      type: "premise",
      position: { x: width / 2 - (NODE_W + 60) / 2, y: rows * ROW + 40 },
      data: {
        id: argument.conclusion_id,
        text: claims[argument.conclusion_id]?.text ?? "",
        formula: formulas[argument.conclusion_id],
        variant: "conclusion",
      } satisfies PremiseData,
      draggable: false,
      connectable: false,
    });
    for (const c of cols) {
      edges.push({
        id: `e-${c.id}`,
        source: c.id,
        target: argument.conclusion_id,
        type: "smoothstep",
        style: {
          stroke: c.variant === "premise" ? "#6B7580" : "#E2A85A",
          strokeWidth: 1.1,
          strokeDasharray: c.variant === "premise" ? undefined : "5 4",
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: c.variant === "premise" ? "#6B7580" : "#E2A85A", width: 14, height: 14 },
      });
    }
    const byTarget = new Map<string, MapObjection[]>();
    let orphan = 0;
    for (const o of objections) {
      if (!(o.target_premise_id in xOf)) {
        xOf[o.target_premise_id] = width + 40 + orphan++ * 50;
        yOf[o.target_premise_id] = BAND;
      }
      const list = byTarget.get(o.target_premise_id) ?? [];
      list.push(o);
      byTarget.set(o.target_premise_id, list);
    }
    const DOT = 40;
    for (const [target, list] of byTarget) {
      const per = Math.max(1, Math.floor(NODE_W / DOT));
      list.forEach((o, j) => {
        const r = Math.floor(j / per);
        const inRow = Math.min(per, list.length - r * per);
        const k = j % per;
        const x = xOf[target] + NODE_W / 2 - (inRow * DOT) / 2 + k * DOT + 2;
        const y = yOf[target] - 52 - r * 44;
        const color = o.outcome ? outcomeColor(o.outcome) : "#808A94";
        const text = o.outcome && isOutcome(o.outcome) ? OUTCOME_TEXT_COLORS[o.outcome] : o.outcome ? "#F4F1E9" : "#B4BBC2";
        nodes.push({
          id: `obj-${o.id}`,
          type: "objection",
          position: { x, y },
          data: {
            label: `O${o.index}`,
            color,
            text,
            active: !!o.active,
            title: `Objection O${o.index} · ${agentLabel(o.agent)} (${o.family}) · ${o.outcome ? o.outcome.replace(/_/g, " ") : o.active ? "in trial" : "not tried"}`,
          } satisfies ObjectionData,
          draggable: false,
          connectable: false,
        });
        if (cols.some((c) => c.id === target)) {
          edges.push({
            id: `a-${o.id}`,
            source: `obj-${o.id}`,
            target,
            animated: !!o.active,
            style: { stroke: color, strokeWidth: o.outcome ? 1.6 : 1, strokeDasharray: o.outcome ? undefined : "3 3" },
            markerEnd: { type: MarkerType.ArrowClosed, color, width: 12, height: 12 },
          });
        }
      });
    }
    return { nodes, edges };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed on content, not array identity
  }, [argument, claims, revKey, objKey, maxCols]);

  // React Flow measures nodes once they mount; keep those measurements when the layout is recomputed
  // (every replay step), otherwise re-created nodes stay hidden waiting for a resize that never comes.
  const [rfNodes, setRfNodes] = useState<Node[]>(nodes);
  useEffect(() => {
    setRfNodes((prev) => {
      const byId = new Map(prev.map((n) => [n.id, n]));
      return nodes.map((n) => {
        const p = byId.get(n.id);
        return p?.measured ? { ...n, measured: p.measured } : n;
      });
    });
  }, [nodes]);
  const onNodesChange = useCallback((changes: NodeChange[]) => setRfNodes((nds) => applyNodeChanges(changes, nds)), []);
  const signature = `${nodes.length}`;
  return (
    <div style={{ height }} className="w-full border border-rule bg-[#1B1F23]">
      <ReactFlow
        nodes={rfNodes}
        onNodesChange={onNodesChange}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        zoomOnDoubleClick={false}
        panOnScroll={false}
        preventScrolling={false}
        minZoom={0.2}
        maxZoom={1.6}
        onNodeClick={(_, node) => {
          if (node.id.startsWith("obj-")) onSelectObjection?.(node.id.slice(4));
          else onSelectClaim?.(node.id);
        }}
        aria-label={`Argument map: ${argument.title || argument.id}`}
      >
        <Controls showInteractive={false} position="bottom-right" />
        <Refit signature={signature} />
      </ReactFlow>
    </div>
  );
}
