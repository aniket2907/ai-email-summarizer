# utils/embedder.py

import os
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, FieldCondition, Filter, MatchValue
from langchain_core.documents import Document

COLLECTION_NAME = "emails"
VECTOR_SIZE = 1536  # text-embedding-3-small


def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")  # None for local Docker
    return QdrantClient(url=url, api_key=api_key)


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.environ["OPENAI_API_KEY"],
    )


def _ensure_collection(client: QdrantClient):
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def get_vector_store() -> QdrantVectorStore:
    client = _get_client()
    _ensure_collection(client)
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=_get_embeddings(),
    )


def _already_ingested(client: QdrantClient, email_id: str) -> bool:
    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="metadata.email_id", match=MatchValue(value=email_id))]
        ),
        limit=1,
        with_payload=False,
        with_vectors=False,
    )
    return len(results) > 0


def upsert_documents(documents: list[Document]):
    client = _get_client()
    _ensure_collection(client)

    # Skip emails that are already in Qdrant
    new_docs = [
        d for d in documents
        if not _already_ingested(client, d.metadata["email_id"])
    ]

    if not new_docs:
        return

    store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=_get_embeddings(),
    )
    store.add_documents(new_docs)
