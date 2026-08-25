import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    ROOT / ".env"
)


DATA_DIR = ROOT / "data" / "docs"
OUTPUT_DIR = ROOT / "outputs"

COLLECTION = "sakkan_properties"

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
)

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333",
)

QDRANT_API_KEY = (
    os.getenv("QDRANT_API_KEY")
    or None
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

GEMINI_EMBED_MODEL = os.getenv(
    "GEMINI_EMBED_MODEL",
    "gemini-embedding-2",
)

MOCK_MODE = (
    os.getenv(
        "MOCK_MODE",
        "false",
    ).lower()
    == "true"
)

MAX_STEPS = int(
    os.getenv(
        "MAX_STEPS",
        "12",
    )
)

MAX_TOOL_CALLS = int(
    os.getenv(
        "MAX_TOOL_CALLS",
        "8",
    )
)

MAX_TOTAL_STEPS = MAX_STEPS
MAX_TOOL_CALLS_PER_AGENT = MAX_TOOL_CALLS
