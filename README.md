# MCP Chat

MCP Chat is a command-line interface application that enables interactive chat capabilities with AI models through the Anthropic API. The application answers questions about 1980s movies stored in PostgreSQL and supports movie mentions, command-based prompts, and extensible tool integrations via the MCP (Model Control Protocol) architecture.

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

On its first start the container runs `db/init.sql`, which creates the `movies` table and adds 100 popular 1980s movies (title, year, genre, description and a random 0–10 rating). The database is exposed on host port **5433** so it doesn't clash with a local Postgres on 5432.

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

### Movie Mentions

Use the @ symbol followed by a movie title to include that movie's details in your query. Titles can contain spaces, and matching ignores case:

```
> Tell me about @Back to the Future
```

You can also ask Claude to look up a movie or change its rating; only the rating can be edited.

### Commands

Use the / prefix to execute commands defined in the MCP server:

```
> /summarize_description Ferris Bueller's Day Off
```

`/summarize_description` shows the movie's description in 50 words or fewer; the stored description is not changed. Commands and movie titles auto-complete when you press Tab.

## Development

### Adding New Movies

Insert rows into the `movies` table, for example:

```bash
docker compose exec db psql -U mcp mcp_docs -c "INSERT INTO movies (title, release_year, genre, description, rating) VALUES ('Tremors', 1990, 'Horror', 'Desert townsfolk battle giant underground worms.', 7.5)"
```

Note that `release_year` must be between 1980 and 1989.

To change the seed data, edit `db/init.sql`. It only runs automatically when the volume is empty; you can run it again with `docker compose exec -T db psql -U mcp mcp_docs < db/init.sql`, or reset everything with `docker compose down -v`.

### Implementing MCP Features

To fully implement the MCP features:

1. Complete the TODOs in `mcp_server.py`
2. Implement the missing functionality in `mcp_client.py`

### Linting and Typing Check

There are no lint or type checks implemented.
