import ast

from collections import OrderedDict


def _get_parent_class(node, tree):
    for parent in ast.walk(tree):
        if isinstance(parent, ast.ClassDef):
            for child in parent.body:
                if child == node:
                    return parent.name
    return None


def get_defined_function_names(code: str) -> set[str]:
    """
    Get names of functions or methods defined in the code.

    Args:
        code (str): Python source code as a string

    Returns:
        set[str]: Set of function and method names defined in the code.
                 Methods are prefixed with their class name (e.g., "ClassName.method_name")
    """
    function_names = set()

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parent_class = _get_parent_class(node, tree)
                if parent_class:
                    function_names.add(f"{parent_class}.{node.name}")
                else:
                    function_names.add(node.name)
    except SyntaxError:
        pass

    return function_names


def get_function_calls(
    code: str, only_defined_in_code: bool = True
) -> dict[int, list[str]]:
    """
    Get function calls in the code, optionally filtered to only calls to defined functions.

    Args:
        code (str): Python source code as a string
        only_defined_in_code (bool): If True, filters calls to only functions defined in the code.
                                    If False, returns all function calls.

    Returns:
        dict[int, list[str]]: Dictionary mapping line numbers to lists of function call names.
    """
    defined_names = get_defined_function_names(code) if only_defined_in_code else None

    call_dict = {}

    def _extract_call_name(func_node):
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return func_node.attr
        return None

    def _get_full_call_name(call_name, defined_names):
        if defined_names is None:
            return call_name
        if call_name in defined_names:
            return call_name
        # Check if it matches any method (ClassName.method_name)
        for defined_name in defined_names:
            if defined_name.endswith(f".{call_name}"):
                return defined_name
        return None

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = _extract_call_name(node.func)
                if call_name:
                    full_name = _get_full_call_name(call_name, defined_names)
                    if full_name:
                        line_number = node.lineno
                        if line_number not in call_dict:
                            call_dict[line_number] = []
                        call_dict[line_number].append(full_name)
    except SyntaxError:
        pass

    # sort by line number
    call_dict = dict(OrderedDict(sorted(call_dict.items())))
    return call_dict


def get_function_ranges(code: str) -> list[dict]:
    """
    Get function and class ranges (0-based start/end lines) in source order.
    Uses AST so multi-line strings and nested blocks are handled correctly.

    Returns:
        list[dict]: [{"name", "type", "startLine", "endLine"}, ...]
        type is "def", "async def", or "class".
    """
    result: list[dict] = []

    def _collect_in_order(body: list) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if isinstance(node, ast.AsyncFunctionDef):
                    type_str = "async def"
                elif isinstance(node, ast.FunctionDef):
                    type_str = "def"
                else:
                    type_str = "class"
                end_lineno = getattr(node, "end_lineno", None)
                if end_lineno is None and getattr(node, "body", None):
                    end_lineno = max(
                        getattr(b, "end_lineno", b.lineno) for b in node.body
                    )
                if end_lineno is None:
                    end_lineno = node.lineno
                result.append(
                    {
                        "name": node.name,
                        "type": type_str,
                        "startLine": node.lineno - 1,
                        "endLine": end_lineno - 1,
                    }
                )
                _collect_in_order(node.body)

    try:
        tree = ast.parse(code)
        _collect_in_order(tree.body)
    except SyntaxError:
        pass

    # Include up to 2 trailing blank lines in each range when present
    lines = code.split("\n")
    for i, item in enumerate(result):
        end = item["endLine"]
        next_start = result[i + 1]["startLine"] if i + 1 < len(result) else len(lines)
        for _ in range(2):
            if end + 1 >= next_start:
                break
            if end + 1 < len(lines) and lines[end + 1].strip() == "":
                end += 1
            else:
                break
        result[i]["endLine"] = end

    return result
