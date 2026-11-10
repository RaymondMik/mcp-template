# MCP Chat

MCP Chat is a command-line chat app for asking Claude about 100 popular movies from the 1980s. The movies are stored in PostgreSQL and served to the app by an MCP (Model Context Protocol) server, which gives Claude tools to look movies up and change their ratings. You can mention movies with `@`, and summarize a movie's description with a `/` command.

## Prerequisites

- Python 3.10+
- Docker (for the PostgreSQL database)
- An Anthropic API key

## Setup

### 1. Configure the environment

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=""  # Your Anthropic API secret key
CLAUDE_MODEL=""       # The Claude model ID to use
DATABASE_URL="postgresql://mcp:mcp@localhost:5433/mcp_docs"
USE_UV=1              # 1 to start the MCP server with uv, 0 to use plain python
```

The MCP server loads `.env` itself, so `DATABASE_URL` only needs to be set there.

### 2. Start the database

```bash
docker compose up -d
```

On first start, the container runs `db/init.sql`, which creates the `movies` table and fills it with 100 movies, 10 from each year from 1980 to 1989. Each movie has a title, release year, genre, a plot summary of more than 100 words, and a rating from 0 to 10.

- **Ratings are random.** Postgres generates them when the script runs, so every fresh database gets different ratings.
- **Port 5433.** The database is exposed on host port 5433, not the usual 5432, so it doesn't clash with a local Postgres.

### 3. Install dependencies

With [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Without uv:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 4. Run

```bash
uv run main.py   # or: python main.py
```

To connect more MCP servers alongside the movie server, pass their scripts as arguments. Each one is started with `uv run <script>`:

```bash
uv run main.py other_server.py
```

## Usage

### Chat

Type a message and press Enter. Claude can look movies up and change their ratings on its own:

```
> What's the rating of Die Hard?
> Set the rating of The Goonies to 8.5
```

Only ratings can be changed.

### Mentioning movies

Put `@` before a movie title to include that movie's details in your message. Titles can contain spaces, matching ignores case, and you can mention several movies at once:

```
> Compare @Back to the Future with @Back to the Future Part II
```

### Commands

Type `/` to run a prompt defined by the MCP server:

```
> /summarize_description Ferris Bueller's Day Off
```

`/summarize_description` has Claude summarize the movie's description in 50 words or fewer. The summary is only shown; the stored description doesn't change.

Commands and movie titles autocomplete with Tab, after `/summarize_description ` and after `@`.

## What the MCP server provides

| Kind | Name | What it does |
| --- | --- | --- |
| Tool | `get_movie_by_title` | Looks up movies by title, ignoring case. Returns exact matches if there are any, otherwise up to 20 movies whose title contains the text. |
| Tool | `update_movie_rating` | Sets a movie's rating (0–10, stored with one decimal). Needs the exact title, plus `release_year` if several movies share it. |
| Resource | `movies://titles` | Every movie title, as JSON. |
| Resource | `movies://titles/{title}` | A movie's details, as plain text. The title must be URL-encoded (for example `Die%20Hard`). |
| Prompt | `summarize_description` | Takes a `title` and asks Claude to summarize that movie's description in 50 words or fewer. |

## Development

### Adding or changing movies

Insert rows into the `movies` table. `release_year` must be between 1980 and 1989, and a title can only appear once per year:

```bash
docker compose exec db psql -U mcp mcp_docs -c "INSERT INTO movies (title, release_year, genre, description, rating) VALUES ('Honey, I Shrunk the Kids', 1989, 'Family', 'An inventor accidentally shrinks his children and the neighbors'' kids, who must cross the backyard to get home.', 7.5)"
```

New movies can be mentioned with `@` straight away. Tab autocomplete only picks them up after you restart the chat app.

The seed data lives in `db/init.sql`, which only runs automatically on an empty database. To apply changes to it:

```bash
docker compose down -v && docker compose up -d
```

This deletes the current data, including any rating changes. To keep it, re-run the script on the existing database instead. Only movies that aren't already there are added:

```bash
docker compose exec -T db psql -U mcp mcp_docs < db/init.sql
```

### Testing the server on its own

```bash
uv run mcp_client.py           # connect to the server and print its tools
uv run mcp dev mcp_server.py   # open the server in the MCP Inspector
```

### Linting and type checks

None are set up.

## Troubleshooting

- **`role "mcp" does not exist` or connection errors:** check that `DATABASE_URL` uses port 5433 and that the container is running (`docker compose ps`). Port 5432 may belong to a different, local Postgres.
- **A traceback appears after a typo in a movie title:** the server logs the "not found" error to the terminal before the app prints its short error message. The chat keeps running.
