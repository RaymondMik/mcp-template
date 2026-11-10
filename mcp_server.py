
from pydantic import Field
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

# TASK: Write a tool to read a doc
@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document"
)

def read_document(
    doc_id: str = Field(description="The ID of the document to read")
):
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    return docs[doc_id]

# TASK: Write a tool to edit a doc
@mcp.tool(
    name="write_doc_contents",
    description="Edit a document by replacing a string in the documents content",
)

def edit_document(
    doc_id: str = Field(description="The ID of the document that will be edited"),
    old_string: str = Field(description="The text to replace. Must macth exactly, including white space"),
    new_string: str = Field(description="The new text to add in place of the old text")
):
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    
    docs[doc_id] = docs[doc_id].replace(old_string, new_string)

# TASK: Write a resource to return all doc id's
@mcp.resource(
    "docs://documents",
    mime_type="application/json"
)

def list_docs() -> list[str]:
    return list(docs.keys())

# TASK: Write a resource to return the contents of a particular doc
@mcp.resource(
    "docs://documents/{doc_id}",
    mime_type="text/plain"
)

def get_doc_contents(
    doc_id: str
) -> str:
    if doc_id not in docs:
        raise ValueError(f"Document with ID '{doc_id}' not found.")
    return docs[doc_id]

# TASK: Write a prompt to rewrite a doc in markdown format
# TASK: Write a prompt to summarize a doc

if __name__ == "__main__":
    mcp.run(transport="stdio")
