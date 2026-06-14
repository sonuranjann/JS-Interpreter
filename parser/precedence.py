# JavaScript operator precedence (higher = tighter)
from ..lexer.tokens import TokenType as T

BINARY_PRECEDENCE = {
    T.OR: 1,
    T.NULLISH: 1,
    T.AND: 2,
    T.BIT_OR: 3,
    T.BIT_XOR: 4,
    T.BIT_AND: 5,
    T.EQ: 6, T.NEQ: 6, T.SEQ: 6, T.SNEQ: 6,
    T.LT: 7, T.LE: 7, T.GT: 7, T.GE: 7, T.INSTANCEOF: 7, T.IN: 7,
    T.LSHIFT: 8, T.RSHIFT: 8, T.URSHIFT: 8,
    T.PLUS: 9, T.MINUS: 9,
    T.STAR: 10, T.SLASH: 10, T.PERCENT: 10,
    T.POWER: 11,  # right-assoc
}

LOGICAL_OPS = {T.OR, T.AND, T.NULLISH}
RIGHT_ASSOC = {T.POWER}
