from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    TEMPLATE_STRING = auto()
    IDENT = auto()
    # Keywords
    LET = auto(); CONST = auto(); VAR = auto()
    FUNCTION = auto(); RETURN = auto()
    IF = auto(); ELSE = auto()
    SWITCH = auto(); CASE = auto(); DEFAULT = auto()
    FOR = auto(); WHILE = auto(); DO = auto()
    BREAK = auto(); CONTINUE = auto()
    TRUE = auto(); FALSE = auto(); NULL = auto(); UNDEFINED = auto()
    TRY = auto(); CATCH = auto(); FINALLY = auto(); THROW = auto()
    NEW = auto(); TYPEOF = auto(); INSTANCEOF = auto(); IN = auto(); OF = auto()
    THIS = auto();
    # Punctuation
    LPAREN = auto(); RPAREN = auto()
    LBRACE = auto(); RBRACE = auto()
    LBRACKET = auto(); RBRACKET = auto()
    COMMA = auto(); SEMI = auto(); COLON = auto(); DOT = auto()
    SPREAD = auto()        # ...
    ARROW = auto()         # =>
    QUESTION = auto()
    # Operators
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto()
    PERCENT = auto(); POWER = auto()
    ASSIGN = auto(); PLUS_ASSIGN = auto(); MINUS_ASSIGN = auto()
    STAR_ASSIGN = auto(); SLASH_ASSIGN = auto(); PERCENT_ASSIGN = auto()
    EQ = auto(); NEQ = auto(); SEQ = auto(); SNEQ = auto()
    LT = auto(); LE = auto(); GT = auto(); GE = auto()
    AND = auto(); OR = auto(); NOT = auto()
    BIT_AND = auto(); BIT_OR = auto(); BIT_XOR = auto(); BIT_NOT = auto()
    LSHIFT = auto(); RSHIFT = auto(); URSHIFT = auto()
    INC = auto(); DEC = auto()
    NULLISH = auto()       # ??
    OPT_CHAIN = auto()     # ?.
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"
