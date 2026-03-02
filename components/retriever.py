import os
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "Chroma" / "env_policy"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


def initialize_retriever():
    if not DB_DIR.exists():
        raise FileNotFoundError(
            f"Chroma DB directory not found at {DB_DIR}. Ensure the vector DB is available in deployment."
        )

    client_settings = chromadb.config.Settings(
        is_persistent=True,
        persist_directory=str(DB_DIR),
        anonymized_telemetry=False,
    )

    # Normalized vectors generally improve cosine similarity retrieval stability.
    embedder = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )

    bge_vectorstore = Chroma(
        embedding_function=embedder,
        client_settings=client_settings,
        collection_name="env_policy_bge",
        collection_metadata={"hnsw:space": "cosine"},
    )

    return bge_vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5},
    )
