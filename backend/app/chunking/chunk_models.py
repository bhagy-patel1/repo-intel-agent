from typing import Optional

from pydantic import BaseModel


class Chunk(BaseModel):
    """A single retrievable unit of code or docs from a repository."""

    chunk_id: str
    repo_id: str
    file_path: str
    chunk_type: str  # "function" | "class" | "module" | "doc"
    name: Optional[str] = None
    start_line: int
    end_line: int
    content: str

    def to_search_text(self) -> str:
        """Text used for embedding + BM25 indexing."""
        header = f"# {self.file_path}"
        if self.name:
            header += f" :: {self.chunk_type} {self.name}"
        return f"{header}\n{self.content}"
