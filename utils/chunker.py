# utils/chunker.py

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def chunk_email(email: dict) -> list[Document]:
    """Chunk an email body into LangChain Documents."""
    if not email.get("body", "").strip():
        return []

    base_meta = {
        "email_id": email["id"],
        "from": email["from"],
        "subject": email["subject"],
        "date": email.get("date", ""),
        "source_type": "body",
    }

    return [
        Document(page_content=chunk, metadata={**base_meta, "chunk_index": i})
        for i, chunk in enumerate(_splitter.split_text(email["body"]))
    ]


def chunk_attachment(email: dict, attachment_name: str, text: str) -> list[Document]:
    """Chunk parsed attachment text into LangChain Documents."""
    if not text.strip():
        return []

    meta = {
        "email_id": email["id"],
        "from": email["from"],
        "subject": email["subject"],
        "date": email.get("date", ""),
        "source_type": "attachment",
        "attachment_name": attachment_name,
    }

    return [
        Document(page_content=chunk, metadata={**meta, "chunk_index": i})
        for i, chunk in enumerate(_splitter.split_text(text))
    ]
