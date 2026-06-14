from typing import Optional
from .values import UNDEFINED
from ..errors import JSReferenceError, JSTypeError


class Environment:
    """Lexical scope with const-awareness."""
    __slots__ = ("vars", "consts", "parent")

    def __init__(self, parent: Optional["Environment"] = None):
        self.vars = {}
        self.consts = set()
        self.parent = parent

    def declare(self, name: str, value, kind: str = "let"):
        if name in self.vars and kind != "var":
            raise JSSyntaxError(f"Identifier '{name}' has already been declared", 0, 0) if False else None
        self.vars[name] = value
        if kind == "const":
            self.consts.add(name)

    def get(self, name: str):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise JSReferenceError(f"{name} is not defined")

    def has(self, name: str) -> bool:
        env = self
        while env is not None:
            if name in env.vars:
                return True
            env = env.parent
        return False

    def set(self, name: str, value):
        env = self
        while env is not None:
            if name in env.vars:
                if name in env.consts:
                    raise JSTypeError(f"Assignment to constant variable '{name}'")
                env.vars[name] = value
                return
            env = env.parent
        raise JSReferenceError(f"{name} is not defined")
