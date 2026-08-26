# Sakkan Properties AI Concierge

Agentic real-estate concierge for Sakkan Properties, built with LangGraph, Qdrant RAG, mem0, MCP, Chainlit, Human-in-the-Loop review, and DeepEval.

The system helps brokers find matching properties, calculate mortgage scenarios, use client-scoped memory, schedule viewings, and draft client messages. Every client-facing draft passes through a broker approval gate before it is returned.

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Example Workflow](#example-workflow)
- [MCP Tools](#mcp-tools)
- [Memory](#memory)
- [Human-in-the-Loop](#human-in-the-loop)
- [Observability](#observability)
- [Evaluation](#evaluation)
- [Useful Commands](#useful-commands)
- [Project Structure](#project-structure)
- [Responsible AI](#responsible-ai)

## Architecture

```text
Broker
  |
  v
Chainlit UI
  |
  v
LangGraph Orchestrator
  |
  |-- Triage Agent
  |-- Property Finder --> Qdrant RAG + Listing Tools
  |-- Mortgage Analyst --> MCP Mortgage Tool
  |-- Communication Agent
             |
             v
       Human-in-the-Loop
             |
             v
          Response
```

Supporting systems:

- **mem0**: client preferences, ongoing deals, episodic memory
- **MCP**: listing search, listing lookup, mortgage calculation, viewing scheduling
- **structlog**: trace ID propagated across all workflow events
- **DeepEval**: automated evaluation suite

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
docker compose up -d
python -m src.ingest_qdrant
chainlit run app.py
```

Add `GEMINI_API_KEY` and the required Qdrant settings to `.env`.

Open `http://localhost:8000`.

## Example Workflow

Main demonstration scenario:

> Find Mr. Hassan three apartments in New Cairo under 5M EGP with 3 bedrooms, calculate his mortgage at 18% over 15 years with a 30% down payment, draft him a WhatsApp message in Arabic with the shortlist, and don't send anything until I approve.

This exercises:

1. Intent and client identification
2. Client-scoped memory retrieval
3. Qdrant retrieval
4. Listing search through tools
5. Mortgage calculation
6. Arabic communication drafting
7. Human approval before client-facing output
8. Structured trace logging

## MCP Tools

The MCP server exposes four validated tools:

- `search_listings`
- `fetch_listing`
- `mortgage_calculator`
- `schedule_viewing`

Run the MCP server with:

```powershell
python mcp\mcp_tool_server.py
```

## Memory

mem0 stores client-scoped information using three patterns:

- Client preferences
- Broker ongoing deals
- Episodic conversation summaries

Memory writes require explicit consent.

Remove a client's stored memory without displaying its contents:

```text
/forget <client_id>
```

## Human-in-the-Loop

Any client-facing draft requires broker review through one of:

- **Approve**
- **Reject**
- **Edit**

No client-facing message is returned as approved without a corresponding approval decision.

## Observability

Each request receives a `trace_id`.

Structured events are written to:

```text
outputs/trace_logs.jsonl
```

Logs cover agent transitions, retrievals, tool calls, memory operations, and Human-in-the-Loop decisions.

## Evaluation

The project includes 10 evaluation cases using DeepEval, covering:

- Faithfulness
- Provenance
- Tool-call presence
- Consent respect
- Human-in-the-Loop behavior
- HiL compliance

Results are stored in:

```text
outputs/eval_report.json
```

Run the evaluation suite with:

```powershell
pytest tests\test_agent.py -q
```

## Useful Commands

Start the application:

```powershell
chainlit run app.py
```

Rebuild the Qdrant index:

```powershell
python -m src.ingest_qdrant
```

Run the MCP server:

```powershell
python mcp\mcp_tool_server.py
```

Run the evaluation suite:

```powershell
pytest tests\test_agent.py -q
```

Run individual component checks:

```powershell
python -c "from src.agents.triage_agent import classify_intent; print(classify_intent('test', 'Calculate a mortgage for a 4M EGP property at 18% for 15 years with 30% down.'))"
```

```powershell
python -c "from src.agents.mortgage_analyst import extract_mortgage_params; print(extract_mortgage_params('Calculate a mortgage for a 4M EGP property at 18% for 15 years with 30% down.', 4000000))"
```

## Project Structure

```text
sakkan-properties-ai-concierge/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── docker-compose.yml
├── src/
│   ├── agents/
│   │   ├── triage_agent.py
│   │   ├── property_finder.py
│   │   ├── mortgage_analyst.py
│   │   └── comms_agent.py
│   ├── orchestrator.py
│   ├── rag_chain.py
│   ├── ingest_qdrant.py
│   ├── memory.py
│   ├── tools.py
│   ├── hil_gate.py
│   └── observability.py
├── mcp/
│   └── mcp_tool_server.py
├── data/
│   └── docs/
├── tests/
│   ├── test_agent.py
│   └── eval_cases.jsonl
├── config/
│   └── RAI_Config.yaml
├── outputs/
│   ├── eval_report.json
│   ├── trace_logs.jsonl
│   └── final_report.md
├── docs/
│   └── demo.gif
└── scripts/
    └── reset.sh
```

## Responsible AI

The system is designed to:

- avoid fabricated listings and prices
- preserve client data isolation
- require consent before memory writes
- require human review for every client-facing message

All property and client data is synthetic and created specifically for this project.