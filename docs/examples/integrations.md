# Integrations Examples

Examples showing StreamBlocks working alongside other frameworks. See also the dedicated guides for [Pydantic AI](../guides/pydantic-ai.md) and the [AG-UI protocol](../guides/agui.md).

## Pydantic AI Integration

Requires `OPENAI_API_KEY` and the `pydantic-ai` package. A PydanticAI agent transparently generates StreamBlocks-compatible output which is extracted in real time as the agent streams.

#! src/hother/streamblocks_examples/06_integrations/01_pydantic_ai_integration.py

## AG-UI Integration

Requires the `ag-ui` package (`pip install streamblocks[agui]`); no API key needed. Bridges StreamBlocks events to the AG-UI protocol for agent-to-frontend communication.

#! src/hother/streamblocks_examples/06_integrations/02_agui_integration.py
