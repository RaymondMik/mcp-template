# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MCP Chat: a terminal chat app that talks to Claude via the Anthropic API and gets its tools, document resources, and slash-command prompts from an MCP server over stdio. The repo is a learning template: `mcp_server.py` and `mcp_client.py` hold `# TASK:` markers for MCP features still to be implemented.

## Commands

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
docker compose up -d                   # start PostgreSQL (host port 5433); seeds from db/init.sql on first start

uv run main.py                         # run the chat CLI
uv run main.py other_server.py ...     # also connect extra MCP servers (each launched via `uv run <script>`)
uv run mcp_client.py                   # smoke test: connect to mcp_server.py and print its tools
uv run mcp dev mcp_server.py           # open the server in the MCP Inspector (from mcp[cli])
```

There are no tests, linters, or type checks.

## Environment (`.env`)

- `ANTHROPIC_API_KEY`: required.
- `CLAUDE_MODEL`: required (`main.py` asserts on it).
- `DATABASE_URL`: required by `mcp_server.py` (`postgresql://mcp:mcp@localhost:5433/mcp_docs`). The MCP stdio client does not pass the parent's environment to server subprocesses (`MCPClient` uses `env=None`), so the server calls `load_dotenv()` itself and doesn't depend on `main.py` for its environment.
- `USE_UV=1`: launch the document server with `uv run mcp_server.py` instead of `python mcp_server.py`.

## Architecture

**Process model:** `main.py` starts `mcp_server.py` as a stdio subprocess through `MCPClient`, which is an async context manager that owns a `ClientSession`. It also starts one more client for each script passed on the command line. All clients go in a `clients` dict; the document server's client is also passed separately as `doc_client`.

**Chat loop (`core/chat.py`):** `Chat.run` collects tools from *every* client (`ToolManager.get_all_tools`) and calls Claude. While `stop_reason == "tool_use"`, `ToolManager.execute_tool_requests` sends each tool call to the first client that lists a tool with that name, then feeds the results back to Claude. The conversation history lives in `Chat.messages`.

**CLI layer (`core/cli_chat.py`, `core/cli.py`):** `CliChat` overrides `_process_query`, and only uses `doc_client` for these features:
- `@doc_id` mentions: reads the `docs://documents` resource (a JSON list of IDs), then inlines each mentioned doc from `docs://documents/{doc_id}` into the prompt inside `<document>` tags.
- `/command doc_id`: calls `get_prompt(command, {"doc_id": ...})` and converts the returned MCP `PromptMessage`s into Anthropic `MessageParam`s. Every prompt is assumed to take a single `doc_id` argument.
- `CliApp` (prompt_toolkit) fills tab completion from `list_prompts()` and the doc ID resource when the app starts.

**Server (`mcp_server.py`):** FastMCP with async handlers. Access goes through a `psycopg_pool.AsyncConnectionPool` that opens on first use. The project is being moved from documents to movies, so the server currently uses two tables:
- **`movies`** (`title, release_year, genre, description, rating`, seeded from `db/init.sql`): used by the tools. `get_movie_by_title` looks up movies (case-insensitive; exact matches first, otherwise partial matches). `update_movie_rating` changes only the rating. It needs an exact title, plus `release_year` when several movies share that title.
- **`documents`**: still used by the `docs://` resources and the `format` prompt. That table no longer exists in `db/init.sql`.

Docker runs `db/init.sql` only when the volume is empty (`docker compose down -v` resets it). The tool, resource, and prompt names/URIs are contracts that the client code depends on. If you rename `docs://documents`, `docs://documents/{doc_id}`, or a prompt's `doc_id` parameter, update `cli_chat.py` too.

`core/claude.py` is a thin wrapper around `anthropic.Anthropic().messages.create` plus helpers for appending messages.
