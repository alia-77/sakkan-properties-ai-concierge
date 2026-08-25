import chainlit as cl

from src.memory import memory
from src.observability import event, new_trace_id
from src.orchestrator import run_concierge


@cl.on_chat_start
async def start():
    await cl.Message(
        content="Sakkan Properties AI Concierge ready."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    if message.content.startswith("/forget "):
        client_id = message.content.split(
            maxsplit=1
        )[1].strip()

        trace_id = new_trace_id()

        count = memory.forget(
            client_id,
            trace_id,
        )

        await cl.Message(
            content=(
                f"Removed {count} memory entries "
                f"for {client_id}."
            )
        ).send()

        return

    trace_id = new_trace_id()

    async with cl.Step(
        name="Orchestrator",
        type="run",
    ) as step:
        step.output = (
            f"trace_id={trace_id}"
        )

    result = await run_concierge(
        trace_id=trace_id,
        request_text=message.content,
        client_id=None,
        client_name=None,
    )

    event(
        trace_id,
        "request_completed",
    )

    async with cl.Step(
        name="Triage",
        type="run",
    ) as step:
        step.output = (
            f"Intents: {result.get('intents', [])}\n"
            f"Client: {result.get('client_name') or 'Unknown'}"
        )

    if result.get("memory_context"):
        async with cl.Step(
            name="Memory",
            type="tool",
        ) as step:
            step.output = (
                f"Retrieved "
                f"{len(result['memory_context'])} "
                f"scoped memory entries."
            )

    if result.get("retrieved"):
        async with cl.Step(
            name="RAG Retrieval",
            type="tool",
        ) as step:
            step.output = str(
                [
                    item.get("id")
                    for item in result["retrieved"]
                ]
            )

    if result.get("listings"):
        async with cl.Step(
            name="Property Finder",
            type="tool",
        ) as step:
            step.output = str(
                result["listings"]
            )

    if result.get("mortgages"):
        async with cl.Step(
            name="Mortgage Analyst",
            type="tool",
        ) as step:
            step.output = str(
                result["mortgages"]
            )

    if result.get("draft"):
        async with cl.Step(
            name="Communication",
            type="tool",
        ) as step:
            step.output = result["draft"]

    if result.get("hil_decision"):
        async with cl.Step(
            name="Human Approval",
            type="run",
        ) as step:
            step.output = (
                f"Decision: "
                f"{result['hil_decision']}"
            )

    final_response = result.get(
        "final_response"
    )

    if final_response:
        await cl.Message(
            content=final_response
        ).send()

    elif result.get("fallback"):
        await cl.Message(
            content=(
                "I could not complete "
                "the request confidently."
            )
        ).send()

    else:
        await cl.Message(
            content="No response was generated."
        ).send()