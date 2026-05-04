from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "swallow"


def src_py_files() -> list[Path]:
    return sorted(path for path in SRC_ROOT.rglob("*.py") if path.is_file())


def relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Attribute):
        return [target.attr]
    if isinstance(target, ast.Subscript):
        names = target_names(target.value)
        key = target.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            names.append(key.value)
        return names
    if isinstance(target, ast.Tuple | ast.List):
        names: list[str] = []
        for item in target.elts:
            names.extend(target_names(item))
        return names
    return []


def constant_strings(node: ast.AST) -> list[str]:
    return [item.value for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)]


def event_type_refs(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.IfExp):
        return event_type_refs(node.body) | event_type_refs(node.orelse)
    return set()


def function_named(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function not found: {name}")


def fastapi_route_path(decorator: ast.AST, method: str) -> str:
    if not isinstance(decorator, ast.Call):
        return ""
    if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != method:
        return ""
    if not decorator.args:
        return ""
    path_arg = decorator.args[0]
    if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
        return path_arg.value
    return ""


def is_httpx_client_constructor(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"Client", "AsyncClient"}
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "httpx"
    )


def collect_httpx_client_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and is_httpx_client_constructor(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and is_httpx_client_constructor(node.value):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.With | ast.AsyncWith):
            for item in node.items:
                if is_httpx_client_constructor(item.context_expr) and isinstance(item.optional_vars, ast.Name):
                    names.add(item.optional_vars.id)
    return names


def chat_completion_url_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "/chat/completions" in node.value
    return isinstance(node, ast.Call) and call_name(node) == "resolve_new_api_chat_completions_url"


def post_call_url_arg(call: ast.Call) -> ast.AST | None:
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg == "url":
            return keyword.value
    return None


def is_httpx_post_call(call: ast.Call, httpx_client_names: set[str]) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "post":
        return False
    receiver = call.func.value
    if isinstance(receiver, ast.Name):
        return receiver.id == "httpx" or receiver.id in httpx_client_names
    return False
