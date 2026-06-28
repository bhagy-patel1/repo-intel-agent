import shutil
import subprocess
from pathlib import Path
from typing import Iterator, Tuple

IGNORED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".yaml", ".yml", ".toml"}
MAX_FILE_BYTES = 200_000  # skip anything bigger than ~200KB, almost never hand-written source


def clone_repo(repo_url: str, dest_dir: str) -> Path:
    """Shallow-clone a repo. Re-clones if dest_dir already exists."""
    dest = Path(dest_dir)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(dest)], check=True)
    return dest


def walk_source_files(repo_path: Path) -> Iterator[Tuple[str, str]]:
    """Yield (relative_path, content) for every file worth indexing."""
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix not in ALLOWED_EXTENSIONS:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        yield str(path.relative_to(repo_path)), content
