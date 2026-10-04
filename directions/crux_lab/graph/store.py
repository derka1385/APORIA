"""SQLite store. One table per object kind (JSON payload + indexed keys) and an edge table."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel

from crux_lab.config import DB_PATH
from crux_lab.graph.schema import Argument, Brief, Claim, Edge, Objection, Paper, Trial

T = TypeVar("T", bound=BaseModel)
KINDS: dict[type[BaseModel], str] = {Paper: "papers", Claim: "claims", Argument: "arguments",
                                     Objection: "objections", Trial: "trials", Brief: "briefs"}
# Secondary key per kind, for cheap filtering.
PARENT = {"papers": "source", "claims": "paper_id", "arguments": "paper_id",
          "objections": "argument_id", "trials": "objection_id", "briefs": "objection_id"}


class Store:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = str(path)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.execute("PRAGMA journal_mode=WAL")
        for table, parent in PARENT.items():
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, "
                              f"{parent} TEXT, data TEXT NOT NULL)")
            self.conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_parent ON {table}({parent})")
        self.conn.execute("CREATE TABLE IF NOT EXISTS edges (src TEXT, dst TEXT, relation TEXT, "
                          "PRIMARY KEY (src, dst, relation))")
        self.conn.commit()

    def put(self, obj: BaseModel) -> None:
        self.put_many([obj])

    def put_many(self, objs: Iterable[BaseModel]) -> None:
        with self._lock:
            for o in objs:
                if isinstance(o, Edge):
                    self.conn.execute("INSERT OR REPLACE INTO edges VALUES (?,?,?)",
                                      (o.src, o.dst, o.relation))
                    continue
                table = KINDS[type(o)]
                parent = getattr(o, PARENT[table])
                self.conn.execute(f"INSERT OR REPLACE INTO {table} VALUES (?,?,?)",
                                  (o.id, parent, o.model_dump_json()))
            self.conn.commit()

    def get(self, cls: type[T], id: str) -> T | None:
        row = self.conn.execute(f"SELECT data FROM {KINDS[cls]} WHERE id=?", (id,)).fetchone()
        return cls.model_validate_json(row[0]) if row else None

    def all(self, cls: type[T], parent: str | None = None) -> list[T]:
        table = KINDS[cls]
        if parent is None:
            rows = self.conn.execute(f"SELECT data FROM {table} ORDER BY rowid").fetchall()
        else:
            rows = self.conn.execute(f"SELECT data FROM {table} WHERE {PARENT[table]}=? ORDER BY rowid",
                                     (parent,)).fetchall()
        return [cls.model_validate_json(r[0]) for r in rows]

    def delete(self, cls: type[BaseModel], id: str) -> None:
        with self._lock:
            self.conn.execute(f"DELETE FROM {KINDS[cls]} WHERE id=?", (id,))
            self.conn.commit()

    def edges(self, src: str | None = None, dst: str | None = None) -> list[Edge]:
        q, args = "SELECT src, dst, relation FROM edges WHERE 1=1", []
        if src:
            q, args = q + " AND src=?", args + [src]
        if dst:
            q, args = q + " AND dst=?", args + [dst]
        return [Edge(src=a, dst=b, relation=c) for a, b, c in self.conn.execute(q, args).fetchall()]

    def count(self, cls: type[BaseModel]) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {KINDS[cls]}").fetchone()[0]

    def close(self) -> None:
        self.conn.close()
