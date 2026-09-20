import json

from google import genai
from google.genai import types

from src.observability import event
from src.settings import GEMINI_API_KEY, GEMINI_MODEL, MOCK_MODE


client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


def generate_json(trace_id, agent, prompt):
    if MOCK_MODE or client is None:
        event(
            trace_id,
            "llm_fallback",
            agent=agent,
            reason="LLM unavailable",
        )
        return None

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        data = json.loads(response.text)

        event(
            trace_id,
            "llm_call",
            agent=agent,
            model=GEMINI_MODEL,
        )

        return data

    except Exception as exc:
        event(
            trace_id,
            "llm_error",
            agent=agent,
            model=GEMINI_MODEL,
            error=str(exc),
        )
        return None
