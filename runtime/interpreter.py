"""Tree-walking JavaScript interpreter."""
from typing import Any, List
from ..ast.nodes import *
from .environment import Environment
from .values import (
    UNDEFINED, is_undefined, JSFunction,
    js_to_string, js_to_number, js_to_boolean,
    js_add, js_sub, js_mul, js_div, js_mod, js_pow,
    js_lt, js_le, js_gt, js_ge,
    js_strict_equals, js_loose_equals,
    is_array, is_object, is_string, is_number, is_bool, is_null,
    js_typeof, NaN, Infinity, NegInfinity,
)
from ..errors import JSReferenceError, JSTypeError, JSSyntaxError
from ..builtins import (
    make_console, make_math, DateClass,
    get_array_property, get_string_property,
)


# --- internal control-flow signals (use exceptions for clean unwinding) ---
class _Return(Exception):
    def __init__(self, value): self.value = value
class _Break(Exception): pass
class _Continue(Exception): pass
class _JSThrow(Exception):
    def __init__(self, value): self.value = value


class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self._install_globals()

    def _install_globals(self):
        g = self.globals
        g.declare("console", make_console(), "const")
        g.declare("Math", make_math(), "const")
        g.declare("Date", DateClass, "const")
        g.declare("undefined", UNDEFINED, "const")
        g.declare("NaN", NaN, "const")
        g.declare("Infinity", Infinity, "const")
        g.declare("globalThis", {}, "const")

        # JSON minimal
        import json as _json
        def _json_stringify(value, replacer=UNDEFINED, indent=UNDEFINED):
            ind = None
            if not is_undefined(indent):
                ind = int(js_to_number(indent))
            return _json.dumps(self._to_jsonable(value), indent=ind, ensure_ascii=False)
        def _json_parse(s):
            return self._from_jsonable(_json.loads(js_to_string(s)))
        g.declare("JSON", {"stringify": _json_stringify, "parse": _json_parse}, "const")

        # Global functions
        def _parseInt(s, radix=UNDEFINED):
            st = js_to_string(s).strip()
            r = 10
            if not is_undefined(radix):
                r = int(js_to_number(radix))
            try:
                # accept leading sign, then digits
                sign = 1
                if st.startswith("-"): sign = -1; st = st[1:]
                elif st.startswith("+"): st = st[1:]
                if r == 16 and st.lower().startswith("0x"): st = st[2:]
                # pick longest valid prefix
                end = 0
                while end < len(st):
                    c = st[end].lower()
                    if c.isdigit() and int(c) < r: end += 1
                    elif r > 10 and 'a' <= c < chr(ord('a') + r - 10): end += 1
                    else: break
                if end == 0: return NaN
                return sign * int(st[:end], r)
            except Exception:
                return NaN
        def _parseFloat(s):
            st = js_to_string(s).strip()
            import re
            m = re.match(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", st)
            if not m: return NaN
            try: return float(m.group(0))
            except: return NaN
        def _isNaN(v):
            import math
            n = js_to_number(v)
            return isinstance(n, float) and math.isnan(n)
        def _isFinite(v):
            import math
            n = js_to_number(v)
            if isinstance(n, float) and (math.isnan(n) or math.isinf(n)): return False
            return True
        def _String(v=UNDEFINED): return js_to_string(v)
        def _Number(v=UNDEFINED): return js_to_number(v) if not is_undefined(v) else 0
        def _Boolean(v=UNDEFINED): return js_to_boolean(v)
        def _Array(*args):
            if len(args) == 1 and is_number(args[0]):
                return [UNDEFINED] * int(args[0])
            return list(args)
        def _Object(*args):
            return dict(args[0]) if args and is_object(args[0]) else {}
        g.declare("parseInt", _parseInt, "const")
        g.declare("parseFloat", _parseFloat, "const")
        g.declare("isNaN", _isNaN, "const")
        g.declare("isFinite", _isFinite, "const")
        g.declare("String", _String, "const")
        g.declare("Number", _Number, "const")
        g.declare("Boolean", _Boolean, "const")
        g.declare("Array", _Array, "const")
        g.declare("Object", _Object, "const")

        # Error constructors (used by `throw new Error(...)`)
        def _make_error(name):
            def ctor(msg=UNDEFINED):
                return {"__type__": "Error", "name": name,
                        "message": "" if is_undefined(msg) else js_to_string(msg)}
            return ctor
        g.declare("Error", _make_error("Error"), "const")
        g.declare("TypeError", _make_error("TypeError"), "const")
        g.declare("RangeError", _make_error("RangeError"), "const")
        g.declare("SyntaxError", _make_error("SyntaxError"), "const")
        g.declare("ReferenceError", _make_error("ReferenceError"), "const")

    def _to_jsonable(self, v):
        if is_undefined(v): return None
        if isinstance(v, dict):
            return {k: self._to_jsonable(x) for k, x in v.items() if not k.startswith("__") and not callable(x)}
        if isinstance(v, list):
            return [self._to_jsonable(x) for x in v]
        if isinstance(v, JSFunction) or callable(v): return None
        return v

    def _from_jsonable(self, v):
        if isinstance(v, dict): return {k: self._from_jsonable(x) for k, x in v.items()}
        if isinstance(v, list): return [self._from_jsonable(x) for x in v]
        return v

    # ---------- public entry ----------
    def run(self, program: Program):
        # hoist function declarations
        self._hoist(program.body, self.globals)
        last = UNDEFINED
        for stmt in program.body:
            if isinstance(stmt, FunctionDecl):
                continue
            last = self.execute(stmt, self.globals)
        return last

    def _hoist(self, body, env):
        for stmt in body:
            if isinstance(stmt, FunctionDecl):
                fn = JSFunction(stmt.name, stmt.params, stmt.body, env)
                env.declare(stmt.name, fn, "let")

    # ---------- execute statements ----------
    def execute(self, node, env: Environment):
        method = "_exec_" + type(node).__name__
        return getattr(self, method)(node, env)

    def _exec_Block(self, node, env):
        scope = Environment(env)
        self._hoist(node.body, scope)
        for stmt in node.body:
            if isinstance(stmt, FunctionDecl):
                continue
            self.execute(stmt, scope)
        return UNDEFINED

    def _exec_VarDecl(self, node, env):
        for name, init in node.declarations:
            value = self.evaluate(init, env) if init is not None else UNDEFINED
            env.declare(name, value, node.kind)
        return UNDEFINED

    def _exec_ExpressionStatement(self, node, env):
        self.evaluate(node.expression, env)
        return UNDEFINED

    def _exec_If(self, node, env):
        if js_to_boolean(self.evaluate(node.test, env)):
            self.execute(node.consequent, env)
        elif node.alternate is not None:
            self.execute(node.alternate, env)
        return UNDEFINED

    def _exec_While(self, node, env):
        while js_to_boolean(self.evaluate(node.test, env)):
            try:
                self.execute(node.body, env)
            except _Break: break
            except _Continue: continue
        return UNDEFINED

    def _exec_DoWhile(self, node, env):
        while True:
            try:
                self.execute(node.body, env)
            except _Break: break
            except _Continue: pass
            if not js_to_boolean(self.evaluate(node.test, env)):
                break
        return UNDEFINED

    def _exec_For(self, node, env):
        scope = Environment(env)
        if node.init is not None:
            if isinstance(node.init, VarDecl):
                self.execute(node.init, scope)
            else:
                self.execute(node.init, scope)
        while True:
            if node.test is not None and not js_to_boolean(self.evaluate(node.test, scope)):
                break
            try:
                self.execute(node.body, scope)
            except _Break: break
            except _Continue: pass
            if node.update is not None:
                self.evaluate(node.update, scope)
        return UNDEFINED

    def _exec_ForOf(self, node, env):
        iterable = self.evaluate(node.iterable, env)
        if isinstance(iterable, str):
            items = list(iterable)
        elif isinstance(iterable, list):
            items = list(iterable)
        elif isinstance(iterable, dict):
            items = list(iterable.values())
        else:
            raise JSTypeError("Object is not iterable")
        for v in items:
            scope = Environment(env)
            scope.declare(node.var_name, v, node.kind or "let")
            try:
                self.execute(node.body, scope)
            except _Break: break
            except _Continue: continue
        return UNDEFINED

    def _exec_ForIn(self, node, env):
        target = self.evaluate(node.iterable, env)
        if isinstance(target, list):
            keys = [str(i) for i in range(len(target))]
        elif isinstance(target, dict):
            keys = [k for k in target.keys() if not k.startswith("__") and not callable(target[k])]
        elif isinstance(target, str):
            keys = [str(i) for i in range(len(target))]
        else:
            return UNDEFINED
        for k in keys:
            scope = Environment(env)
            scope.declare(node.var_name, k, node.kind or "let")
            try:
                self.execute(node.body, scope)
            except _Break: break
            except _Continue: continue
        return UNDEFINED

    def _exec_Return(self, node, env):
        value = self.evaluate(node.argument, env) if node.argument is not None else UNDEFINED
        raise _Return(value)

    def _exec_Break(self, node, env): raise _Break()
    def _exec_Continue(self, node, env): raise _Continue()

    def _exec_Throw(self, node, env):
        raise _JSThrow(self.evaluate(node.argument, env))

    def _exec_TryCatch(self, node, env):
        try:
            self.execute(node.block, env)
        except _JSThrow as ex:
            if node.handler is not None:
                scope = Environment(env)
                if node.catch_param:
                    scope.declare(node.catch_param, ex.value, "let")
                self.execute(node.handler, scope)
        except (JSReferenceError, JSTypeError, JSSyntaxError) as ex:
            if node.handler is not None:
                scope = Environment(env)
                if node.catch_param:
                    err = {"__type__": "Error",
                           "name": type(ex).__name__.replace("JS", ""),
                           "message": getattr(ex, "message", str(ex))}
                    scope.declare(node.catch_param, err, "let")
                self.execute(node.handler, scope)
        finally:
            if node.finalizer is not None:
                self.execute(node.finalizer, env)
        return UNDEFINED

    def _exec_Switch(self, node, env):
        disc = self.evaluate(node.discriminant, env)
        matched = False
        scope = Environment(env)
        try:
            for i, (test, stmts) in enumerate(node.cases):
                if not matched:
                    if test is None:
                        continue  # handle default separately
                    if js_strict_equals(disc, self.evaluate(test, scope)):
                        matched = True
                if matched:
                    for s in stmts:
                        self.execute(s, scope)
            if not matched:
                # find default and run from there with fallthrough
                default_idx = None
                for i, (test, _) in enumerate(node.cases):
                    if test is None: default_idx = i; break
                if default_idx is not None:
                    for j in range(default_idx, len(node.cases)):
                        for s in node.cases[j][1]:
                            self.execute(s, scope)
        except _Break:
            pass
        return UNDEFINED

    def _exec_FunctionDecl(self, node, env):
        fn = JSFunction(node.name, node.params, node.body, env)
        env.declare(node.name, fn, "let")
        return UNDEFINED

    # ---------- evaluate expressions ----------
    def evaluate(self, node, env: Environment):
        method = "_eval_" + type(node).__name__
        return getattr(self, method)(node, env)

    def _eval_Literal(self, node, env): return node.value

    def _eval_Identifier(self, node, env):
        if node.name == "undefined":
            return UNDEFINED
        return env.get(node.name)

    def _eval_TemplateLiteral(self, node, env): return node.value

    def _eval_ArrayLit(self, node, env):
        out = []
        for el in node.elements:
            if isinstance(el, Spread):
                val = self.evaluate(el.argument, env)
                if isinstance(val, list): out.extend(val)
                elif isinstance(val, str): out.extend(list(val))
                else: raise JSTypeError("Spread target is not iterable")
            else:
                out.append(self.evaluate(el, env))
        return out

    def _eval_ObjectLit(self, node, env):
        obj = {}
        for prop in node.properties:
            key, value, computed, shorthand, spread = prop
            if spread:
                v = self.evaluate(value, env)
                if isinstance(v, dict):
                    for k, x in v.items():
                        if not k.startswith("__"): obj[k] = x
                continue
            if isinstance(key, Literal):
                k = js_to_string(key.value)
            elif computed:
                k = js_to_string(self.evaluate(key, env))
            else:
                k = js_to_string(key.value if hasattr(key, "value") else key)
            obj[k] = self.evaluate(value, env)
        return obj

    def _eval_Unary(self, node, env):
        if node.op == "typeof":
            # typeof on undeclared identifier should not throw
            if isinstance(node.argument, Identifier) and not env.has(node.argument.name):
                return "undefined"
            return js_typeof(self.evaluate(node.argument, env))
        v = self.evaluate(node.argument, env)
        if node.op == "-":
            n = js_to_number(v)
            return -n
        if node.op == "+":
            return js_to_number(v)
        if node.op == "!":
            return not js_to_boolean(v)
        if node.op == "~":
            return ~int(js_to_number(v))
        raise JSSyntaxError(f"Unknown unary op {node.op}")

    def _eval_Update(self, node, env):
        old = js_to_number(self._read_target(node.argument, env))
        new = old + 1 if node.op == "++" else old - 1
        self._assign_target(node.argument, new, env)
        return new if node.prefix else old

    def _read_target(self, target, env):
        return self.evaluate(target, env)

    def _assign_target(self, target, value, env):
        if isinstance(target, Identifier):
            env.set(target.name, value)
        elif isinstance(target, Member):
            obj = self.evaluate(target.object, env)
            key = self._member_key(target, env)
            if isinstance(obj, list):
                if isinstance(key, (int, float)) or (isinstance(key, str) and key.isdigit()):
                    idx = int(key)
                    while len(obj) <= idx: obj.append(UNDEFINED)
                    obj[idx] = value
                elif key == "length":
                    n = int(js_to_number(value))
                    if n < len(obj): del obj[n:]
                    else:
                        while len(obj) < n: obj.append(UNDEFINED)
                else:
                    # arrays can have named props; rare in practice
                    pass
            elif isinstance(obj, dict):
                obj[js_to_string(key)] = value
            else:
                raise JSTypeError("Cannot set property on non-object")
        else:
            raise JSSyntaxError("Invalid assignment target")

    def _member_key(self, node: Member, env):
        if node.computed:
            return self.evaluate(node.property, env)
        # not computed: property is Identifier name
        return node.property.name

    def _eval_Binary(self, node, env):
        op = node.op
        if op == "+":
            return js_add(self.evaluate(node.left, env), self.evaluate(node.right, env))
        if op == "-":
            return js_sub(self.evaluate(node.left, env), self.evaluate(node.right, env))
        if op == "*":
            return js_mul(self.evaluate(node.left, env), self.evaluate(node.right, env))
        if op == "/":
            return js_div(self.evaluate(node.left, env), self.evaluate(node.right, env))
        if op == "%":
            return js_mod(self.evaluate(node.left, env), self.evaluate(node.right, env))
        if op == "**":
            return js_pow(self.evaluate(node.left, env), self.evaluate(node.right, env))
        l = self.evaluate(node.left, env); r = self.evaluate(node.right, env)
        if op == "<": return js_lt(l, r)
        if op == "<=": return js_le(l, r)
        if op == ">": return js_gt(l, r)
        if op == ">=": return js_ge(l, r)
        if op == "==": return js_loose_equals(l, r)
        if op == "!=": return not js_loose_equals(l, r)
        if op == "===": return js_strict_equals(l, r)
        if op == "!==": return not js_strict_equals(l, r)
        if op == "&": return int(js_to_number(l)) & int(js_to_number(r))
        if op == "|": return int(js_to_number(l)) | int(js_to_number(r))
        if op == "^": return int(js_to_number(l)) ^ int(js_to_number(r))
        if op == "<<": return int(js_to_number(l)) << (int(js_to_number(r)) & 31)
        if op == ">>": return int(js_to_number(l)) >> (int(js_to_number(r)) & 31)
        if op == "in":
            key = js_to_string(l)
            if isinstance(r, dict): return key in r
            if isinstance(r, list):
                if key.isdigit(): return 0 <= int(key) < len(r)
                return False
            raise JSTypeError("Cannot use 'in' on non-object")
        raise JSSyntaxError(f"Unknown binary op {op}")

    def _eval_Logical(self, node, env):
        l = self.evaluate(node.left, env)
        if node.op == "&&":
            return self.evaluate(node.right, env) if js_to_boolean(l) else l
        if node.op == "||":
            return l if js_to_boolean(l) else self.evaluate(node.right, env)
        if node.op == "??":
            return l if not (is_null(l) or is_undefined(l)) else self.evaluate(node.right, env)
        raise JSSyntaxError(f"Unknown logical op {node.op}")

    def _eval_Assign(self, node, env):
        if node.op == "=":
            value = self.evaluate(node.value, env)
        else:
            cur = self._read_target(node.target, env)
            rhs = self.evaluate(node.value, env)
            mapping = {"+=": js_add, "-=": js_sub, "*=": js_mul, "/=": js_div, "%=": js_mod}
            value = mapping[node.op](cur, rhs)
        # declare-on-assign at global scope if undeclared (sloppy mode)
        if isinstance(node.target, Identifier) and not env.has(node.target.name):
            self.globals.declare(node.target.name, value, "let")
            return value
        self._assign_target(node.target, value, env)
        return value

    def _eval_Conditional(self, node, env):
        return self.evaluate(node.consequent, env) if js_to_boolean(self.evaluate(node.test, env)) \
            else self.evaluate(node.alternate, env)

    def _eval_Member(self, node, env):
        obj = self.evaluate(node.object, env)
        key = self._member_key(node, env)
        return self._get_member(obj, key)

    def _get_member(self, obj, key):
        if obj is None or is_undefined(obj):
            raise JSTypeError(f"Cannot read properties of {'null' if obj is None else 'undefined'} (reading '{key}')")
        if isinstance(obj, str):
            return get_string_property(obj, key, self)
        if isinstance(obj, list):
            return get_array_property(obj, key, self)
        if isinstance(obj, dict):
            k = js_to_string(key)
            if k in obj: return obj[k]
            return UNDEFINED
        # functions
        return UNDEFINED

    def _eval_Call(self, node, env):
        # method call vs free call: capture `this`
        this_val = UNDEFINED
        if isinstance(node.callee, Member):
            obj = self.evaluate(node.callee.object, env)
            key = self._member_key(node.callee, env)
            callee = self._get_member(obj, key)
            this_val = obj
        else:
            callee = self.evaluate(node.callee, env)
        args = []
        for a in node.arguments:
            if isinstance(a, Spread):
                v = self.evaluate(a.argument, env)
                if isinstance(v, list): args.extend(v)
                elif isinstance(v, str): args.extend(list(v))
                else: raise JSTypeError("Spread not iterable")
            else:
                args.append(self.evaluate(a, env))
        if callee is None or is_undefined(callee):
            name = node.callee.property.name if isinstance(node.callee, Member) else getattr(node.callee, "name", "?")
            raise JSTypeError(f"{name} is not a function")
        return self.call_function(callee, args, this_val)

    def _eval_New(self, node, env):
        callee = self.evaluate(node.callee, env)
        args = [self.evaluate(a, env) for a in node.arguments]
        if callable(callee) and not isinstance(callee, JSFunction):
            return callee(*args)
        if isinstance(callee, JSFunction):
            obj = {}
            self.call_function(callee, args, obj)
            return obj
        raise JSTypeError("Not a constructor")

    def _eval_FunctionExpr(self, node, env):
        return JSFunction(node.name, node.params, node.body, env)

    def _eval_ArrowFunction(self, node, env):
        return JSFunction(None, node.params, node.body, env, is_arrow=True)

    # ---------- function invocation ----------
    def call_function(self, fn, args, this_val=UNDEFINED):
        if isinstance(fn, JSFunction):
            scope = Environment(fn.closure)
            # bind params
            self._bind_params(fn.params, args, scope)
            if not fn.is_arrow:
                scope.declare("this", this_val, "let")
                scope.declare("arguments", list(args), "let")
            try:
                if isinstance(fn.body, Block):
                    self._hoist(fn.body.body, scope)
                    for stmt in fn.body.body:
                        if isinstance(stmt, FunctionDecl): continue
                        self.execute(stmt, scope)
                    return UNDEFINED
                else:
                    # expression-bodied arrow
                    return self.evaluate(fn.body, scope)
            except _Return as r:
                return r.value
        # native python callable
        if callable(fn):
            try:
                return fn(*args)
            except TypeError:
                # callable expects fewer args; pad
                return fn(*args[:fn.__code__.co_argcount]) if hasattr(fn, "__code__") else fn(*args)
        raise JSTypeError("Not a function")

    def _bind_params(self, params, args, scope):
        i = 0
        for p in params:
            if p["rest"]:
                scope.declare(p["name"], list(args[i:]), "let")
                return
            if i < len(args):
                val = args[i]
                if is_undefined(val) and p["default"] is not None:
                    val = self.evaluate(p["default"], scope)
            else:
                val = self.evaluate(p["default"], scope) if p["default"] is not None else UNDEFINED
            scope.declare(p["name"], val, "let")
            i += 1
