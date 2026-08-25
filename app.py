import chainlit as cl

from src.agents import triage_agent
from src.memory import memory
from src.observability import event, new_trace_id
from src.orchestrator import run_concierge


async def broker_approval(
    draft,
    trace_id,
    client_id,
    client_name,
):
    if client_id:
        consent_response = await cl.AskActionMessage(
            content=(
                f"Allow saving this request to "
                f"{client_name or client_id}'s memory?"
            ),
            actions=[
                cl.Action(
                    name="yes",
                    payload={"value": "yes"},
                    label="Yes",
                ),
                cl.Action(
                    name="no",
                    payload={"value": "no"},
                    label="No",
                ),
            ],
            timeout=300,
        ).send()

        consent = bool(
            consent_response
            and consent_response.get(
                "payload",
                {},
            ).get(
                "value"
            )
            == "yes"
        )

        if consent:
            memory.add(
                client_id,
                f"Episodic request: {draft}",
                True,
                trace_id,
            )
        else:
            event(
                trace_id,
                "memory_write_blocked",
                client_id=client_id,
            )

    event(
        trace_id,
        "hil_requested",
    )

    actions = [
        cl.Action(
            name="approve",
            payload={"value": "approve"},
            label="Approve",
        ),
        cl.Action(
            name="reject",
            payload={"value": "reject"},
            label="Reject",
        ),
        cl.Action(
            name="edit",
            payload={"value": "edit"},
            label="Edit",
        ),
    ]

    response = await cl.AskActionMessage(
        content=draft,
        actions=actions,
        timeout=300,
    ).send()

    if not response:
        event(
            trace_id,
            "hil_decision",
            decision="timeout",
        )

        return "reject", draft

    decision = response.get(
        "payload",
        {},
    ).get(
        "value",
        "reject",
    )

    if decision == "edit":
        edited = await cl.AskUserMessage(
            content="Send the edited client message:",
            timeout=300,
        ).send()

        if edited:
            draft = edited.get(
                "output",
                draft,
            )

    event(
        trace_id,
        "hil_decision",
        decision=decision,
    )

    return decision, draft


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

    client_id, client_name = triage_agent.get_client(
        trace_id,
        message.content,
    )

    async with cl.Step(
        name="Orchestrator",
        type="run",
    ) as step:
        step.output = (
            f"trace_id={trace_id}"
        )

    approval_callback = lambda draft: broker_approval(
        draft,
        trace_id,
        client_id,
        client_name,
    )

    result = await run_concierge(
        trace_id=trace_id,
        request_text=message.content,
        client_id=client_id,
        client_name=client_name,
        approve_callback=approval_callback,
    )

    async with cl.Step(
        name="Triage",
        type="run",
    ) as step:
        step.output = (
            f"Intents: {result.get('intents', [])}\n"
            f"Client: {client_name or 'Unknown'}"
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
    else:
        await cl.Message(
            content=(
                "I could not complete "
                "the request confidently."
            )
        ).send()