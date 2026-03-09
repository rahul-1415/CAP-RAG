import os
from dataclasses import dataclass
from pathlib import Path


POSTPROCESS_MODES = ("none", "rules_only", "rules_plus_llm")


def _parse_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(value: str, default: int, minimum: int = None, maximum: int = None) -> int:
    try:
        parsed = int(str(value).strip()) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


@dataclass(frozen=True)
class RagRuntimeConfig:
    rerank_provider: str
    cohere_rerank_model: str
    rerank_candidates_multiplier: int
    postprocess_mode_default: str
    enable_analytics: bool
    analytics_db_path: Path
    analytics_retention_days: int
    analytics_retention_rows: int
    postprocess_dedup_threshold: float
    postprocess_max_doc_chars: int
    postprocess_max_docs: int


def load_rag_runtime_config() -> RagRuntimeConfig:
    rerank_provider = os.getenv("RERANK_PROVIDER", "cohere").strip().lower() or "cohere"
    default_mode = os.getenv("POSTPROCESS_MODE_DEFAULT", "rules_only").strip().lower() or "rules_only"
    if default_mode not in POSTPROCESS_MODES:
        default_mode = "rules_only"

    analytics_db_default = Path("analytics") / "rag_metrics.sqlite3"
    analytics_db_path = Path(os.getenv("ANALYTICS_DB_PATH", str(analytics_db_default))).expanduser()

    dedup_threshold_raw = os.getenv("POSTPROCESS_DEDUP_THRESHOLD", "0.92")
    try:
        dedup_threshold = float(dedup_threshold_raw)
    except (TypeError, ValueError):
        dedup_threshold = 0.92
    dedup_threshold = max(0.5, min(0.999, dedup_threshold))

    return RagRuntimeConfig(
        rerank_provider=rerank_provider,
        cohere_rerank_model=os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5"),
        rerank_candidates_multiplier=_parse_int(
            os.getenv("RERANK_CANDIDATES_MULTIPLIER"), default=4, minimum=1, maximum=10
        ),
        postprocess_mode_default=default_mode,
        enable_analytics=_parse_bool(os.getenv("ENABLE_ANALYTICS"), default=True),
        analytics_db_path=analytics_db_path,
        analytics_retention_days=_parse_int(
            os.getenv("ANALYTICS_RETENTION_DAYS"), default=45, minimum=1, maximum=3650
        ),
        analytics_retention_rows=_parse_int(
            os.getenv("ANALYTICS_RETENTION_ROWS"), default=50000, minimum=1000, maximum=1000000
        ),
        postprocess_dedup_threshold=dedup_threshold,
        postprocess_max_doc_chars=_parse_int(
            os.getenv("POSTPROCESS_MAX_DOC_CHARS"), default=1200, minimum=200, maximum=5000
        ),
        postprocess_max_docs=_parse_int(
            os.getenv("POSTPROCESS_MAX_DOCS"), default=20, minimum=1, maximum=50
        ),
    )


def init_advanced_rag_session_state(session_state, config: RagRuntimeConfig, default_model: str) -> None:
    if "rerank_enabled" not in session_state:
        session_state.rerank_enabled = True
    if "postprocess_mode" not in session_state:
        session_state.postprocess_mode = config.postprocess_mode_default
    if "postprocess_model_choice" not in session_state:
        session_state.postprocess_model_choice = default_model
