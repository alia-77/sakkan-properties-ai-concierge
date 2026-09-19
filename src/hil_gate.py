from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.observability import event


@dataclass
class ApprovalResult:
    decision: str
    final_text: str


async def request_approval(
    trace_id: str,
    draft: str,
    approve_callback: Optional[Callable[..., Any]] = None,
) -> ApprovalResult:
    event(
        trace_id,
        "hil_requested",
        draft=draft,
    )

    # Used by the Chainlit UI and scripted evaluation callbacks.
    if approve_callback:
        result = await approve_callback(draft)

        if isinstance(result, tuple):
            decision, final_text = result
        elif isinstance(result, dict):
            decision = result.get("decision", "reject")
            final_text = result.get("final_text", draft)
        else:
            decision = "reject"
            final_text = draft

        event(
            trace_id,
            "hil_decision",
            decision=decision,
        )

        return ApprovalResult(
            decision=decision,
            final_text=final_text,
        )

    # Fail closed when no approval mechanism is available.
    event(
        trace_id,
        "hil_decision",
        decision="pending",
        reason="approval_callback_missing",
    )

    return ApprovalResult(
        decision="pending",
        final_text="",
    )
