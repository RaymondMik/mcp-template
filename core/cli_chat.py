from typing import List, Tuple
from urllib.parse import quote
from mcp.types import Prompt, PromptMessage
from anthropic.types import MessageParam

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient


class CliChat(Chat):
    def __init__(
        self,
        doc_client: MCPClient,
        clients: dict[str, MCPClient],
        claude_service: Claude,
    ):
        super().__init__(clients=clients, claude_service=claude_service)

        self.doc_client: MCPClient = doc_client

    async def list_prompts(self) -> list[Prompt]:
        return await self.doc_client.list_prompts()

    async def list_movie_titles(self) -> list[str]:
        return await self.doc_client.read_resource("movies://titles")

    async def get_movie(self, title: str) -> str:
        # Titles contain spaces and punctuation; encode them as one path segment.
        return await self.doc_client.read_resource(
            f"movies://titles/{quote(title, safe='')}"
        )

    async def get_prompt(
        self, command: str, title: str
    ) -> list[PromptMessage]:
        return await self.doc_client.get_prompt(command, {"title": title})

    async def _extract_resources(self, query: str) -> str:
        # Titles can span several words ("@Back to the Future Part II"), so look
        # for "@<title>" in the query instead of splitting it on spaces. Longest
        # titles go first, so "@Back to the Future Part II" isn't also read as
        # "@Back to the Future".
        remaining = query.lower()
        mentioned: list[Tuple[str, str]] = []

        titles = await self.list_movie_titles()
        for title in sorted(titles, key=len, reverse=True):
            needle = f"@{title.lower()}"
            if needle in remaining:
                remaining = remaining.replace(needle, " ")
                mentioned.append((title, await self.get_movie(title)))

        return "".join(
            f'\n<movie title="{title}">\n{content}\n</movie>\n'
            for title, content in mentioned
        )

    async def _process_command(self, query: str) -> bool:
        if not query.startswith("/"):
            return False

        command, _, title = query[1:].partition(" ")
        title = title.strip()
        if not title:
            raise ValueError(f"Usage: /{command} <movie title>")

        messages = await self.doc_client.get_prompt(command, {"title": title})

        self.messages += convert_prompt_messages_to_message_params(messages)
        return True

    async def _process_query(self, query: str):
        if await self._process_command(query):
            return

        added_resources = await self._extract_resources(query)

        prompt = f"""
        The user has a question:
        <query>
        {query}
        </query>

        The following context may be useful in answering their question:
        <context>
        {added_resources}
        </context>

        Note the user's query might mention movies like "@Die Hard". The "@" is only
        included as a way of mentioning the movie. The actual title of the movie would be "Die Hard".
        If the movie's details are included in this prompt, you don't need to use an additional tool to look it up.
        Answer the user's question directly and concisely. Start with the exact information they need. 
        Don't refer to or mention the provided context in any way - just use it to inform your answer.
        """

        self.messages.append({"role": "user", "content": prompt})


def convert_prompt_message_to_message_param(
    prompt_message: "PromptMessage",
) -> MessageParam:
    role = "user" if prompt_message.role == "user" else "assistant"

    content = prompt_message.content

    # Check if content is a dict-like object with a "type" field
    if isinstance(content, dict) or hasattr(content, "__dict__"):
        content_type = (
            content.get("type", None)
            if isinstance(content, dict)
            else getattr(content, "type", None)
        )
        if content_type == "text":
            content_text = (
                content.get("text", "")
                if isinstance(content, dict)
                else getattr(content, "text", "")
            )
            return {"role": role, "content": content_text}

    if isinstance(content, list):
        text_blocks = []
        for item in content:
            # Check if item is a dict-like object with a "type" field
            if isinstance(item, dict) or hasattr(item, "__dict__"):
                item_type = (
                    item.get("type", None)
                    if isinstance(item, dict)
                    else getattr(item, "type", None)
                )
                if item_type == "text":
                    item_text = (
                        item.get("text", "")
                        if isinstance(item, dict)
                        else getattr(item, "text", "")
                    )
                    text_blocks.append({"type": "text", "text": item_text})

        if text_blocks:
            return {"role": role, "content": text_blocks}

    return {"role": role, "content": ""}


def convert_prompt_messages_to_message_params(
    prompt_messages: List[PromptMessage],
) -> List[MessageParam]:
    return [
        convert_prompt_message_to_message_param(msg) for msg in prompt_messages
    ]
