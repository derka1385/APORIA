"""Databricks (sponsor) integration. Wired in, never blocking: does nothing without credentials.

`python -m crux_lab.databricks_sync`:
  1. writes every extracted claim to a `claims` Delta table (Unity Catalog) through a SQL warehouse,
  2. creates an AI Search (formerly Vector Search) endpoint and a Delta Sync index over that table
     with managed embeddings (`databricks-gte-large-en`) on the claim text,
  3. `query(text)` searches it — the same "Has this move been made?" lookup the local index serves.
The local BM25 + embedding index stays the source of truth (CLAUDE.md). MLflow tracing to a
Databricks experiment is handled in crux_lab/llm/tracing.py; Model Serving endpoints are picked up
by `make providers` (crux_lab/llm/providers.py: DatabricksProvider).

Env: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID, optional CRUX_LAB_CATALOG
(default `workspace`), CRUX_LAB_SCHEMA (default `crux_lab`), CRUX_LAB_VS_ENDPOINT
(default `crux-lab`), CRUX_LAB_EMBEDDING_ENDPOINT (default `databricks-gte-large-en`).
"""
from __future__ import annotations

import logging
import os

from crux_lab.config import settings
from crux_lab.graph.schema import Claim
from crux_lab.graph.store import Store

log = logging.getLogger(__name__)
CATALOG = os.environ.get("CRUX_LAB_CATALOG", "workspace")
SCHEMA = os.environ.get("CRUX_LAB_SCHEMA", "crux_lab")
TABLE = f"{CATALOG}.{SCHEMA}.claims"
INDEX = f"{CATALOG}.{SCHEMA}.claims_index"
ENDPOINT = os.environ.get("CRUX_LAB_VS_ENDPOINT", "crux-lab")
EMBED = os.environ.get("CRUX_LAB_EMBEDDING_ENDPOINT", "databricks-gte-large-en")


def available() -> bool:
    return settings.has("databricks") and bool(os.environ.get("DATABRICKS_WAREHOUSE_ID"))


def client():
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient(host=settings.databricks_host, token=settings.databricks_token)


def _sql(w, statement: str, params: list | None = None):
    from databricks.sdk.service.sql import StatementParameterListItem

    r = w.statement_execution.execute_statement(
        statement=statement, warehouse_id=os.environ["DATABRICKS_WAREHOUSE_ID"], wait_timeout="50s",
        parameters=[StatementParameterListItem(name=k, value=v) for k, v in (params or [])] or None)
    if r.status and r.status.error:
        raise RuntimeError(r.status.error.message)
    return r


def write_claims_table(w, claims: list[Claim], batch: int = 200) -> int:
    _sql(w, f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
    _sql(w, f"CREATE OR REPLACE TABLE {TABLE} (id STRING, paper_id STRING, kind STRING, level STRING, "
            f"text STRING, quote STRING) TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    n = 0
    for i in range(0, len(claims), batch):
        rows, params = [], []
        for j, c in enumerate(claims[i:i + batch]):
            rows.append(f"(:i{j}, :p{j}, :k{j}, :l{j}, :t{j}, :q{j})")
            params += [(f"i{j}", c.id), (f"p{j}", c.paper_id), (f"k{j}", c.kind), (f"l{j}", c.level),
                       (f"t{j}", c.text), (f"q{j}", c.quote)]
        _sql(w, f"INSERT INTO {TABLE} VALUES " + ", ".join(rows), params)
        n += len(rows)
    return n


def ensure_index(w) -> None:
    from databricks.sdk.service.vectorsearch import (DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn,
                                                     EndpointType, PipelineType, VectorIndexType)

    names = [e.name for e in w.vector_search_endpoints.list_endpoints()]
    if ENDPOINT not in names:
        w.vector_search_endpoints.create_endpoint_and_wait(name=ENDPOINT, endpoint_type=EndpointType.STANDARD)
    try:
        w.vector_search_indexes.get_index(INDEX)
        w.vector_search_indexes.sync_index(INDEX)
    except Exception:  # noqa: BLE001 - index does not exist yet
        w.vector_search_indexes.create_index(
            name=INDEX, endpoint_name=ENDPOINT, primary_key="id", index_type=VectorIndexType.DELTA_SYNC,
            delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
                source_table=TABLE, pipeline_type=PipelineType.TRIGGERED,
                embedding_source_columns=[EmbeddingSourceColumn(name="text", embedding_model_endpoint_name=EMBED)]))


def query(text: str, k: int = 10) -> list[dict]:
    w = client()
    r = w.vector_search_indexes.query_index(index_name=INDEX, columns=["id", "paper_id", "kind", "text"],
                                            query_text=text, num_results=k)
    cols = [c.name for c in r.manifest.columns]
    return [dict(zip(cols, row)) for row in (r.result.data_array or [])]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not available():
        print("Databricks not configured (need DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID); "
              "skipping. The local index remains the source of truth.")
        return
    w = client()
    claims = [c for c in Store().all(Claim) if c.level in ("fulltext", "abstract")]
    n = write_claims_table(w, claims)
    ensure_index(w)
    print(f"wrote {n} claims to {TABLE}; Delta Sync index {INDEX} on endpoint {ENDPOINT} ({EMBED})")


if __name__ == "__main__":
    main()
