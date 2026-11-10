# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MCP Chat: a terminal chat app that talks to Claude via the Anthropic API and gets its tools, movie resources, and slash-command prompts from an MCP server over stdio. The repo is a learning template: `mcp_server.py` and `mcp_client.py` hold `# TASK:` markers for MCP features still to be implemented.

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
- `USE_UV=1`: launch the movie server with `uv run mcp_server.py` instead of `python mcp_server.py`.

## Architecture

**Process model:** `main.py` starts `mcp_server.py` as a stdio subprocess through `MCPClient`, which is an async context manager that owns a `ClientSession`. It also starts one more client for each script passed on the command line. All clients go in a `clients` dict; the movie server's client is also passed separately as `doc_client`.

**Chat loop (`core/chat.py`):** `Chat.run` collects tools from *every* client (`ToolManager.get_all_tools`) and calls Claude. While `stop_reason == "tool_use"`, `ToolManager.execute_tool_requests` sends each tool call to the first client that lists a tool with that name, then feeds the results back to Claude. The conversation history lives in `Chat.messages`.

**CLI layer (`core/cli_chat.py`, `core/cli.py`):** `CliChat` overrides `_process_query`, and only uses `doc_client` for these features:
- `@Title` mentions: reads the `movies://titles` resource (a JSON list of titles) and searches the query for `@<title>`, ignoring case and trying the longest titles first. Titles span several words, so the query is not split on spaces. Each mentioned movie is read from `movies://titles/{title}` and inlined into the prompt inside `<movie>` tags.
- `/command <title>`: everything after the command is the title. It calls `get_prompt(command, {"title": ...})` and converts the returned MCP `PromptMessage`s into Anthropic `MessageParam`s. Every prompt is assumed to take a single `title` argument.
- **Title encoding:** the client percent-encodes titles as one path segment (`quote(title, safe="")`), and the server `unquote`s them. FastMCP matches resource templates on the raw URI and doesn't decode.
- `CliApp` (prompt_toolkit) fills tab completion from `list_prompts()` and the `movies://titles` resource when the app starts. The `/command` argument completes against everything after the command, so multi-word titles work.

**Server (`mcp_server.py`):** FastMCP with async handlers. Everything reads the PostgreSQL `movies` table (`title, release_year, genre, description, rating`) through a `psycopg_pool.AsyncConnectionPool` that opens on first use. Titles are not unique (the unique key is title + year), so title lookups return every match.
- **Tools:** `get_movie_by_title` (case-insensitive; exact matches first, otherwise partial matches) and `update_movie_rating`. Ratings are the only editable field; the update needs an exact title, plus `release_year` when several movies share that title.
- **Resources:** `movies://titles` and `movies://titles/{title}` (plain-text details).
- **Prompt:** `summarize_description` embeds the movie's details and asks for a summary of 50 words or fewer. The summary is only shown; the stored description is never changed.

Docker runs `db/init.sql` only when the volume is empty (`docker compose down -v` resets it). The tool, resource, and prompt names/URIs are contracts that the client code depends on. If you rename `movies://titles`, `movies://titles/{title}`, or a prompt's `title` parameter, update `cli_chat.py` too.

`core/claude.py` is a thin wrapper around `anthropic.Anthropic().messages.create` plus helpers for appending messages.
