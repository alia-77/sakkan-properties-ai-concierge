# Sakkan Properties AI Concierge

Agentic real-estate concierge for Sakkan Properties, combining **LangGraph, Qdrant RAG, mem0, MCP, Chainlit, Human-in-the-Loop, and DeepEval**.

The system helps brokers find matching properties, calculate mortgage scenarios, use client-scoped memory, and draft client messages. Every client-facing draft requires broker approval before it is returned.

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

Add `GEMINI_API_KEY` to `.env`.

Open `http://localhost:8000`.

## Demo

> Find Mr. Hassan three apartments in New Cairo under 5M EGP with 3 bedrooms, calculate his mortgage at 18% over 15 years with a 30% down payment, draft him a WhatsApp message in Arabic with the shortlist, and don't send anything until I approve.

The workflow demonstrates triage, Qdrant retrieval, MCP tools, mortgage analysis, memory, communication drafting, trace logging, and Human-in-the-Loop approval.

## Structure

```text
src/
  agents/          Multi-agent workflow
  orchestrator.py  LangGraph orchestration
  rag_chain.py     Qdrant retrieval
  memory.py        Client-scoped memory
  tools.py         Validated tools
  hil_gate.py      Broker approval
  observability.py Trace logging

mcp/               MCP tool server
data/docs/         60-document synthetic corpus
tests/             DeepEval test suite
```

## Commands

```powershell
chainlit run app.py
python -m src.ingest_qdrant
python mcp\mcp_tool_server.py
pytest tests\test_agent.py -q
```

Use `/forget <client_id>` to remove a client's stored memory.

All property data is synthetic and created for this project.
