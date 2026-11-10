
import os
from urllib.parse import unquote
from dotenv import load_dotenv
from pydantic import Field
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

# The MCP stdio client does not pass the parent's environment to this
# subprocess, so load DATABASE_URL from .env here.
load_dotenv()

mcp = FastMCP("DocumentMCP", log_level="ERROR")

pool = AsyncConnectionPool(os.environ["DATABASE_URL"], open=False)


async def _pool() -> AsyncConnectionPool:
    """Open the connection pool on first use."""
    if pool.closed:
        await pool.open()
    return pool


async def _movies_with_title(title: str) -> list[dict]:
    """All movies whose title matches exactly (case-insensitive)."""
    async with (await _pool()).connection() as conn:
        cur = await conn.cursor(row_factory=dict_row).execute(
            """
            SELECT title, release_year, genre, description, rating::float AS rating
            FROM movies
            WHERE lower(title) = lower(%s)
            ORDER BY release_year
            """,
            (title.strip(),),
        )
        rows = await cur.fetchall()
    if not rows:
        raise ValueError(f"No movie titled '{title}' found.")
    return rows


def _format_movie(movie: dict) -> str:
    return (
        f"Title: {movie['title']}\n"
        f"Year: {movie['release_year']}\n"
        f"Genre: {movie['genre']}\n"
        f"Rating: {movie['rating']}/10\n"
        f"Description: {movie['description']}"
    )


@mcp.tool(
    name="get_movie_by_title",
    description=(
        "Look up 1980s movies by title (case-insensitive). Returns exact title "
        "matches if there are any, otherwise movies whose title contains the "
        "given text. Each result has title, release_year, genre, description "
        "and rating (0-10)."
    ),
)
async def get_movie_by_title(
    title: str = Field(description="The movie title, or part of it, to search for")
) -> list[dict]:
    title = title.strip()
    if not title:
        raise ValueError("Title must not be empty.")

    async with (await _pool()).connection() as conn:
        cur = await conn.cursor(row_factory=dict_row).execute(
            """
            SELECT title, release_year, genre, description, rating::float AS rating
            FROM movies
            WHERE title ILIKE '%%' || %(pattern)s || '%%'
            ORDER BY lower(title) = lower(%(title)s) DESC, release_year, title
            LIMIT 20
            """,
            {
                "title": title,
                # Escape LIKE wildcards so they match literally.
                "pattern": title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_"),
            },
        )
        rows = await cur.fetchall()

    exact = [r for r in rows if r["title"].lower() == title.lower()]
    if exact:
        return exact
    if not rows:
        raise ValueError(f"No movie found with a title matching '{title}'.")
    return rows


@mcp.tool(
    name="update_movie_rating",
    description=(
        "Change the rating of a movie, identified by its exact title "
        "(case-insensitive). Only the rating can be changed. If several "
        "movies share the title, release_year is required. Returns the "
        "updated movie."
    ),
)
async def update_movie_rating(
    title: str = Field(description="The exact title of the movie to update"),
    rating: float = Field(ge=0, le=10, description="The new rating, from 0 to 10 (stored with one decimal)"),
    release_year: int | None = Field(
        default=None,
        description="Release year, only needed when several movies share the title",
    ),
) -> dict:
    title = title.strip()
    async with (await _pool()).connection() as conn:
        cur = await conn.cursor(row_factory=dict_row).execute(
            """
            SELECT id, title, release_year FROM movies
            WHERE lower(title) = lower(%(title)s)
              AND (%(year)s::int IS NULL OR release_year = %(year)s::int)
            """,
            {"title": title, "year": release_year},
        )
        matches = await cur.fetchall()

        if not matches:
            year = f" ({release_year})" if release_year is not None else ""
            raise ValueError(
                f"No movie titled '{title}'{year} found. Use get_movie_by_title to find the exact title."
            )
        if len(matches) > 1:
            years = ", ".join(str(m["release_year"]) for m in matches)
            raise ValueError(
                f"Several movies are titled '{title}' ({years}). Pass release_year to choose one."
            )

        cur = await conn.cursor(row_factory=dict_row).execute(
            """
            UPDATE movies SET rating = round(%(rating)s::numeric, 1)
            WHERE id = %(id)s
            RETURNING title, release_year, genre, description, rating::float AS rating
            """,
            {"rating": rating, "id": matches[0]["id"]},
        )
        return await cur.fetchone()


@mcp.resource(
    "movies://titles",
    mime_type="application/json"
)
async def list_movie_titles() -> list[str]:
    async with (await _pool()).connection() as conn:
        cur = await conn.execute("SELECT DISTINCT title FROM movies ORDER BY title")
        return [row[0] for row in await cur.fetchall()]


# Titles contain spaces and punctuation, so clients percent-encode them in the
# URI (e.g. movies://titles/Die%20Hard). FastMCP passes the raw path segment
# through, so decode it here.
@mcp.resource(
    "movies://titles/{title}",
    mime_type="text/plain"
)
async def get_movie(title: str) -> str:
    movies = await _movies_with_title(unquote(title))
    return "\n\n".join(_format_movie(m) for m in movies)


@mcp.prompt(
    name="summarize_description",
    description="Summarize a movie's description in 50 words or fewer"
)
async def summarize_description(
    title: str = Field(description="The exact title of the movie to summarize")
) -> list[base.Message]:
    movies = await _movies_with_title(title)
    details = "\n\n".join(_format_movie(m) for m in movies)

    prompt = f"""
    Summarize the description of the movie below in 50 words or fewer.

    <movie>
    {details}
    </movie>

    Reply with only the summary. Keep it accurate to the stored description
    and don't invent plot details. If several movies are listed, write one
    summary per movie, each labeled with its title and year.
    The stored description must not be changed, so don't call any tools.
    """

    return [base.UserMessage(prompt)]

if __name__ == "__main__":
    mcp.run(transport="stdio")
