from typing import List
from .tokens import Token, TokenType as T
from ..errors import JSSyntaxError

KEYWORDS = {
    "let": T.LET, "const": T.CONST, "var": T.VAR,
    "function": T.FUNCTION, "return": T.RETURN,
    "if": T.IF, "else": T.ELSE,
    "switch": T.SWITCH, "case": T.CASE, "default": T.DEFAULT,
    "for": T.FOR, "while": T.WHILE, "do": T.DO,
    "break": T.BREAK, "continue": T.CONTINUE,
    "true": T.TRUE, "false": T.FALSE, "null": T.NULL, "undefined": T.UNDEFINED,
    "try": T.TRY, "catch": T.CATCH, "finally": T.FINALLY, "throw": T.THROW,
    "new": T.NEW, "typeof": T.TYPEOF, "instanceof": T.INSTANCEOF,
    "in": T.IN, "of": T.OF, "this": T.THIS,
}

class Tokenizer:
    def __init__(self, source: str):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def error(self, msg):
        raise JSSyntaxError(msg, self.line, self.col)

    def peek(self, off=0):
        p = self.pos + off
        return self.src[p] if p < len(self.src) else ""

    def advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, s):
        if self.src.startswith(s, self.pos):
            for _ in s:
                self.advance()
            return True
        return False

    def add(self, type_, value, line, col):
        self.tokens.append(Token(type_, value, line, col))

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.src):
            ch = self.peek()
            # whitespace
            if ch in " \t\r\n":
                self.advance(); continue
            # comments
            if ch == "/" and self.peek(1) == "/":
                while self.pos < len(self.src) and self.peek() != "\n":
                    self.advance()
                continue
            if ch == "/" and self.peek(1) == "*":
                self.advance(); self.advance()
                while self.pos < len(self.src) and not (self.peek() == "*" and self.peek(1) == "/"):
                    self.advance()
                if self.pos < len(self.src):
                    self.advance(); self.advance()
                continue
            line, col = self.line, self.col
            # numbers
            if ch.isdigit() or (ch == "." and self.peek(1).isdigit()):
                self.read_number(line, col); continue
            # strings
            if ch in ("'", '"'):
                self.read_string(ch, line, col); continue
            if ch == "`":
                self.read_template(line, col); continue
            # identifiers / keywords
            if ch.isalpha() or ch == "_" or ch == "$":
                self.read_ident(line, col); continue
            # operators / punctuation
            self.read_punct(line, col)
        self.add(T.EOF, None, self.line, self.col)
        return self.tokens

    def read_number(self, line, col):
        start = self.pos
        # hex
        if self.peek() == "0" and self.peek(1) in ("x", "X"):
            self.advance(); self.advance()
            while self.peek() and (self.peek().isdigit() or self.peek().lower() in "abcdef"):
                self.advance()
            val = int(self.src[start:self.pos], 16)
            self.add(T.NUMBER, float(val), line, col); return
        while self.peek().isdigit():
            self.advance()
        if self.peek() == "." and self.peek(1).isdigit():
            self.advance()
            while self.peek().isdigit():
                self.advance()
        if self.peek() in ("e", "E"):
            self.advance()
            if self.peek() in ("+", "-"):
                self.advance()
            while self.peek().isdigit():
                self.advance()
        text = self.src[start:self.pos]
        if "." in text or "e" in text or "E" in text:
            self.add(T.NUMBER, float(text), line, col)
        else:
            n = int(text)
            self.add(T.NUMBER, float(n) if False else n, line, col)

    def read_string(self, quote, line, col):
        self.advance()
        buf = []
        while self.pos < len(self.src) and self.peek() != quote:
            ch = self.peek()
            if ch == "\\":
                self.advance()
                esc = self.advance()
                buf.append({"n":"\n","t":"\t","r":"\r","\\":"\\","'":"'",'"':'"',"`":"`","0":"\0","b":"\b","f":"\f","v":"\v"}.get(esc, esc))
            else:
                buf.append(self.advance())
        if self.pos >= len(self.src):
            self.error("Unterminated string")
        self.advance()  # closing quote
        self.add(T.STRING, "".join(buf), line, col)

    def read_template(self, line, col):
        # Minimal: treat as plain string; no ${} interpolation
        self.advance()
        buf = []
        while self.pos < len(self.src) and self.peek() != "`":
            ch = self.peek()
            if ch == "\\":
                self.advance()
                esc = self.advance()
                buf.append({"n":"\n","t":"\t","r":"\r","\\":"\\","`":"`"}.get(esc, esc))
            elif ch == "$" and self.peek(1) == "{":
                # naive: read until matching }
                self.advance(); self.advance()
                expr = []
                depth = 1
                while self.pos < len(self.src) and depth:
                    c = self.peek()
                    if c == "{": depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            self.advance(); break
                    expr.append(self.advance())
                # We can't evaluate here; embed as marker - simplification: skip interpolation
                buf.append("${" + "".join(expr) + "}")
            else:
                buf.append(self.advance())
        if self.pos >= len(self.src):
            self.error("Unterminated template")
        self.advance()
        self.add(T.STRING, "".join(buf), line, col)

    def read_ident(self, line, col):
        start = self.pos
        while self.peek() and (self.peek().isalnum() or self.peek() in "_$"):
            self.advance()
        name = self.src[start:self.pos]
        if name in KEYWORDS:
            tt = KEYWORDS[name]
            value = None
            if tt == T.TRUE: value = True
            elif tt == T.FALSE: value = False
            elif tt == T.NULL: value = None
            self.add(tt, value if value is not None or tt in (T.FALSE, T.NULL) else name, line, col)
        else:
            self.add(T.IDENT, name, line, col)

    def read_punct(self, line, col):
        # multi-char operators first
        three = self.src[self.pos:self.pos+3]
        two = self.src[self.pos:self.pos+2]
        if three == "===":
            self.pos += 3; self.col += 3; self.add(T.SEQ, "===", line, col); return
        if three == "!==":
            self.pos += 3; self.col += 3; self.add(T.SNEQ, "!==", line, col); return
        if three == "...":
            self.pos += 3; self.col += 3; self.add(T.SPREAD, "...", line, col); return
        if three == "**=":
            self.pos += 3; self.col += 3; self.add(T.STAR_ASSIGN, "**=", line, col); return
        if three == ">>>":
            self.pos += 3; self.col += 3; self.add(T.URSHIFT, ">>>", line, col); return
        two_map = {
            "==": T.EQ, "!=": T.NEQ, "<=": T.LE, ">=": T.GE,
            "&&": T.AND, "||": T.OR, "=>": T.ARROW,
            "+=": T.PLUS_ASSIGN, "-=": T.MINUS_ASSIGN,
            "*=": T.STAR_ASSIGN, "/=": T.SLASH_ASSIGN, "%=": T.PERCENT_ASSIGN,
            "++": T.INC, "--": T.DEC, "**": T.POWER,
            "<<": T.LSHIFT, ">>": T.RSHIFT,
            "??": T.NULLISH, "?.": T.OPT_CHAIN,
        }
        if two in two_map:
            self.pos += 2; self.col += 2; self.add(two_map[two], two, line, col); return
        one_map = {
            "(": T.LPAREN, ")": T.RPAREN,
            "{": T.LBRACE, "}": T.RBRACE,
            "[": T.LBRACKET, "]": T.RBRACKET,
            ",": T.COMMA, ";": T.SEMI, ":": T.COLON, ".": T.DOT,
            "+": T.PLUS, "-": T.MINUS, "*": T.STAR, "/": T.SLASH, "%": T.PERCENT,
            "=": T.ASSIGN, "<": T.LT, ">": T.GT, "!": T.NOT,
            "&": T.BIT_AND, "|": T.BIT_OR, "^": T.BIT_XOR, "~": T.BIT_NOT,
            "?": T.QUESTION,
        }
        ch = self.peek()
        if ch in one_map:
            self.advance(); self.add(one_map[ch], ch, line, col); return
        self.error(f"Unexpected character: {ch!r}")

    def skip_whitespace(self):
    # Add '\xa0' alongside standard spaces, tabs, and line breaks
        while self.position < len(self.source) and self.source[self.position] in (' ', '\t', '\n', '\r', '\xa0'):
            if self.source[self.position] == '\n':
                self.line += 1  # Track line numbers if your lexer does this
            self.position += 1
