"""JavaScript value system & coercion built atop Python primitives.

Mapping:
- JS Number  -> Python int or float (we keep int when safe; coerce on demand)
- JS String  -> Python str
- JS Boolean -> Python bool
- JS Null    -> Python None
- JS Undefined -> singleton UNDEFINED
- JS Object  -> dict (insertion-ordered)
- JS Array   -> list (subclass JSArray to support .length etc., but plain list works)
- JS Function -> JSFunction or Python callable (built-ins)
"""
import math
from dataclasses import dataclass
from typing import Any, Callable, List, Optional


class _Undefined:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self): return "undefined"
    def __bool__(self): return False
    def __eq__(self, other): return isinstance(other, _Undefined)
    def __hash__(self): return hash("__undefined__")

Undefined = _Undefined
UNDEFINED = _Undefined()


class JSFunction:
    """User-defined JS function with closure."""
    def __init__(self, name: Optional[str], params: List[dict], body, closure, is_arrow=False):
        self.name = name or ""
        self.params = params
        self.body = body
        self.closure = closure
        self.is_arrow = is_arrow

    def __repr__(self):
        return f"[Function: {self.name or 'anonymous'}]"


# ---------- type predicates ----------
def is_number(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
def is_string(v): return isinstance(v, str)
def is_bool(v): return isinstance(v, bool)
def is_null(v): return v is None
def is_undefined(v): return isinstance(v, _Undefined)
def is_array(v): return isinstance(v, list)
def is_object(v): return isinstance(v, dict)
def is_function(v): return isinstance(v, JSFunction) or callable(v) and not isinstance(v, type)

def js_typeof(v):
    if is_undefined(v): return "undefined"
    if is_null(v): return "object"  # JS quirk
    if is_bool(v): return "boolean"
    if is_number(v): return "number"
    if is_string(v): return "string"
    if is_function(v): return "function"
    return "object"


# ---------- coercion ----------
NaN = float("nan")
Infinity = float("inf")
NegInfinity = float("-inf")

def is_nan(v): return isinstance(v, float) and math.isnan(v)


def js_to_number(v) -> float:
    if is_undefined(v): return NaN
    if is_null(v): return 0
    if is_bool(v): return 1 if v else 0
    if is_number(v): return v
    if is_string(v):
        s = v.strip()
        if s == "": return 0
        try:
            if s.startswith(("0x","0X")):
                return float(int(s, 16))
            if "." in s or "e" in s or "E" in s:
                return float(s)
            return float(int(s))
        except ValueError:
            return NaN
    if is_array(v):
        if len(v) == 0: return 0
        if len(v) == 1: return js_to_number(v[0])
        return NaN
    return NaN


def _num_to_str(n) -> str:
    if isinstance(n, bool):  # safety (shouldn't normally hit here)
        return "true" if n else "false"
    if isinstance(n, float):
        if math.isnan(n): return "NaN"
        if n == Infinity: return "Infinity"
        if n == NegInfinity: return "-Infinity"
        if n.is_integer() and abs(n) < 1e21:
            return str(int(n))
        # JS-ish float repr
        return repr(n) if abs(n) >= 1e21 or (n != 0 and abs(n) < 1e-6) else format(n, "g")
    return str(n)


def js_to_string(v) -> str:
    if is_undefined(v): return "undefined"
    if is_null(v): return "null"
    if is_bool(v): return "true" if v else "false"
    if is_number(v): return _num_to_str(v)
    if is_string(v): return v
    if is_array(v):
        return ",".join("" if (is_null(x) or is_undefined(x)) else js_to_string(x) for x in v)
    if isinstance(v, JSFunction):
        return f"function {v.name}() {{ [native code] }}"
    if callable(v):
        return "function () { [native code] }"
    if is_object(v):
        return "[object Object]"
    return str(v)


def js_to_boolean(v) -> bool:
    if is_undefined(v) or is_null(v): return False
    if is_bool(v): return v
    if is_number(v):
        return not (v == 0 or is_nan(v))
    if is_string(v): return len(v) > 0
    return True  # objects, arrays, functions all truthy


# ---------- equality ----------
def js_strict_equals(a, b) -> bool:
    if is_undefined(a) and is_undefined(b): return True
    if is_null(a) and is_null(b): return True
    if is_number(a) and is_number(b):
        if is_nan(a) or is_nan(b): return False
        return a == b
    if is_string(a) and is_string(b): return a == b
    if is_bool(a) and is_bool(b): return a == b
    if type(a) != type(b):
        # number vs number where one is int and other float still matches above
        return False
    return a is b  # object identity


def js_loose_equals(a, b) -> bool:
    if is_strict_same_kind(a, b):
        return js_strict_equals(a, b)
    if (is_null(a) and is_undefined(b)) or (is_undefined(a) and is_null(b)):
        return True
    if is_number(a) and is_string(b):
        return js_strict_equals(a, js_to_number(b))
    if is_string(a) and is_number(b):
        return js_strict_equals(js_to_number(a), b)
    if is_bool(a):
        return js_loose_equals(js_to_number(a), b)
    if is_bool(b):
        return js_loose_equals(a, js_to_number(b))
    # object to primitive
    if (is_object(a) or is_array(a)) and (is_number(b) or is_string(b)):
        return js_loose_equals(js_to_string(a) if is_string(b) else js_to_number(a), b)
    if (is_object(b) or is_array(b)) and (is_number(a) or is_string(a)):
        return js_loose_equals(a, js_to_string(b) if is_string(a) else js_to_number(b))
    return False


def is_strict_same_kind(a, b) -> bool:
    if is_undefined(a) and is_undefined(b): return True
    if is_null(a) and is_null(b): return True
    if is_number(a) and is_number(b): return True
    if is_string(a) and is_string(b): return True
    if is_bool(a) and is_bool(b): return True
    if (is_array(a) and is_array(b)) or (is_object(a) and is_object(b)): return True
    if is_function(a) and is_function(b): return True
    return False


# ---------- arithmetic ----------
def js_add(a, b):
    # If either is string → concatenate
    if is_string(a) or is_string(b):
        return js_to_string(a) + js_to_string(b)
    # arrays/objects → coerce via to_string per JS spec (simplification)
    if is_array(a) or is_array(b) or is_object(a) or is_object(b):
        if is_array(a) or is_object(a): a = js_to_string(a)
        if is_array(b) or is_object(b): b = js_to_string(b)
        if is_string(a) or is_string(b):
            return js_to_string(a) + js_to_string(b)
    na, nb = js_to_number(a), js_to_number(b)
    return _num_op(na, nb, lambda x, y: x + y)


def _num_op(a, b, fn):
    r = fn(a, b)
    if isinstance(r, float) and r.is_integer() and not math.isnan(r) and not math.isinf(r):
        # Keep as float if either operand is float to mirror JS number semantics enough
        return r
    return r


def js_sub(a, b): return js_to_number(a) - js_to_number(b)
def js_mul(a, b): return js_to_number(a) * js_to_number(b)


def js_div(a, b):
    na, nb = js_to_number(a), js_to_number(b)
    if nb == 0:
        if na == 0 or is_nan(na): return NaN
        return Infinity if na > 0 else NegInfinity
    return na / nb


def js_mod(a, b):
    na, nb = js_to_number(a), js_to_number(b)
    if nb == 0: return NaN
    # JS modulo follows dividend sign
    return math.fmod(na, nb)


def js_pow(a, b):
    return js_to_number(a) ** js_to_number(b)


def js_lt(a, b):
    if is_string(a) and is_string(b):
        return a < b
    na, nb = js_to_number(a), js_to_number(b)
    if is_nan(na) or is_nan(nb): return False
    return na < nb


def js_le(a, b):
    if is_string(a) and is_string(b):
        return a <= b
    na, nb = js_to_number(a), js_to_number(b)
    if is_nan(na) or is_nan(nb): return False
    return na <= nb


def js_gt(a, b): return js_lt(b, a)
def js_ge(a, b): return js_le(b, a)
