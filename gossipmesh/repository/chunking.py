from typing import List, Dict, Any
import ast


def chunk_python_code(code: str, filepath: str) -> List[Dict[str, Any]]:
    """
    Splits Python code into symbol-level chunks (functions, classes).
    This is a basic AST-based chunker.
    """
    chunks = []
    try:
        tree = ast.parse(code, filename=filepath)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line

                # Extract the source code for this node
                lines = code.splitlines()
                node_code = "\n".join(lines[start_line - 1 : end_line])

                chunks.append(
                    {
                        "symbol_name": node.name,
                        "type": type(node).__name__,
                        "content": node_code,
                        "start_line": start_line,
                        "end_line": end_line,
                        "filepath": filepath,
                    }
                )

        # If no major symbols found, just return the whole file as one chunk
        if not chunks:
            chunks.append(
                {
                    "symbol_name": "module",
                    "type": "Module",
                    "content": code,
                    "start_line": 1,
                    "end_line": len(code.splitlines()),
                    "filepath": filepath,
                }
            )

    except SyntaxError:
        # Fallback to naive line chunking if syntax is invalid
        lines = code.splitlines()
        chunks.append(
            {
                "symbol_name": "unknown",
                "type": "Text",
                "content": code,
                "start_line": 1,
                "end_line": len(lines),
                "filepath": filepath,
            }
        )

    return chunks
