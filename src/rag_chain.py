from google import genai
from google.genai import types
from qdrant_client import QdrantClient

from src.settings import (
    COLLECTION,
    GEMINI_API_KEY,
    GEMINI_EMBED_MODEL,
    MOCK_MODE,
    QDRANT_API_KEY,
    QDRANT_URL,
)
from src.observability import event


client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

genai_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


def embed(text, task):
    if MOCK_MODE:
        return [0.0] * 768

    response = genai_client.models.embed_content(
        model=GEMINI_EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task,
            output_dimensionality=768,
        ),
    )

    return response.embeddings[0].values


def retrieve(query, trace_id=None, top_k=4):
    vector = embed(
        query,
        "RETRIEVAL_QUERY",
    )

    hits = client.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=top_k,
    ).points

    results = [
        {
            "id": point.payload.get("doc_id"),
            "text": point.payload.get("text"),
            "score": point.score,
            "kind": point.payload.get("kind"),
        }
        for point in hits
    ]

    if trace_id:
        event(
            trace_id,
            "retrieval",
            query=query,
            results=[item["id"] for item in results],
        )

    return results
