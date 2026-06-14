from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

# Base
class Node: pass

# Program
@dataclass
class Program(Node):
    body: List[Any]

# Statements
@dataclass
class VarDecl(Node):
    kind: str  # 'let','const','var'
    declarations: List[tuple]  # list of (name, init_expr)

@dataclass
class Block(Node):
    body: List[Any]

@dataclass
class ExpressionStatement(Node):
    expression: Any

@dataclass
class If(Node):
    test: Any
    consequent: Any
    alternate: Optional[Any] = None

@dataclass
class While(Node):
    test: Any
    body: Any

@dataclass
class DoWhile(Node):
    body: Any
    test: Any

@dataclass
class For(Node):
    init: Optional[Any]
    test: Optional[Any]
    update: Optional[Any]
    body: Any

@dataclass
class ForIn(Node):
    kind: Optional[str]
    var_name: str
    iterable: Any
    body: Any

@dataclass
class ForOf(Node):
    kind: Optional[str]
    var_name: str
    iterable: Any
    body: Any

@dataclass
class Return(Node):
    argument: Optional[Any]

@dataclass
class Break(Node): pass
@dataclass
class Continue(Node): pass

@dataclass
class Throw(Node):
    argument: Any

@dataclass
class TryCatch(Node):
    block: Any
    catch_param: Optional[str]
    handler: Optional[Any]
    finalizer: Optional[Any]

@dataclass
class Switch(Node):
    discriminant: Any
    cases: List[tuple]  # (test_or_None, [stmts])

@dataclass
class FunctionDecl(Node):
    name: str
    params: List[Any]   # list of dicts: {'name':..., 'rest':bool, 'default':expr}
    body: Any

# Expressions
@dataclass
class Literal(Node):
    value: Any

@dataclass
class Identifier(Node):
    name: str

@dataclass
class TemplateLiteral(Node):
    value: str  # placeholder, we lower to string

@dataclass
class ArrayLit(Node):
    elements: List[Any]  # may include Spread

@dataclass
class ObjectLit(Node):
    properties: List[tuple]  # (key, value, computed:bool, shorthand:bool, spread:bool)

@dataclass
class Spread(Node):
    argument: Any

@dataclass
class Unary(Node):
    op: str
    argument: Any
    prefix: bool = True

@dataclass
class Update(Node):
    op: str  # '++' or '--'
    argument: Any
    prefix: bool

@dataclass
class Binary(Node):
    op: str
    left: Any
    right: Any

@dataclass
class Logical(Node):
    op: str
    left: Any
    right: Any

@dataclass
class Assign(Node):
    op: str
    target: Any
    value: Any

@dataclass
class Conditional(Node):
    test: Any
    consequent: Any
    alternate: Any

@dataclass
class Call(Node):
    callee: Any
    arguments: List[Any]

@dataclass
class New(Node):
    callee: Any
    arguments: List[Any]

@dataclass
class Member(Node):
    object: Any
    property: Any
    computed: bool  # True for [], False for .

@dataclass
class FunctionExpr(Node):
    name: Optional[str]
    params: List[Any]
    body: Any

@dataclass
class ArrowFunction(Node):
    params: List[Any]
    body: Any  # Block or Expression
    expression: bool
