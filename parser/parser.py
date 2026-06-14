from typing import List, Optional
from ..lexer.tokens import Token, TokenType as T
from ..ast.nodes import *
from ..errors import JSSyntaxError
from .precedence import BINARY_PRECEDENCE, LOGICAL_OPS, RIGHT_ASSOC

ASSIGN_OPS = {T.ASSIGN, T.PLUS_ASSIGN, T.MINUS_ASSIGN,
              T.STAR_ASSIGN, T.SLASH_ASSIGN, T.PERCENT_ASSIGN}


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    # ---------- helpers ----------
    def peek(self, off=0) -> Token:
        return self.tokens[self.pos + off]

    def at_end(self) -> bool:
        return self.peek().type == T.EOF

    def check(self, *types) -> bool:
        return self.peek().type in types

    def match(self, *types) -> bool:
        if self.check(*types):
            self.pos += 1
            return True
        return False

    def consume(self, type_, msg="") -> Token:
        if self.check(type_):
            tok = self.peek()
            self.pos += 1
            return tok
        tok = self.peek()
        raise JSSyntaxError(msg or f"Expected {type_.name}, got {tok.type.name} ({tok.value!r})",
                            tok.line, tok.column)

    def error(self, msg):
        tok = self.peek()
        raise JSSyntaxError(msg, tok.line, tok.column)

    # ---------- entry ----------
    def parse(self) -> Program:
        body = []
        while not self.at_end():
            body.append(self.parse_statement())
        return Program(body)

    # ---------- statements ----------
    def parse_statement(self):
        t = self.peek().type
        if t in (T.LET, T.CONST, T.VAR):
            return self.parse_var_decl()
        if t == T.LBRACE:
            return self.parse_block()
        if t == T.IF:
            return self.parse_if()
        if t == T.WHILE:
            return self.parse_while()
        if t == T.DO:
            return self.parse_do_while()
        if t == T.FOR:
            return self.parse_for()
        if t == T.RETURN:
            return self.parse_return()
        if t == T.BREAK:
            self.pos += 1; self.match(T.SEMI); return Break()
        if t == T.CONTINUE:
            self.pos += 1; self.match(T.SEMI); return Continue()
        if t == T.FUNCTION:
            return self.parse_function_decl()
        if t == T.TRY:
            return self.parse_try()
        if t == T.THROW:
            self.pos += 1
            arg = self.parse_expression()
            self.match(T.SEMI)
            return Throw(arg)
        if t == T.SWITCH:
            return self.parse_switch()
        if t == T.SEMI:
            self.pos += 1
            return Block([])
        # expression statement
        expr = self.parse_expression()
        self.match(T.SEMI)
        return ExpressionStatement(expr)

    def parse_var_decl(self):
        kind = self.peek().value if self.peek().value else self.peek().type.name.lower()
        kind = {"LET": "let", "CONST": "const", "VAR": "var"}.get(kind.upper(), kind.lower())
        self.pos += 1
        decls = []
        while True:
            name_tok = self.consume(T.IDENT, "Expected identifier")
            init = None
            if self.match(T.ASSIGN):
                init = self.parse_assignment()
            decls.append((name_tok.value, init))
            if not self.match(T.COMMA):
                break
        self.match(T.SEMI)
        return VarDecl(kind, decls)

    def parse_block(self):
        self.consume(T.LBRACE)
        body = []
        while not self.check(T.RBRACE) and not self.at_end():
            body.append(self.parse_statement())
        self.consume(T.RBRACE)
        return Block(body)

    def parse_if(self):
        self.consume(T.IF)
        self.consume(T.LPAREN)
        test = self.parse_expression()
        self.consume(T.RPAREN)
        cons = self.parse_statement()
        alt = None
        if self.match(T.ELSE):
            alt = self.parse_statement()
        return If(test, cons, alt)

    def parse_while(self):
        self.consume(T.WHILE)
        self.consume(T.LPAREN)
        test = self.parse_expression()
        self.consume(T.RPAREN)
        body = self.parse_statement()
        return While(test, body)

    def parse_do_while(self):
        self.consume(T.DO)
        body = self.parse_statement()
        self.consume(T.WHILE)
        self.consume(T.LPAREN)
        test = self.parse_expression()
        self.consume(T.RPAREN)
        self.match(T.SEMI)
        return DoWhile(body, test)

    def parse_for(self):
        self.consume(T.FOR)
        self.consume(T.LPAREN)
        # for-in / for-of detection
        init = None
        # Snapshot position to allow potential rewind for for-in/of
        save = self.pos
        kind = None
        if self.check(T.LET, T.CONST, T.VAR):
            kind_tok = self.peek()
            kind = {"LET":"let","CONST":"const","VAR":"var"}[kind_tok.type.name]
            self.pos += 1
            if self.check(T.IDENT):
                name = self.peek().value
                self.pos += 1
                if self.match(T.OF):
                    iterable = self.parse_expression()
                    self.consume(T.RPAREN)
                    body = self.parse_statement()
                    return ForOf(kind, name, iterable, body)
                if self.match(T.IN):
                    iterable = self.parse_expression()
                    self.consume(T.RPAREN)
                    body = self.parse_statement()
                    return ForIn(kind, name, iterable, body)
                # not for-in/of; rewind
                self.pos = save
            else:
                self.pos = save
        # classic for(;;)
        if not self.check(T.SEMI):
            if self.check(T.LET, T.CONST, T.VAR):
                init = self.parse_var_decl()  # consumes optional ;
            else:
                init = ExpressionStatement(self.parse_expression())
                self.consume(T.SEMI)
        else:
            self.consume(T.SEMI)
        test = None
        if not self.check(T.SEMI):
            test = self.parse_expression()
        self.consume(T.SEMI)
        update = None
        if not self.check(T.RPAREN):
            update = self.parse_expression()
        self.consume(T.RPAREN)
        body = self.parse_statement()
        return For(init, test, update, body)

    def parse_return(self):
        self.consume(T.RETURN)
        arg = None
        if not self.check(T.SEMI, T.RBRACE) and not self.at_end():
            arg = self.parse_expression()
        self.match(T.SEMI)
        return Return(arg)

    def parse_function_decl(self):
        self.consume(T.FUNCTION)
        name_tok = self.consume(T.IDENT, "Expected function name")
        params = self.parse_params()
        body = self.parse_block()
        return FunctionDecl(name_tok.value, params, body)

    def parse_params(self):
        self.consume(T.LPAREN)
        params = []
        if not self.check(T.RPAREN):
            while True:
                rest = self.match(T.SPREAD)
                name_tok = self.consume(T.IDENT, "Expected parameter name")
                default = None
                if self.match(T.ASSIGN):
                    default = self.parse_assignment()
                params.append({"name": name_tok.value, "rest": rest, "default": default})
                if not self.match(T.COMMA):
                    break
        self.consume(T.RPAREN)
        return params

    def parse_try(self):
        self.consume(T.TRY)
        block = self.parse_block()
        catch_param = None
        handler = None
        if self.match(T.CATCH):
            if self.match(T.LPAREN):
                if self.check(T.IDENT):
                    catch_param = self.peek().value
                    self.pos += 1
                self.consume(T.RPAREN)
            handler = self.parse_block()
        finalizer = None
        if self.match(T.FINALLY):
            finalizer = self.parse_block()
        return TryCatch(block, catch_param, handler, finalizer)

    def parse_switch(self):
        self.consume(T.SWITCH)
        self.consume(T.LPAREN)
        disc = self.parse_expression()
        self.consume(T.RPAREN)
        self.consume(T.LBRACE)
        cases = []
        while not self.check(T.RBRACE) and not self.at_end():
            if self.match(T.CASE):
                test = self.parse_expression()
                self.consume(T.COLON)
                stmts = []
                while not self.check(T.CASE, T.DEFAULT, T.RBRACE) and not self.at_end():
                    stmts.append(self.parse_statement())
                cases.append((test, stmts))
            elif self.match(T.DEFAULT):
                self.consume(T.COLON)
                stmts = []
                while not self.check(T.CASE, T.DEFAULT, T.RBRACE) and not self.at_end():
                    stmts.append(self.parse_statement())
                cases.append((None, stmts))
            else:
                self.error("Expected case or default in switch")
        self.consume(T.RBRACE)
        return Switch(disc, cases)

    # ---------- expressions ----------
    def parse_expression(self):
        # comma operator not deeply supported; just one assignment for safety
        expr = self.parse_assignment()
        return expr

    def parse_assignment(self):
        left = self.parse_conditional()
        if self.peek().type in ASSIGN_OPS:
            op = self.peek().value
            self.pos += 1
            right = self.parse_assignment()
            return Assign(op, left, right)
        return left

    def parse_conditional(self):
        test = self.parse_binary(0)
        if self.match(T.QUESTION):
            cons = self.parse_assignment()
            self.consume(T.COLON)
            alt = self.parse_assignment()
            return Conditional(test, cons, alt)
        return test

    def parse_binary(self, min_prec: int):
        left = self.parse_unary()
        while True:
            tok = self.peek()
            prec = BINARY_PRECEDENCE.get(tok.type)
            if prec is None or prec < min_prec:
                break
            op_type = tok.type
            op_val = tok.value
            self.pos += 1
            next_min = prec + (0 if op_type in RIGHT_ASSOC else 1)
            right = self.parse_binary(next_min)
            if op_type in LOGICAL_OPS:
                left = Logical(op_val, left, right)
            else:
                left = Binary(op_val, left, right)
        return left

    def parse_unary(self):
        tok = self.peek()
        if tok.type in (T.NOT, T.MINUS, T.PLUS, T.BIT_NOT, T.TYPEOF):
            self.pos += 1
            arg = self.parse_unary()
            return Unary(tok.value if tok.type != T.TYPEOF else "typeof", arg)
        if tok.type in (T.INC, T.DEC):
            self.pos += 1
            arg = self.parse_unary()
            return Update(tok.value, arg, prefix=True)
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_call_member(self.parse_primary())
        if self.peek().type in (T.INC, T.DEC):
            op = self.peek().value
            self.pos += 1
            return Update(op, expr, prefix=False)
        return expr

    def parse_call_member(self, expr):
        while True:
            if self.match(T.DOT):
                name_tok = self.consume(T.IDENT, "Expected property name")
                expr = Member(expr, Identifier(name_tok.value), computed=False)
            elif self.match(T.LBRACKET):
                prop = self.parse_expression()
                self.consume(T.RBRACKET)
                expr = Member(expr, prop, computed=True)
            elif self.check(T.LPAREN):
                args = self.parse_arguments()
                expr = Call(expr, args)
            else:
                break
        return expr

    def parse_arguments(self):
        self.consume(T.LPAREN)
        args = []
        if not self.check(T.RPAREN):
            while True:
                if self.match(T.SPREAD):
                    args.append(Spread(self.parse_assignment()))
                else:
                    args.append(self.parse_assignment())
                if not self.match(T.COMMA):
                    break
        self.consume(T.RPAREN)
        return args

    def parse_primary(self):
        tok = self.peek()
        t = tok.type
        # arrow function detection: (params) =>  OR  ident =>
        if t == T.IDENT and self.peek(1).type == T.ARROW:
            name = tok.value; self.pos += 2
            body = self.parse_arrow_body()
            return ArrowFunction([{"name": name, "rest": False, "default": None}], body,
                                 expression=not isinstance(body, Block))
        if t == T.LPAREN:
            # try arrow function with paren params
            arrow = self.try_parse_arrow()
            if arrow is not None:
                return arrow
            self.pos += 1
            expr = self.parse_expression()
            self.consume(T.RPAREN)
            return expr
        if t == T.NUMBER:
            self.pos += 1; return Literal(tok.value)
        if t == T.STRING:
            self.pos += 1; return Literal(tok.value)
        if t == T.TRUE:
            self.pos += 1; return Literal(True)
        if t == T.FALSE:
            self.pos += 1; return Literal(False)
        if t == T.NULL:
            self.pos += 1; return Literal(None)
        if t == T.UNDEFINED:
            self.pos += 1; return Identifier("undefined")
        if t == T.IDENT:
            self.pos += 1; return Identifier(tok.value)
        if t == T.THIS:
            self.pos += 1; return Identifier("this")
        if t == T.LBRACKET:
            return self.parse_array_lit()
        if t == T.LBRACE:
            return self.parse_object_lit()
        if t == T.FUNCTION:
            self.pos += 1
            name = None
            if self.check(T.IDENT):
                name = self.peek().value; self.pos += 1
            params = self.parse_params()
            body = self.parse_block()
            return FunctionExpr(name, params, body)
        if t == T.NEW:
            self.pos += 1
            callee = self._parse_member_only(self.parse_primary_no_call())
            args = []
            if self.check(T.LPAREN):
                args = self.parse_arguments()
            node = New(callee, args)
            # allow further member/call after the new-expression
            return self.parse_call_member(node)
        self.error(f"Unexpected token {tok.type.name} ({tok.value!r})")

    def _parse_member_only(self, expr):
        while True:
            if self.match(T.DOT):
                name_tok = self.consume(T.IDENT, "Expected property name")
                expr = Member(expr, Identifier(name_tok.value), computed=False)
            elif self.match(T.LBRACKET):
                prop = self.parse_expression()
                self.consume(T.RBRACKET)
                expr = Member(expr, prop, computed=True)
            else:
                break
        return expr

    def parse_primary_no_call(self):
        # for new X (no immediate call attached to base); kept simple
        tok = self.peek()
        if tok.type == T.IDENT:
            self.pos += 1; return Identifier(tok.value)
        return self.parse_primary()

    def try_parse_arrow(self):
        # Look for: ( ... ) =>
        save = self.pos
        if not self.check(T.LPAREN):
            return None
        # Scan forward for matching paren and check if followed by =>
        depth = 0
        i = self.pos
        while i < len(self.tokens):
            tt = self.tokens[i].type
            if tt == T.LPAREN: depth += 1
            elif tt == T.RPAREN:
                depth -= 1
                if depth == 0:
                    if i + 1 < len(self.tokens) and self.tokens[i+1].type == T.ARROW:
                        break
                    return None
            elif tt == T.EOF:
                return None
            i += 1
        # parse params
        params = self.parse_params()
        self.consume(T.ARROW)
        body = self.parse_arrow_body()
        return ArrowFunction(params, body, expression=not isinstance(body, Block))

    def parse_arrow_body(self):
        if self.check(T.LBRACE):
            return self.parse_block()
        return self.parse_assignment()

    def parse_array_lit(self):
        self.consume(T.LBRACKET)
        elements = []
        while not self.check(T.RBRACKET):
            if self.match(T.COMMA):
                elements.append(Literal(None))  # elision -> null
                continue
            if self.match(T.SPREAD):
                elements.append(Spread(self.parse_assignment()))
            else:
                elements.append(self.parse_assignment())
            if not self.match(T.COMMA):
                break
        self.consume(T.RBRACKET)
        return ArrayLit(elements)

    def parse_object_lit(self):
        self.consume(T.LBRACE)
        props = []
        while not self.check(T.RBRACE):
            if self.match(T.SPREAD):
                props.append((None, self.parse_assignment(), False, False, True))
                if not self.match(T.COMMA): break
                continue
            computed = False
            key = None
            tok = self.peek()
            if tok.type == T.LBRACKET:
                self.pos += 1
                key = self.parse_assignment()
                self.consume(T.RBRACKET)
                computed = True
            elif tok.type == T.STRING:
                self.pos += 1
                key = Literal(tok.value)
            elif tok.type == T.NUMBER:
                self.pos += 1
                key = Literal(tok.value)
            elif tok.type == T.IDENT or tok.type.name in ("LET","CONST","VAR","IF","ELSE","FOR","WHILE","RETURN","FUNCTION","TRUE","FALSE","NULL","UNDEFINED"):
                self.pos += 1
                key = Literal(tok.value if tok.value is not None else tok.type.name.lower())
            else:
                self.error("Expected property name")
            shorthand = False
            if self.match(T.COLON):
                value = self.parse_assignment()
            elif self.check(T.LPAREN):
                # method shorthand
                params = self.parse_params()
                body = self.parse_block()
                value = FunctionExpr(None, params, body)
            else:
                # shorthand: { x } -> x: x
                shorthand = True
                if not isinstance(key, Literal):
                    self.error("Invalid shorthand")
                value = Identifier(key.value)
            props.append((key, value, computed, shorthand, False))
            if not self.match(T.COMMA):
                break
        self.consume(T.RBRACE)
        return ObjectLit(props)
