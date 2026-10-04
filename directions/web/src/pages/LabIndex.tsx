import { Navigate } from "react-router";
import { Code, DataState, Empty } from "../components/ui";
import { useJSON } from "../lib/data";
import type { Index } from "../types";

export default function LabIndex() {
  const index = useJSON<Index>("index.json");
  return (
    <div className="mx-auto max-w-[1200px] px-4 py-10 sm:px-6">
      <DataState load={index} what="the index">
        {(ix) =>
          ix.runs?.length ? (
            <Navigate to={`/runs/${encodeURIComponent(ix.runs[0].run_id)}`} replace />
          ) : (
            <Empty>
              No runs to replay yet. Run <Code>make runs</Code> then <Code>make export</Code>.
            </Empty>
          )
        }
      </DataState>
    </div>
  );
}
