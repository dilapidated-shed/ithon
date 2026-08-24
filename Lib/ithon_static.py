from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class IType:
    name: str
    args: tuple["IType", ...] = ()

    def __str__(self) -> str:
        if self.name == "union":
            return " | ".join(map(str, self.args))
        if self.name == "callable" and self.args:
            *params, result = self.args
            return f"Callable[[{', '.join(map(str, params))}], {result}]"
        if not self.args:
            return self.name
        return f"{self.name}[{', '.join(map(str, self.args))}]"


UNKNOWN = IType("<unknown>")
ANY = IType("Any")
OBJECT = IType("object")
NONE = IType("None")
BOOL = IType("bool")
INT = IType("int")
FLOAT = IType("float")
COMPLEX = IType("complex")
STR = IType("str")
BYTES = IType("bytes")

_NUMERIC_RANK = {BOOL: 0, INT: 1, FLOAT: 2, COMPLEX: 3}


class StaticTypeError(SyntaxError):
    """Valid Ithon syntax violated Ithon's mandatory static typing."""


def _union(types: Iterable[IType]) -> IType:
    values: list[IType] = []
    for typ in types:
        members = typ.args if typ.name == "union" else (typ,)
        for member in members:
            if member not in values:
                values.append(member)
    if not values:
        return UNKNOWN
    if len(values) == 1:
        return values[0]
    return IType("union", tuple(values))


def is_assignable(actual: IType, expected: IType) -> bool:
    if expected in (ANY, OBJECT) or actual == ANY:
        return True
    if actual == UNKNOWN:
        return True  # only callers with an explicit typed boundary may permit this
    if actual == expected:
        return True
    if expected.name == "union":
        return any(is_assignable(actual, member) for member in expected.args)
    if actual.name == "union":
        return all(is_assignable(member, expected) for member in actual.args)
    if actual in _NUMERIC_RANK and expected in _NUMERIC_RANK:
        return _NUMERIC_RANK[actual] <= _NUMERIC_RANK[expected]
    return actual.name == expected.name and actual.args == expected.args


class Checker:
    def __init__(self, source: str, filename: str = "<ithon>") -> None:
        self.source = source
        self.lines = source.splitlines()
        self.filename = filename
        self.scopes: list[dict[str, IType]] = [{}]
        self.returns: list[IType] = []
        self._install_builtins()

    @property
    def scope(self) -> dict[str, IType]:
        return self.scopes[-1]

    def _install_builtins(self) -> None:
        self.scope.update({
            "None": NONE,
            "True": BOOL,
            "False": BOOL,
            "int": IType("type", (INT,)),
            "float": IType("type", (FLOAT,)),
            "complex": IType("type", (COMPLEX,)),
            "bool": IType("type", (BOOL,)),
            "str": IType("type", (STR,)),
            "bytes": IType("type", (BYTES,)),
            "object": IType("type", (OBJECT,)),
            "range": IType("builtin-range"),
            "print": IType("builtin-print"),
        })

    def lookup(self, name: str) -> IType | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def error(self, node: ast.AST, message: str) -> None:
        lineno = getattr(node, "lineno", 1)
        offset = getattr(node, "col_offset", 0) + 1
        text = self.lines[lineno - 1] if 0 < lineno <= len(self.lines) else None
        raise StaticTypeError(message, (self.filename, lineno, offset, text))

    def parse_annotation(self, node: ast.AST | None) -> IType:
        if node is None:
            return UNKNOWN
        if isinstance(node, ast.Name):
            return {
                "Any": ANY,
                "None": NONE,
                "bool": BOOL,
                "int": INT,
                "float": FLOAT,
                "complex": COMPLEX,
                "str": STR,
                "bytes": BYTES,
                "object": OBJECT,
            }.get(node.id, IType(node.id))
        if isinstance(node, ast.Constant) and node.value is None:
            return NONE
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return _union((self.parse_annotation(node.left), self.parse_annotation(node.right)))
        if isinstance(node, ast.Subscript):
            base = self._annotation_name(node.value)
            if base in {"Optional", "typing.Optional"}:
                return _union((self.parse_annotation(node.slice), NONE))
            if base in {"Callable", "typing.Callable", "collections.abc.Callable"}:
                if not isinstance(node.slice, ast.Tuple) or len(node.slice.elts) != 2:
                    self.error(node, "Callable annotation must be Callable[[args...], result]")
                params_node, result_node = node.slice.elts
                if not isinstance(params_node, (ast.List, ast.Tuple)):
                    self.error(params_node, "Callable parameter list must be written in brackets")
                params = tuple(self.parse_annotation(p) for p in params_node.elts)
                return IType("callable", params + (self.parse_annotation(result_node),))
            args = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            return IType(base, tuple(self.parse_annotation(arg) for arg in args))
        if isinstance(node, ast.Attribute):
            return IType(self._annotation_name(node))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return IType(node.value)
        self.error(node, "unsupported static type annotation")
        raise AssertionError

    def _annotation_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            cur = node
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
                return ".".join(reversed(parts))
        self.error(node, "type annotation must have a named base")
        raise AssertionError

    def check(self, tree: ast.Module) -> None:
        # Declare top-level names before bodies so local calls and class annotations
        # have stable types.
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._declare_function(stmt)
            elif isinstance(stmt, ast.ClassDef):
                self._declare_class(stmt)
        for stmt in tree.body:
            self.check_stmt(stmt)

    def _declare_class(self, node: ast.ClassDef) -> IType:
        instance_type = IType(node.name)
        class_type = IType("type", (instance_type,))
        existing = self.scope.get(node.name)
        if existing is not None and existing != class_type:
            self.error(node, f"'{node.name}' was already declared as {existing}")
        self.scope[node.name] = class_type
        return instance_type

    def _declare_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> IType:
        existing = self.scope.get(node.name)
        if existing is not None and existing.name == "callable":
            return existing
        params: list[IType] = []
        for arg in [*node.args.posonlyargs, *node.args.args]:
            if arg.annotation is None:
                self.error(arg, f"parameter '{arg.arg}' needs a static type")
            params.append(self.parse_annotation(arg.annotation))
        if node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
            self.error(node, "typed varargs and keyword-only parameters are not implemented yet")
        if node.returns is None:
            if node.name == "__init__":
                result = NONE
            else:
                self.error(node, f"function '{node.name}' needs a return type")
        else:
            result = self.parse_annotation(node.returns)
        typ = IType("callable", tuple(params) + (result,))
        self.scope[node.name] = typ
        return typ

    def check_stmt(self, node: ast.stmt) -> None:
        if isinstance(node, ast.ClassDef):
            self._declare_class(node)
            if node.keywords:
                self.error(node, "typed class keywords and metaclasses are not implemented yet")
            if node.decorator_list:
                self.error(node, "typed class decorators are not implemented yet")
            for base in node.bases:
                base_type = self.infer(base)
                if base_type.name not in {"external", "type"}:
                    self.error(base, f"class base must be a type, got {base_type}")

            self.scopes.append({})
            try:
                for stmt in node.body:
                    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self._declare_function(stmt)
                for stmt in node.body:
                    self.check_stmt(stmt)
            finally:
                self.scopes.pop()
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signature = self._declare_function(node)
            params, result = list(signature.args[:-1]), signature.args[-1]
            local = dict(zip((arg.arg for arg in [*node.args.posonlyargs, *node.args.args]), params))
            self.scopes.append(local)
            self.returns.append(result)
            for stmt in node.body:
                self.check_stmt(stmt)
            self.returns.pop()
            self.scopes.pop()
            return
        if isinstance(node, ast.Assign):
            actual = self.infer(node.value)
            if actual == UNKNOWN:
                self.error(node.value, "cannot infer assignment type; add a type annotation")
            for target in node.targets:
                self.assign(target, actual, node)
            return
        if isinstance(node, ast.AnnAssign):
            expected = self.parse_annotation(node.annotation)
            if not isinstance(node.target, ast.Name):
                self.error(node.target, "typed declarations currently require a simple name target")
            current = self.lookup(node.target.id)
            if current is not None and current != expected:
                self.error(node.target, f"'{node.target.id}' was already declared as {current}, not {expected}")
            self.scope[node.target.id] = expected
            if node.value is not None:
                self.require(self.infer(node.value, expected), expected, node.value)
            return
        if isinstance(node, ast.Return):
            if not self.returns:
                self.error(node, "return outside statically typed function")
            expected = self.returns[-1]
            actual = NONE if node.value is None else self.infer(node.value, expected)
            self.require(actual, expected, node)
            return
        if isinstance(node, ast.For):
            iterable = self.infer(node.iter)
            item = INT if iterable.name == "range" else (iterable.args[0] if iterable.args else UNKNOWN)
            if item == UNKNOWN:
                self.error(node.target, "cannot infer loop variable type")
            self.assign(node.target, item, node)
            for stmt in [*node.body, *node.orelse]:
                self.check_stmt(stmt)
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.scope[alias.asname or alias.name.split('.')[0]] = IType("module", (IType(alias.name),))
            return
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    self.error(node, "star imports have no statically knowable bindings")
                self.scope[alias.asname or alias.name] = IType("external")
            return
        if isinstance(node, ast.Expr):
            self.infer(node.value)
            return
        if isinstance(node, ast.If):
            self.infer(node.test)
            for stmt in [*node.body, *node.orelse]:
                self.check_stmt(stmt)
            return
        if isinstance(node, ast.Pass):
            return
        self.error(node, f"static typing for {type(node).__name__} is not implemented")

    def assign(self, target: ast.AST, typ: IType, node: ast.AST) -> None:
        if not isinstance(target, ast.Name):
            self.error(target, "static assignment currently requires a simple name target")
        existing = self.lookup(target.id)
        if existing is None:
            self.scope[target.id] = typ
        else:
            self.require(typ, existing, node, target.id)

    def require(self, actual: IType, expected: IType, node: ast.AST, name: str | None = None) -> None:
        if not is_assignable(actual, expected):
            prefix = f"'{name}' expects" if name else "expected"
            self.error(node, f"{prefix} {expected}, got {actual}")

    def infer(self, node: ast.AST, expected: IType | None = None) -> IType:
        if isinstance(node, ast.Constant):
            value = node.value
            if value is None:
                return NONE
            return {bool: BOOL, int: INT, float: FLOAT, complex: COMPLEX, str: STR, bytes: BYTES}.get(type(value), IType(type(value).__name__))
        if isinstance(node, ast.Name):
            typ = self.lookup(node.id)
            if typ is None:
                self.error(node, f"name '{node.id}' has no static type")
            return typ
        if isinstance(node, ast.BinOp):
            left, right = self.infer(node.left), self.infer(node.right)
            if isinstance(node.op, ast.Div):
                if left in _NUMERIC_RANK and right in _NUMERIC_RANK:
                    return COMPLEX if COMPLEX in (left, right) else FLOAT
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.Pow, ast.FloorDiv)):
                if left in _NUMERIC_RANK and right in _NUMERIC_RANK:
                    return max((left, right), key=_NUMERIC_RANK.__getitem__)
                if isinstance(node.op, ast.Add) and left == right and left in {STR, BYTES}:
                    return left
            self.error(node, f"operator is not statically defined for {left} and {right}")
        if isinstance(node, ast.UnaryOp):
            operand = self.infer(node.operand)
            if isinstance(node.op, (ast.USub, ast.UAdd)) and operand in _NUMERIC_RANK:
                return INT if operand == BOOL else operand
            self.error(node, f"unary operator is not statically defined for {operand}")
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            operand_types = [self.infer(operand) for operand in operands]
            for operator, left, right in zip(node.ops, operand_types, operand_types[1:]):
                if UNKNOWN in {left, right}:
                    self.error(node, "comparison operands need statically known types")
                if isinstance(operator, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    if left in _NUMERIC_RANK and right in _NUMERIC_RANK:
                        continue
                elif isinstance(operator, (ast.Eq, ast.NotEq)):
                    if is_assignable(left, right) or is_assignable(right, left):
                        continue
                self.error(node, f"comparison is not statically defined for {left} and {right}")
            return BOOL
        if isinstance(node, ast.IfExp):
            self.require(self.infer(node.test), BOOL, node.test)
            body = self.infer(node.body, expected)
            otherwise = self.infer(node.orelse, expected)
            return _union((body, otherwise))
        if isinstance(node, ast.List):
            if not node.elts:
                if expected is not None and expected.name == "list" and expected.args:
                    return expected
                self.error(node, "empty list needs an explicit element type")
            return IType("list", (_union(self.infer(elt) for elt in node.elts),))
        if isinstance(node, ast.Lambda):
            if expected is None or expected.name != "callable" or not expected.args:
                self.error(node, "lambda needs a contextual Callable[[...], result] type")
            params, result = expected.args[:-1], expected.args[-1]
            args = [*node.args.posonlyargs, *node.args.args]
            if len(args) != len(params):
                self.error(node, f"lambda expects {len(params)} parameters from its Callable type")
            self.scopes.append(dict(zip((arg.arg for arg in args), params)))
            body = self.infer(node.body, result)
            self.require(body, result, node.body)
            self.scopes.pop()
            return expected
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "range":
                for arg in node.args:
                    self.require(self.infer(arg), INT, arg)
                return IType("range")
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                for arg in node.args:
                    self.infer(arg)
                return NONE
            callee = self.infer(node.func)
            if callee.name == "type" and callee.args:
                for arg in node.args:
                    self.infer(arg)
                return callee.args[0]
            if callee.name == "callable" and callee.args:
                params, result = callee.args[:-1], callee.args[-1]
                if len(node.args) != len(params) or node.keywords:
                    self.error(node, f"call expects {len(params)} positional arguments")
                for arg, param in zip(node.args, params):
                    self.require(self.infer(arg, param), param, arg)
                return result
            if callee.name in {"module", "external"} or callee == UNKNOWN:
                for arg in node.args:
                    self.infer(arg)
                return UNKNOWN
            self.error(node.func, f"{callee} is not statically callable")
        if isinstance(node, ast.Attribute):
            self.infer(node.value)
            return UNKNOWN
        self.error(node, f"cannot infer static type of {type(node).__name__}")
        raise AssertionError


def check_source(source: str, filename: str = "<ithon>") -> ast.Module:
    tree = ast.parse(source, filename=filename, mode="exec")
    checker = Checker(source, filename)
    checker.check(tree)
    return tree


def check_file(path: str) -> ast.Module:
    with open(path, "r", encoding="utf-8") as handle:
        return check_source(handle.read(), path)
