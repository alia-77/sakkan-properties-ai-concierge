import json
import uuid

import structlog

from src.settings import OUTPUT_DIR


OUTPUT_DIR.mkdir(exist_ok=True)

LOG = OUTPUT_DIR / "trace_logs.jsonl"


structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


def new_trace_id():
    return uuid.uuid4().hex


def event(trace_id, event_name, **data):
    record = {
        "trace_id": trace_id,
        "event": event_name,
        **data,
    }

    with LOG.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )

    logger.info(
        event_name,
        **data,
        trace_id=trace_id,
    )
