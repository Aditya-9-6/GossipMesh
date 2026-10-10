from typing import List, Dict, Any
import ast

def chunk_python_code(code: str, filepath: str) -> List[Dict[str, Any]]:
    """Return chunks for top-level Python functions and classes.

    Each chunk includes its symbol name, AST node type, source content,
    filepath, and inclusive 1-based line bounds. Decorator lines are excluded;
    nested symbols remain inside their enclosing chunk. The filepath labels
    the supplied source and is not read from disk.

    Return the whole source as a Module chunk if no symbols exist, or as a
    Text chunk on SyntaxError. Empty source has bounds 1 through 0.
    """
    chunks = []
    try:
        tree = ast.parse(code, filename=filepath)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line

                # Extract the source code for this node
                lines = code.splitlines()
                node_code = "\n".join(lines[start_line - 1:end_line])

                chunks.append({
                    "symbol_name": node.name,
                    "type": type(node).__name__,
                    "content": node_code,
                    "start_line": start_line,
                    "end_line": end_line,
                    "filepath": filepath
                })

        # If no major symbols found, just return the whole file as one chunk
        if not chunks:
            chunks.append({
                "symbol_name": "module",
                "type": "Module",
                "content": code,
                "start_line": 1,
                "end_line": len(code.splitlines()),
                "filepath": filepath
            })

    except SyntaxError:
        # Fallback to naive line chunking if syntax is invalid
        lines = code.splitlines()
        chunks.append({
            "symbol_name": "unknown",
            "type": "Text",
            "content": code,
            "start_line": 1,
            "end_line": len(lines),
            "filepath": filepath
        })

    return chunks
