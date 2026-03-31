# api/query.py

import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from utils.embedder import get_vector_store

router = APIRouter()


class Message(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    query: str
    history: list[Message] = []


def _format_docs(docs) -> str:
    return "\n\n".join(
        f"[From: {d.metadata.get('from', '')} | Subject: {d.metadata.get('subject', '')} | Date: {d.metadata.get('date', '')}]\n{d.page_content}"
        for d in docs
    )


def _build_chat_history(history: list[Message]):
    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    return messages


@router.post("/api/query")
def query(req: QueryRequest):
    """
    RAG query over stored emails. Accepts conversation history for multi-turn.
    """
    store = get_vector_store()
    retriever = store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 5, "score_threshold": 0.5},
    )

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0.2,
        api_key=os.environ["OPENAI_API_KEY"],
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful email assistant. Answer questions using only the email context below. "
         "If the answer isn't in the context, say so.\n\nContext:\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    chat_history = _build_chat_history(req.history)

    chain = (
        {
            "context": retriever | _format_docs,
            "question": RunnablePassthrough(),
            "chat_history": lambda _: chat_history,
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(req.query)

    # Return deduplicated sources alongside the answer
    source_docs = retriever.invoke(req.query)
    seen = set()
    sources = []
    for d in source_docs:
        key = (d.metadata.get("email_id", ""), d.metadata.get("attachment_name", ""))
        if key in seen:
            continue
        seen.add(key)
        source = {
            "from": d.metadata.get("from", ""),
            "subject": d.metadata.get("subject", ""),
            "date": d.metadata.get("date", ""),
            "source_type": d.metadata.get("source_type", "body"),
        }
        if d.metadata.get("source_type") == "attachment":
            source["attachment_name"] = d.metadata.get("attachment_name", "")
        sources.append(source)

    return JSONResponse({"answer": answer, "sources": sources})
