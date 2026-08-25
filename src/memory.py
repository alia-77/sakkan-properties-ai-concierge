import json
import os

from src.observability import event
from src.settings import ROOT


try:
    from mem0 import Memory
except Exception:
    Memory = None


STORE = ROOT / "mem0_store"
STORE.mkdir(exist_ok=True)


class MemoryStore:
    def __init__(self):
        mock_mode = (
            os.getenv(
                "MOCK_MODE",
                "false",
            ).lower()
            == "true"
        )

        if Memory and not mock_mode:
            try:
                self.memory = Memory.from_config(
                    {
                        "vector_store": {
                            "provider": "qdrant",
                            "config": {
                                "host": "localhost",
                                "port": 6333,
                                "collection_name": "sakkan_memory",
                                "embedding_model_dims": 1536,
                            },
                        },
                        "llm": {
                            "provider": "gemini",
                            "config": {
                                "model": "gemini-2.0-flash-001",
                                "api_key": os.getenv(
                                    "GEMINI_API_KEY"
                                ),
                                "temperature": 0.1,
                            },
                        },
                        "embedder": {
                            "provider": "gemini",
                            "config": {
                                "model": "gemini-embedding-001",
                                "api_key": os.getenv(
                                    "GEMINI_API_KEY"
                                ),
                                "embedding_dims": 1536,
                            },
                        },
                    }
                )
            except Exception as exc:
                self.memory = None

                event(
                    "memory-init",
                    "memory_init_error",
                    error=str(exc),
                )
        else:
            self.memory = None

    def search(self, client_id, query):
        if self.memory:
            try:
                return self.memory.search(
                    query,
                    user_id=client_id,
                    limit=5,
                )
            except Exception:
                return []

        path = STORE / f"{client_id}.json"

        if not path.exists():
            return []

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def get(self, client_id, trace_id):
        result = self.search(
            client_id,
            "preferences and ongoing deals",
        )

        event(
            trace_id,
            "memory_read",
            client_id=client_id,
            count=len(result),
        )

        return result

    def add(
        self,
        client_id,
        text,
        consent,
        trace_id,
    ):
        if not consent:
            event(
                trace_id,
                "memory_write_blocked",
                client_id=client_id,
            )

            return False

        if self.memory:
            try:
                self.memory.add(
                    text,
                    user_id=client_id,
                )
            except Exception as exc:
                event(
                    trace_id,
                    "memory_write_error",
                    client_id=client_id,
                    error=str(exc),
                )

                return False
        else:
            path = STORE / f"{client_id}.json"

            if path.exists():
                old = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            else:
                old = []

            old.append(text)

            path.write_text(
                json.dumps(
                    old,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        event(
            trace_id,
            "memory_write",
            client_id=client_id,
        )

        return True

    def forget(self, client_id, trace_id):
        count = 0

        if self.memory:
            try:
                result = self.memory.get_all(
                    user_id=client_id
                )

                count = len(result or [])

                self.memory.delete_all(
                    user_id=client_id
                )

            except Exception as exc:
                event(
                    trace_id,
                    "memory_forget_error",
                    client_id=client_id,
                    error=str(exc),
                )
        else:
            path = STORE / f"{client_id}.json"

            if path.exists():
                data = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

                count = len(data)

                path.unlink()

        event(
            trace_id,
            "memory_forget",
            client_id=client_id,
            count=count,
        )

        return count


memory = MemoryStore()