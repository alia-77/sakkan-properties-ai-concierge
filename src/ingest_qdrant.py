from qdrant_client import QdrantClient, models

from src.rag_chain import embed
from src.settings import (
    COLLECTION,
    DATA_DIR,
    QDRANT_API_KEY,
    QDRANT_URL,
)


CHUNK_SIZE = 1200


def chunk_text(text):
    chunks = []

    for start in range(
        0,
        len(text),
        CHUNK_SIZE,
    ):
        chunk = text[
            start:start + CHUNK_SIZE
        ].strip()

        if chunk:
            chunks.append(chunk)

    return chunks


def main():
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

    if client.collection_exists(
        COLLECTION
    ):
        client.delete_collection(
            COLLECTION
        )

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(
            size=768,
            distance=models.Distance.COSINE,
        ),
    )

    points = []
    point_id = 0

    for path in sorted(
        DATA_DIR.glob("*.txt")
    ):
        text = path.read_text(
            encoding="utf-8"
        ).strip()

        chunks = chunk_text(text)

        for chunk_index, chunk in enumerate(
            chunks
        ):
            vector = embed(
                chunk,
                "RETRIEVAL_DOCUMENT",
            )

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "doc_id": path.stem,
                        "chunk_id": (
                            f"{path.stem}_chunk_{chunk_index}"
                        ),
                        "text": chunk,
                        "kind": path.stem.split(
                            "_"
                        )[0],
                    },
                )
            )

            point_id += 1

    if points:
        client.upsert(
            collection_name=COLLECTION,
            points=points,
        )

    print(
        f"Indexed {len(points)} chunks"
    )


if __name__ == "__main__":
    main()
