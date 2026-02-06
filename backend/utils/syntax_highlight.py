"""
Syntax highlighting for Python code using tree-sitter.

Returns highlight ranges (0-based line/column) with capture names from
tree-sitter-python highlights query (e.g. "keyword", "function", "string").
"""

from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
from typing import Any

from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython


# Pasted verbatim from tree-sitter-python queries/highlights.scm
# https://raw.githubusercontent.com/tree-sitter/tree-sitter-python/refs/heads/master/queries/highlights.scm
PYTHON_HIGHLIGHTS_QUERY = """
; Identifier naming conventions

(identifier) @variable

((identifier) @constructor
 (#match? @constructor "^[A-Z]"))

((identifier) @constant
 (#match? @constant "^[A-Z][A-Z_]*$"))

; Function calls

(decorator) @function
(decorator
  (identifier) @function)

(call
  function: (attribute attribute: (identifier) @function.method))
(call
  function: (identifier) @function)

; Builtin functions

((call
  function: (identifier) @function.builtin)
 (#match?
   @function.builtin
   "^(abs|all|any|ascii|bin|bool|breakpoint|bytearray|bytes|callable|chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|property|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip|__import__)$"))

; Function definitions

(function_definition
  name: (identifier) @function)

(attribute attribute: (identifier) @property)
(type (identifier) @type)

; Literals

[
  (none)
  (true)
  (false)
] @constant.builtin

[
  (integer)
  (float)
] @number

(comment) @comment
(string) @string
(escape_sequence) @escape

(interpolation
  "{" @punctuation.special
  "}" @punctuation.special) @embedded

[
  "-"
  "-="
  "!="
  "*"
  "**"
  "**="
  "*="
  "/"
  "//"
  "//="
  "/="
  "&"
  "&="
  "%"
  "%="
  "^"
  "^="
  "+"
  "->"
  "+="
  "<"
  "<<"
  "<<="
  "<="
  "<>"
  "="
  ":="
  "=="
  ">"
  ">="
  ">>"
  ">>="
  "|"
  "|="
  "~"
  "@="
  "and"
  "in"
  "is"
  "not"
  "or"
  "is not"
  "not in"
] @operator

[
  "as"
  "assert"
  "async"
  "await"
  "break"
  "class"
  "continue"
  "def"
  "del"
  "elif"
  "else"
  "except"
  "exec"
  "finally"
  "for"
  "from"
  "global"
  "if"
  "import"
  "lambda"
  "nonlocal"
  "pass"
  "print"
  "raise"
  "return"
  "try"
  "while"
  "with"
  "yield"
  "match"
  "case"
] @keyword
"""


@lru_cache(maxsize=1)
def _ts_objects() -> tuple[Language, Parser, Query]:
    lang = Language(tspython.language())
    parser = Parser(lang)
    query = Query(lang, PYTHON_HIGHLIGHTS_QUERY)
    return lang, parser, query


def _build_line_start_bytes(code_bytes: bytes) -> list[int]:
    # Byte offsets where each line starts (0-based).
    starts = [0]
    i = 0
    while True:
        j = code_bytes.find(b"\n", i)
        if j == -1:
            break
        starts.append(j + 1)
        i = j + 1
    return starts


def _line_for_byte(line_starts: list[int], byte_offset: int) -> int:
    # largest line_start <= byte_offset
    return bisect_right(line_starts, byte_offset) - 1


def _utf16_col_for_byte_in_line(line_bytes: bytes, byte_col: int) -> int:
    """
    Convert a UTF-8 byte column within a single line to a UTF-16 code unit column.

    Tree-sitter node byte offsets should always land on UTF-8 character boundaries,
    so decoding the prefix is safe (errors='strict').
    """
    prefix = line_bytes[:byte_col]
    s = prefix.decode("utf-8", errors="strict")
    return len(s.encode("utf-16-le")) // 2


def _byte_offset_to_line_utf16(
    code_bytes: bytes, line_starts: list[int], byte_offset: int
) -> tuple[int, int]:
    line = _line_for_byte(line_starts, byte_offset)
    line_start = line_starts[line]
    line_end = line_starts[line + 1] if line + 1 < len(line_starts) else len(code_bytes)

    line_bytes = code_bytes[line_start:line_end]
    byte_col = byte_offset - line_start
    utf16_col = _utf16_col_for_byte_in_line(line_bytes, byte_col)
    return line, utf16_col


def _string_contains_interpolation(node: Any) -> bool:
    """Return True if this node has an interpolation descendant (e.g. f-string content)."""
    if node.type == "interpolation":
        return True
    for child in node.children:
        if _string_contains_interpolation(child):
            return True
    return False


def _collect_fstring_ranges(node: Any) -> set[tuple[int, int]]:
    """Collect (start_byte, end_byte) of string nodes that contain at least one interpolation (f-strings)."""
    result: set[tuple[int, int]] = set()
    if node.type == "string":
        if _string_contains_interpolation(node):
            result.add((node.start_byte, node.end_byte))
        return result
    for child in node.children:
        result.update(_collect_fstring_ranges(child))
    return result


def _is_triple_quoted_string(code_bytes: bytes, start_byte: int) -> bool:
    """Return True if the string at start_byte is triple-quoted (\"\"\" or ''')."""
    if start_byte + 3 > len(code_bytes):
        return False
    prefix = code_bytes[start_byte : start_byte + 3]
    return prefix == b'"""' or prefix == b"'''"


def get_python_highlights(code: str) -> list[dict[str, Any]]:
    """
    Return syntax highlight ranges for Python source code.

    Output columns are UTF-16 code units (compatible with JS string indexing).
    Each item has 0-based startLine, startCol, endLine, endCol, type, and content
    (the source text for that range).
    """
    if not code:
        return []

    # Tree-sitter parses bytes; UTF-8 is the correct encoding for Python source text storage here.
    code_bytes = code.encode("utf-8")

    try:
        _lang, parser, query = _ts_objects()
    except Exception:
        return []

    tree = parser.parse(code_bytes)

    cursor = QueryCursor(query)
    # NOTE: API varies slightly by tree-sitter Python binding version.
    # Some return a list of (node, capture_index), others return dicts.
    # We handle the common "list of (node, capture_name)" case by using query.captures.
    matches = cursor.captures(tree.root_node)

    # Build line start table once per call
    line_starts = _build_line_start_bytes(code_bytes)

    # F-string post-processing: mark strings that contain interpolation so the frontend can style them differently.
    fstring_ranges = _collect_fstring_ranges(tree.root_node)

    result: list[dict[str, Any]] = []

    # Two common shapes:
    # 1) dict: {capture_name: [nodes]}
    # 2) list: [(node, capture_name)] or [(node, capture_index)]
    if isinstance(matches, dict):
        items = ((cap, node) for cap, nodes in matches.items() for node in nodes)
    else:
        # try to normalize list/iterable
        def _iter_items():
            for item in matches:
                if len(item) == 2:
                    a, b = item
                    # Heuristic: if second is int -> capture index, else name
                    if isinstance(b, int):
                        cap_name = query.capture_names[b]
                        node = a
                    else:
                        node = a
                        cap_name = b
                    yield cap_name, node

        items = _iter_items()

    for capture_name, node in items:
        sl, sc = _byte_offset_to_line_utf16(code_bytes, line_starts, node.start_byte)
        el, ec = _byte_offset_to_line_utf16(code_bytes, line_starts, node.end_byte)

        # Skip empty ranges (can happen with error nodes / weird captures)
        if (sl, sc) == (el, ec):
            continue

        content = code_bytes[node.start_byte : node.end_byte].decode("utf-8")

        # Use distinct types for f-strings and triple-quoted strings so the frontend can style them differently.
        highlight_type = capture_name
        if capture_name == "string":
            is_fstring = (node.start_byte, node.end_byte) in fstring_ranges
            is_triple_quoted = _is_triple_quoted_string(code_bytes, node.start_byte)

            if is_fstring and is_triple_quoted:
                highlight_type = "triple-quoted-f-string"
            elif is_fstring:
                highlight_type = "f-string"
            elif is_triple_quoted:
                highlight_type = "triple-quoted-string"

        result.append(
            {
                "startLine": sl,
                "startCol": sc,
                "endLine": el,
                "endCol": ec,
                "type": highlight_type,
                "content": content,
            }
        )

    result.sort(
        key=lambda r: (r["startLine"], r["startCol"], r["endLine"], r["endCol"])
    )
    return result
