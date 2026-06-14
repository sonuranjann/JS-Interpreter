import math, random
from ..runtime.values import js_to_number, NaN


def make_math():
    def _floor(x): return math.floor(js_to_number(x))
    def _ceil(x): return math.ceil(js_to_number(x))
    def _round(x):
        n = js_to_number(x)
        # JS rounds .5 toward +Infinity
        return math.floor(n + 0.5)
    def _abs(x): return abs(js_to_number(x))
    def _max(*args):
        if not args: return float("-inf")
        nums = [js_to_number(a) for a in args]
        return NaN if any(isinstance(n, float) and math.isnan(n) for n in nums) else max(nums)
    def _min(*args):
        if not args: return float("inf")
        nums = [js_to_number(a) for a in args]
        return NaN if any(isinstance(n, float) and math.isnan(n) for n in nums) else min(nums)
    def _pow(a, b): return js_to_number(a) ** js_to_number(b)
    def _sqrt(x): return math.sqrt(js_to_number(x))
    def _random(): return random.random()
    def _trunc(x): return math.trunc(js_to_number(x))
    def _sign(x):
        n = js_to_number(x)
        if isinstance(n, float) and math.isnan(n): return NaN
        if n > 0: return 1
        if n < 0: return -1
        return 0
    def _log(x): return math.log(js_to_number(x))
    def _exp(x): return math.exp(js_to_number(x))
    def _sin(x): return math.sin(js_to_number(x))
    def _cos(x): return math.cos(js_to_number(x))
    def _tan(x): return math.tan(js_to_number(x))
    return {
        "floor": _floor, "ceil": _ceil, "round": _round, "abs": _abs,
        "max": _max, "min": _min, "pow": _pow, "sqrt": _sqrt,
        "random": _random, "trunc": _trunc, "sign": _sign,
        "log": _log, "exp": _exp, "sin": _sin, "cos": _cos, "tan": _tan,
        "PI": math.pi, "E": math.e,
    }
