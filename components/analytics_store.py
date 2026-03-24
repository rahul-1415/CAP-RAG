import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd


class AnalyticsStore:
    def __init__(self, db_path: Path, enabled: bool = True):
        self.enabled = bool(enabled)
        self.db_path = Path(db_path).expanduser()
        if self.enabled:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS query_runs (
                    run_id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    generation_model TEXT NOT NULL,
                    postprocess_model TEXT,
                    rerank_provider TEXT,
                    rerank_model TEXT,
                    retrieval_k INTEGER NOT NULL,
                    rerank_enabled INTEGER NOT NULL,
                    postprocess_mode TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    error_type TEXT,
                    warning_text TEXT,
                    total_ms REAL,
                    retrieval_ms REAL,
                    rerank_ms REAL,
                    generation_ms REAL,
                    postprocess_ms REAL,
                    context_chars INTEGER,
                    response_chars INTEGER,
                    retrieved_docs INTEGER,
                    selected_docs INTEGER,
                    rerank_fallback_reason TEXT,
                    refinement_applied INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS retrieval_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    rank_before INTEGER,
                    rank_after INTEGER,
                    source TEXT,
                    score_raw REAL,
                    score_rerank REAL,
                    selected INTEGER NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES query_runs(run_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY(run_id) REFERENCES query_runs(run_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    doc_id TEXT,
                    source TEXT,
                    title TEXT,
                    position INTEGER,
                    FOREIGN KEY(run_id) REFERENCES query_runs(run_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_query_runs_ts ON query_runs(ts);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_query_runs_model ON query_runs(generation_model);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_retrieval_docs_run_id ON retrieval_docs(run_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_feedback_run_id ON run_feedback(run_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_clicks_run_id ON source_clicks(run_id);")

    def log_run(self, run_payload: Dict[str, Any], doc_payloads: Sequence[Dict[str, Any]]) -> None:
        if not self.enabled:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_runs (
                    run_id, ts, query_hash, generation_model, postprocess_model,
                    rerank_provider, rerank_model, retrieval_k, rerank_enabled,
                    postprocess_mode, success, error_type, warning_text, total_ms,
                    retrieval_ms, rerank_ms, generation_ms, postprocess_ms,
                    context_chars, response_chars, retrieved_docs, selected_docs,
                    rerank_fallback_reason, refinement_applied
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_payload.get("run_id"),
                    run_payload.get("ts"),
                    run_payload.get("query_hash"),
                    run_payload.get("generation_model"),
                    run_payload.get("postprocess_model"),
                    run_payload.get("rerank_provider"),
                    run_payload.get("rerank_model"),
                    run_payload.get("retrieval_k"),
                    int(bool(run_payload.get("rerank_enabled"))),
                    run_payload.get("postprocess_mode"),
                    int(bool(run_payload.get("success"))),
                    run_payload.get("error_type"),
                    run_payload.get("warning_text"),
                    run_payload.get("total_ms"),
                    run_payload.get("retrieval_ms"),
                    run_payload.get("rerank_ms"),
                    run_payload.get("generation_ms"),
                    run_payload.get("postprocess_ms"),
                    run_payload.get("context_chars"),
                    run_payload.get("response_chars"),
                    run_payload.get("retrieved_docs"),
                    run_payload.get("selected_docs"),
                    run_payload.get("rerank_fallback_reason"),
                    int(bool(run_payload.get("refinement_applied"))),
                ),
            )
            conn.execute("DELETE FROM retrieval_docs WHERE run_id = ?", (run_payload.get("run_id"),))
            for row in doc_payloads:
                conn.execute(
                    """
                    INSERT INTO retrieval_docs (
                        run_id, rank_before, rank_after, source, score_raw, score_rerank, selected
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_payload.get("run_id"),
                        row.get("rank_before"),
                        row.get("rank_after"),
                        row.get("source"),
                        row.get("score_raw"),
                        row.get("score_rerank"),
                        int(bool(row.get("selected"))),
                    ),
                )

    def apply_retention(self, max_days: int, max_rows: int) -> None:
        if not self.enabled:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM query_runs WHERE ts < datetime('now', ?)",
                (f"-{int(max_days)} days",),
            )
            if max_rows and max_rows > 0:
                conn.execute(
                    """
                    DELETE FROM query_runs
                    WHERE run_id NOT IN (
                        SELECT run_id FROM query_runs ORDER BY ts DESC LIMIT ?
                    )
                    """,
                    (int(max_rows),),
                )

    def read_query_runs(
        self,
        days: int = 30,
        generation_model: Optional[str] = None,
        rerank_enabled: Optional[bool] = None,
        postprocess_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        if not self.enabled or not self.db_path.exists():
            return pd.DataFrame()

        clauses: List[str] = ["ts >= datetime('now', ?)"]
        params: List[Any] = [f"-{int(days)} days"]

        if generation_model:
            clauses.append("generation_model = ?")
            params.append(generation_model)
        if rerank_enabled is not None:
            clauses.append("rerank_enabled = ?")
            params.append(1 if rerank_enabled else 0)
        if postprocess_mode:
            clauses.append("postprocess_mode = ?")
            params.append(postprocess_mode)

        query = "SELECT * FROM query_runs WHERE " + " AND ".join(clauses) + " ORDER BY ts DESC"
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def read_doc_rows(self, run_ids: Iterable[str]) -> pd.DataFrame:
        run_ids = [run_id for run_id in run_ids if run_id]
        if not self.enabled or not self.db_path.exists() or not run_ids:
            return pd.DataFrame()

        placeholders = ",".join(["?"] * len(run_ids))
        query = (
            "SELECT run_id, rank_before, rank_after, source, score_raw, score_rerank, selected "
            f"FROM retrieval_docs WHERE run_id IN ({placeholders})"
        )
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=run_ids)

    def log_feedback(self, run_id: str, feedback_type: str, note: Optional[str] = None) -> None:
        if not self.enabled or not run_id or not feedback_type:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_feedback (run_id, ts, feedback_type, note)
                VALUES (?, ?, ?, ?)
                """,
                (
                    run_id,
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    feedback_type,
                    note,
                ),
            )

    def log_source_click(
        self,
        run_id: str,
        doc_id: Optional[str],
        source: Optional[str],
        title: Optional[str],
        position: Optional[int],
    ) -> None:
        if not self.enabled or not run_id:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO source_clicks (run_id, ts, doc_id, source, title, position)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    doc_id,
                    source,
                    title,
                    position,
                ),
            )

    def read_feedback_rows(self, run_ids: Iterable[str]) -> pd.DataFrame:
        run_ids = [run_id for run_id in run_ids if run_id]
        if not self.enabled or not self.db_path.exists() or not run_ids:
            return pd.DataFrame()

        placeholders = ",".join(["?"] * len(run_ids))
        query = (
            "SELECT run_id, ts, feedback_type, note "
            f"FROM run_feedback WHERE run_id IN ({placeholders}) ORDER BY ts DESC"
        )
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=run_ids)

    def read_source_click_rows(self, run_ids: Iterable[str]) -> pd.DataFrame:
        run_ids = [run_id for run_id in run_ids if run_id]
        if not self.enabled or not self.db_path.exists() or not run_ids:
            return pd.DataFrame()

        placeholders = ",".join(["?"] * len(run_ids))
        query = (
            "SELECT run_id, ts, doc_id, source, title, position "
            f"FROM source_clicks WHERE run_id IN ({placeholders}) ORDER BY ts DESC"
        )
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=run_ids)
