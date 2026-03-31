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


def upsert_documents(documents: list[Document]):
    client = _get_client()
    _ensure_collection(client)

    # Delete existing chunks for each email_id before inserting
    email_ids = {d.metadata["email_id"] for d in documents}
    for email_id in email_ids:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[FieldCondition(key="metadata.email_id", match=MatchValue(value=email_id))]
            ),
        )

    store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=_get_embeddings(),
    )
    store.add_documents(documents)
