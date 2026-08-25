# Sakkan Properties AI Concierge

Agentic real-estate concierge using LangGraph, Qdrant RAG, mem0, MCP, Chainlit, Human-in-the-Loop and DeepEval.

## Quick Start

1. `python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. `copy .env.example .env` and add `GEMINI_API_KEY`
4. `docker compose up -d` then `python -m src.ingest_qdrant`
5. `chainlit run app.py -w`

The demo scenario is designed around Mr. Hassan and always pauses before a client-facing draft is returned.

## Structure

- `src/orchestrator.py`: LangGraph workflow
- `src/agents/`: triage, property, mortgage and communication agents
- `src/rag_chain.py`: Gemini embeddings and Qdrant retrieval
- `src/memory.py`: consent-gated scoped memory
- `mcp/mcp_tool_server.py`: four MCP tools
- `src/hil_gate.py`: approval, rejection and edit gate
- `src/observability.py`: trace logs
- `tests/`: evaluation cases
- `data/docs/`: 60-document corpus

## Commands

`python -m src.ingest_qdrant`

`chainlit run app.py -w`

`python mcp/mcp_tool_server.py`

`pytest tests/test_agent.py -q`

`/forget <client_id>` removes that client's stored memory and reports only the count.
