# MCP Chat

MCP Chat is a command-line interface application that enables interactive chat capabilities with AI models through the Anthropic API. The application supports document retrieval, command-based prompts, and extensible tool integrations via the MCP (Model Control Protocol) architecture.

## Prerequisites

- Python 3.9+
- Anthropic API Key

## Setup

### Step 1: Configure the environment variables

1. Create or edit the `.env` file in the project root and verify that the following variables are set correctly:

```
ANTHROPIC_API_KEY=""  # Enter your Anthropic API secret key
CLAUDE_MODEL=""       # The Claude model ID to use
DATABASE_URL="postgresql://mcp:mcp@localhost:5433/mcp_docs"
```

### Step 1b: Start the PostgreSQL database

Documents are stored in PostgreSQL, run with Docker Compose:

```bash
docker compose up -d
```

On its first start the container runs `db/init.sql`, which creates the `documents` table and adds the sample documents. The database is exposed on host port **5433** so it doesn't clash with a local Postgres on 5432.

### Step 2: Install dependencies

#### Option 1: Setup with uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

1. Install uv, if not already installed:

```bash
pip install uv
```

2. Create and activate a virtual environment:

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
uv pip install -e .
```

4. Run the project

```bash
uv run main.py
```

#### Option 2: Setup without uv

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install anthropic python-dotenv prompt-toolkit "mcp[cli]>=1.8.0" "psycopg[binary,pool]>=3.2"
```

3. Run the project

```bash
python main.py
```

## Usage

### Basic Interaction

Simply type your message and press Enter to chat with the model.

### Document Retrieval

Use the @ symbol followed by a document ID to include document content in your query:

```
> Tell me about @deposition.md
```

### Commands

Use the / prefix to execute commands defined in the MCP server:

```
> /summarize deposition.md
```

Commands will auto-complete when you press Tab.

## Development

### Adding New Documents

Insert rows into the `documents` table (`id`, `content`), for example:

```bash
docker compose exec db psql -U mcp mcp_docs -c "INSERT INTO documents VALUES ('notes.txt', 'Some notes')"
```

To change the seed data, edit `db/init.sql`. It only runs automatically when the volume is empty; you can run it again with `docker compose exec -T db psql -U mcp mcp_docs < db/init.sql`, or reset everything with `docker compose down -v`.

### Implementing MCP Features

To fully implement the MCP features:

1. Complete the TODOs in `mcp_server.py`
2. Implement the missing functionality in `mcp_client.py`

### Linting and Typing Check

There are no lint or type checks implemented.
