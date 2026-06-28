import ast
from pathlib import Path
from typing import List

from app.chunking.chunk_models import Chunk


def chunk_python_file(repo_id: str, file_path: str, source: str) -> List[Chunk]:
    """Split a Python file into function- and class-level chunks.

    Falls back to one whole-file chunk if the source doesn't parse
    (syntax errors, partial files, etc.) so ingestion never hard-fails.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [_whole_file_chunk(repo_id, file_path, source)]

    lines = source.splitlines()
    chunks: List[Chunk] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            content = "\n".join(lines[start - 1:end])
            chunk_type = "class" if isinstance(node, ast.ClassDef) else "function"
            chunks.append(
                Chunk(
                    chunk_id=f"{file_path}:{node.name}:{start}",
                    repo_id=repo_id,
                    file_path=file_path,
                    chunk_type=chunk_type,
                    name=node.name,
                    start_line=start,
                    end_line=end,
                    content=content,
                )
            )

    if not chunks:
        chunks.append(_whole_file_chunk(repo_id, file_path, source))

    return chunks


def chunk_generic_file(repo_id: str, file_path: str, source: str, max_lines: int = 80) -> List[Chunk]:
    """Fallback chunker for non-Python files: fixed-size line windows.

    Good enough for README/config/markdown until you add a real
    multi-language parser (tree-sitter) in a later pass.
    """
    lines = source.splitlines()
    chunks = []
    for i in range(0, len(lines), max_lines):
        window = lines[i:i + max_lines]
        chunks.append(
            Chunk(
                chunk_id=f"{file_path}:{i}",
                repo_id=repo_id,
                file_path=file_path,
                chunk_type="doc",
                start_line=i + 1,
                end_line=i + len(window),
                content="\n".join(window),
            )
        )
    return chunks


def chunk_file(repo_id: str, file_path: str, source: str) -> List[Chunk]:
    if Path(file_path).suffix == ".py":
        return chunk_python_file(repo_id, file_path, source)
    return chunk_generic_file(repo_id, file_path, source)


def _whole_file_chunk(repo_id: str, file_path: str, source: str) -> Chunk:
    lines = source.splitlines()
    return Chunk(
        chunk_id=f"{file_path}:0",
        repo_id=repo_id,
        file_path=file_path,
        chunk_type="module",
        start_line=1,
        end_line=max(len(lines), 1),
        content=source,
    )
