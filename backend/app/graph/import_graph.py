import ast
from pathlib import Path
from typing import Dict, List

import networkx as nx

# Common entry-point file naming conventions — checked before falling back
# to raw in-degree, which is noisy/meaningless on a sparse or unresolved graph.
ENTRY_FILE_NAMES = {"main", "app", "server", "manage", "cli", "__main__"}


def build_import_graph(repo_path: Path) -> nx.DiGraph:
    """Build a module-level import graph for a Python codebase.

    Each node is a module path; each edge A -> B means A imports B.
    Intentionally skips third-party imports — only tracks intra-repo deps.
    """
    graph = nx.DiGraph()
    py_files = list(repo_path.rglob("*.py"))

    # Full dotted path from repo root, e.g. "python.datasources.data_source".
    module_names = {
        f.relative_to(repo_path).with_suffix("").as_posix().replace("/", "."): f
        for f in py_files
    }

    # Real repos very often add a subdirectory (python/, src/, app/) to
    # sys.path, so internal imports DON'T include that prefix — e.g. code
    # imports "datasources.data_source" even though the file lives at
    # "python/datasources/data_source.py". An exact full-path match would
    # silently resolve zero edges in that case. Indexing every dotted
    # *suffix* of each module path lets "datasources.data_source" resolve
    # to "python.datasources.data_source" without hardcoding the root name.
    suffix_lookup: Dict[str, str] = {}
    for dotted in module_names:
        parts = dotted.split(".")
        for i in range(len(parts)):
            suffix = ".".join(parts[i:])
            suffix_lookup.setdefault(suffix, dotted)

    for module, path in module_names.items():
        graph.add_node(module)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                target = suffix_lookup.get(name)
                if target and target != module:
                    graph.add_edge(module, target)

    return graph


def summarize_graph(graph: nx.DiGraph, top_n: int = 10) -> Dict[str, List[str]]:
    """Cheap architecture signal: which modules are most depended-on (hubs)
    and which look like real entry points."""
    in_degrees = sorted(graph.in_degree, key=lambda x: x[1], reverse=True)
    # Filter out zero-count noise — if nothing has real fan-in yet, an
    # honest empty list is better signal than padding with meaningless nodes.
    most_imported = [n for n, d in in_degrees if d > 0][:top_n]

    named_entries = [n for n in graph.nodes if n.rsplit(".", 1)[-1] in ENTRY_FILE_NAMES]
    if named_entries:
        entry_points = named_entries[:top_n]
    else:
        entry_points = [n for n, d in graph.in_degree if d == 0][:top_n]

    return {
        "most_imported": most_imported,
        "likely_entry_points": entry_points,
    }