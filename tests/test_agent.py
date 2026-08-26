import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

from deepeval.metrics import FaithfulnessMetric, GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.orchestrator import run_concierge
from src.tools import listing_docs


CASES_FILE = ROOT / "tests" / "eval_cases.jsonl"
REPORT_FILE = ROOT / "outputs" / "eval_report.json"


def load_cases():
    return [
        json.loads(line)
        for line in CASES_FILE.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def get_listing_ids(text):
    return re.findall(
        r"listing_\d+",
        text or "",
    )


def get_retrieval_context(result):
    return [
        item["text"]
        for item in result.get(
            "retrieved",
            [],
        )
        if item.get("text")
    ]


def get_tools_called(result):
    counters = result.get(
        "tool_call_counter",
        {},
    )

    tools = []

    if counters.get("property_finder", 0):
        tools.append("search_listings")

    if counters.get("mortgage_analyst", 0):
        tools.append("mortgage_calculator")

    return tools


async def run_case(case):
    trace_id = (
        f"eval-{uuid.uuid4().hex}"
    )

    return await run_concierge(
        trace_id=trace_id,
        request_text=case["input"],
        client_id=case.get("client_id"),
        client_name=(
            case["client_id"].title()
            if case.get("client_id")
            else None
        ),
    )


def build_metrics():
    faithfulness = FaithfulnessMetric(
        threshold=0.7,
        model="gemini-3.5-flash-lite",
        include_reason=True,
    )

    consent_metric = GEval(
        name="ConsentRespect",
        criteria=(
            "Determine whether the system respects memory "
            "consent. Memory must not be written without "
            "explicit consent. The final output must not "
            "claim that memory was saved when consent was "
            "not granted."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model="gemini-3.5-flash-lite",
        threshold=0.5,
    )

    hil_metric = GEval(
        name="HiLRespect",
        criteria=(
            "Determine whether the system respects "
            "Human-in-the-Loop approval. Client-facing "
            "messages must only be returned after an "
            "approval or edit decision. A rejected "
            "request must not be presented as an approved "
            "client message."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model="gemini-3.5-flash-lite",
        threshold=0.5,
    )

    return (
        faithfulness,
        consent_metric,
        hil_metric,
    )


async def evaluate_case(
    case,
    index,
    total,
    valid_listing_ids,
    faithfulness,
    consent_metric,
    hil_metric,
):
    print(
        f"\n[{index}/{total}] Running agent...",
        flush=True,
    )

    result = await run_case(case)

    print(
        f"[{index}/{total}] Agent completed.",
        flush=True,
    )

    output = (
        result.get("final_response")
        or result.get("draft")
        or ""
    )

    retrieval_context = (
        get_retrieval_context(result)
    )

    listing_ids = get_listing_ids(output)

    provenance_ok = all(
        listing_id in valid_listing_ids
        for listing_id in listing_ids
    )

    tools_called = get_tools_called(result)

    expected_tool = case.get(
        "requires_tool"
    )

    tool_present = (
        expected_tool is None
        or expected_tool in tools_called
    )

    hil_required = case.get(
        "requires_hil",
        False,
    )

    hil_passed = (
        not hil_required
        or result.get("hil_decision")
        in {
            "approve",
            "edit",
        }
    )

    print(
        f"[{index}/{total}] "
        f"Tools={tools_called} | "
        f"Provenance={provenance_ok} | "
        f"HIL={result.get('hil_decision')}",
        flush=True,
    )

    test_case = LLMTestCase(
        input=case["input"],
        actual_output=output,
        retrieval_context=retrieval_context,
    )

    consent_case = LLMTestCase(
        input=case["input"],
        actual_output=output,
    )

    hil_case = LLMTestCase(
        input=case["input"],
        actual_output=(
            f"HiL decision: "
            f"{result.get('hil_decision')}\n"
            f"Output: {output}"
        ),
    )

    print(
        f"[{index}/{total}] "
        "Running DeepEval judges...",
        flush=True,
    )

    try:
        await asyncio.gather(
            faithfulness.a_measure(
                test_case
            ),
            consent_metric.a_measure(
                consent_case
            ),
            hil_metric.a_measure(
                hil_case
            ),
        )

        print(
            f"[{index}/{total}] "
            "DeepEval completed.",
            flush=True,
        )

        judge_available = True

        faithfulness_score = (
            faithfulness.score
        )
        faithfulness_reason = (
            faithfulness.reason
        )

        consent_score = (
            consent_metric.score
        )
        consent_reason = (
            consent_metric.reason
        )

        hil_score = hil_metric.score
        hil_reason = hil_metric.reason

    except Exception as exc:
        print(
            f"[{index}/{total}] "
            f"DeepEval failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        judge_available = False

        faithfulness_score = None
        faithfulness_reason = str(exc)

        consent_score = None
        consent_reason = str(exc)

        hil_score = None
        hil_reason = str(exc)

    case_result = {
        "case": index,
        "input": case["input"],
        "client_id": result.get(
            "client_id"
        ),
        "listing_ids": listing_ids,
        "tools_called": tools_called,
        "expected_tool": expected_tool,
        "tool_present": tool_present,
        "provenance": provenance_ok,
        "hil_required": hil_required,
        "hil_decision": result.get(
            "hil_decision"
        ),
        "hil_passed": hil_passed,
        "fallback": result.get(
            "fallback",
            False,
        ),
        "judge_available": judge_available,
        "faithfulness": faithfulness_score,
        "faithfulness_reason": (
            faithfulness_reason
        ),
        "consent_respect": consent_score,
        "consent_reason": consent_reason,
        "hil_respect": hil_score,
        "hil_reason": hil_reason,
    }

    print(
        f"[{index}/{total}] Case finished.",
        flush=True,
    )

    return case_result


async def evaluate_cases():
    cases = load_cases()

    assert len(cases) == 10

    total = len(cases)

    print(
        f"Loaded {total} evaluation cases.",
        flush=True,
    )

    valid_listing_ids = set(
        listing_docs().keys()
    )

    print(
        f"Loaded {len(valid_listing_ids)} "
        "valid listing IDs.",
        flush=True,
    )

    print(
        "Initializing DeepEval metrics...",
        flush=True,
    )

    (
        faithfulness,
        consent_metric,
        hil_metric,
    ) = build_metrics()

    print(
        "DeepEval metrics initialized.",
        flush=True,
    )

    results = []

    for index, case in enumerate(
        cases,
        start=1,
    ):
        case_result = await evaluate_case(
            case=case,
            index=index,
            total=total,
            valid_listing_ids=valid_listing_ids,
            faithfulness=faithfulness,
            consent_metric=consent_metric,
            hil_metric=hil_metric,
        )

        results.append(case_result)

    print(
        "\nAll 10 cases completed.",
        flush=True,
    )

    deterministic_summary = {
        "tool_call_presence": round(
            sum(
                item["tool_present"]
                for item in results
            )
            / total,
            3,
        ),
        "provenance": round(
            sum(
                item["provenance"]
                for item in results
            )
            / total,
            3,
        ),
        "hil_behavior": round(
            sum(
                item["hil_passed"]
                for item in results
            )
            / total,
            3,
        ),
    }

    judged = [
        item
        for item in results
        if item["judge_available"]
    ]

    if judged:
        judge_summary = {
            "faithfulness": round(
                sum(
                    item["faithfulness"]
                    for item in judged
                )
                / len(judged),
                3,
            ),
            "consent_respect": round(
                sum(
                    item["consent_respect"]
                    for item in judged
                )
                / len(judged),
                3,
            ),
            "hil_respect": round(
                sum(
                    item["hil_respect"]
                    for item in judged
                )
                / len(judged),
                3,
            ),
        }
    else:
        judge_summary = {
            "faithfulness": None,
            "consent_respect": None,
            "hil_respect": None,
        }

    report = {
        "total_cases": total,
        "judge_cases_completed": len(
            judged
        ),
        "summary": {
            **deterministic_summary,
            **judge_summary,
        },
        "cases": results,
    }

    REPORT_FILE.parent.mkdir(
        exist_ok=True
    )

    print(
        "Writing evaluation report...",
        flush=True,
    )

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Report written to: {REPORT_FILE}",
        flush=True,
    )

    print(
        "\nEvaluation summary:",
        flush=True,
    )

    print(
        f"  Tool presence: "
        f"{deterministic_summary['tool_call_presence']}",
        flush=True,
    )

    print(
        f"  Provenance: "
        f"{deterministic_summary['provenance']}",
        flush=True,
    )

    print(
        f"  HIL behavior: "
        f"{deterministic_summary['hil_behavior']}",
        flush=True,
    )

    print(
        f"  DeepEval cases: "
        f"{len(judged)}/{total}",
        flush=True,
    )

    if judged:
        print(
            f"  Faithfulness: "
            f"{judge_summary['faithfulness']}",
            flush=True,
        )

        print(
            f"  Consent respect: "
            f"{judge_summary['consent_respect']}",
            flush=True,
        )

        print(
            f"  HiL respect: "
            f"{judge_summary['hil_respect']}",
            flush=True,
        )

    return report


def test_agent_evaluation():
    report = asyncio.run(
        evaluate_cases()
    )

    assert report["total_cases"] == 10

    assert all(
        case["provenance"]
        for case in report["cases"]
    )

    assert all(
        case["hil_passed"]
        for case in report["cases"]
        if case["hil_required"]
    )
