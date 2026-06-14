from ..runtime.values import (
    js_to_string, js_to_number, js_to_boolean, js_strict_equals,
    UNDEFINED, is_undefined, JSFunction,
)


def _call(interpreter, fn, args, this=None):
    return interpreter.call_function(fn, list(args), this)


def get_array_property(arr, prop, interpreter):
    if prop == "length":
        return len(arr)
    if isinstance(prop, (int, float)):
        idx = int(prop)
        if 0 <= idx < len(arr):
            return arr[idx]
        return UNDEFINED
    if isinstance(prop, str) and prop.isdigit():
        idx = int(prop)
        if 0 <= idx < len(arr):
            return arr[idx]
        return UNDEFINED
    fn = ARRAY_METHODS.get(prop)
    if fn is None:
        return UNDEFINED
    # bind arr + interpreter
    return lambda *args, _fn=fn, _arr=arr, _i=interpreter: _fn(_i, _arr, list(args))


# Each method: (interpreter, arr, args)
def _push(i, arr, args):
    arr.extend(args); return len(arr)

def _pop(i, arr, args):
    return arr.pop() if arr else UNDEFINED

def _shift(i, arr, args):
    return arr.pop(0) if arr else UNDEFINED

def _unshift(i, arr, args):
    for x in reversed(args): arr.insert(0, x)
    return len(arr)

def _slice(i, arr, args):
    start = int(js_to_number(args[0])) if len(args) >= 1 and not is_undefined(args[0]) else 0
    end = int(js_to_number(args[1])) if len(args) >= 2 and not is_undefined(args[1]) else len(arr)
    return arr[start:end]

def _splice(i, arr, args):
    start = int(js_to_number(args[0])) if args else 0
    if start < 0: start = max(0, len(arr) + start)
    start = min(start, len(arr))
    delete_count = (int(js_to_number(args[1])) if len(args) > 1 else len(arr) - start)
    delete_count = max(0, min(delete_count, len(arr) - start))
    items = list(args[2:])
    removed = arr[start:start+delete_count]
    arr[start:start+delete_count] = items
    return removed

def _concat(i, arr, args):
    result = list(arr)
    for a in args:
        if isinstance(a, list): result.extend(a)
        else: result.append(a)
    return result

def _includes(i, arr, args):
    target = args[0] if args else UNDEFINED
    return any(js_strict_equals(x, target) for x in arr)

def _index_of(i, arr, args):
    target = args[0] if args else UNDEFINED
    for idx, x in enumerate(arr):
        if js_strict_equals(x, target):
            return idx
    return -1

def _sort(i, arr, args):
    if args and args[0]:
        comp = args[0]
        from functools import cmp_to_key
        def cmp(a, b):
            r = _call(i, comp, [a, b])
            n = js_to_number(r)
            if n < 0: return -1
            if n > 0: return 1
            return 0
        arr.sort(key=cmp_to_key(cmp))
    else:
        arr.sort(key=lambda x: js_to_string(x))
    return arr

def _reverse(i, arr, args):
    arr.reverse(); return arr

def _join(i, arr, args):
    sep = js_to_string(args[0]) if args and not is_undefined(args[0]) else ","
    return sep.join("" if (x is None or is_undefined(x)) else js_to_string(x) for x in arr)

def _map(i, arr, args):
    fn = args[0]
    return [_call(i, fn, [v, idx, arr]) for idx, v in enumerate(arr)]

def _filter(i, arr, args):
    fn = args[0]
    return [v for idx, v in enumerate(arr) if js_to_boolean(_call(i, fn, [v, idx, arr]))]

def _reduce(i, arr, args):
    fn = args[0]
    if len(args) >= 2:
        acc = args[1]
        start = 0
    else:
        if not arr: raise Exception("Reduce of empty array with no initial value")
        acc = arr[0]; start = 1
    for idx in range(start, len(arr)):
        acc = _call(i, fn, [acc, arr[idx], idx, arr])
    return acc

def _find(i, arr, args):
    fn = args[0]
    for idx, v in enumerate(arr):
        if js_to_boolean(_call(i, fn, [v, idx, arr])):
            return v
    return UNDEFINED

def _findIndex(i, arr, args):
    fn = args[0]
    for idx, v in enumerate(arr):
        if js_to_boolean(_call(i, fn, [v, idx, arr])):
            return idx
    return -1

def _some(i, arr, args):
    fn = args[0]
    return any(js_to_boolean(_call(i, fn, [v, idx, arr])) for idx, v in enumerate(arr))

def _every(i, arr, args):
    fn = args[0]
    return all(js_to_boolean(_call(i, fn, [v, idx, arr])) for idx, v in enumerate(arr))

def _forEach(i, arr, args):
    fn = args[0]
    for idx, v in enumerate(arr):
        _call(i, fn, [v, idx, arr])
    return UNDEFINED

def _flat(i, arr, args):
    depth = int(js_to_number(args[0])) if args else 1
    def flatten(a, d):
        out = []
        for x in a:
            if isinstance(x, list) and d > 0:
                out.extend(flatten(x, d-1))
            else:
                out.append(x)
        return out
    return flatten(arr, depth)


ARRAY_METHODS = {
    "push": _push, "pop": _pop, "shift": _shift, "unshift": _unshift,
    "slice": _slice, "splice": _splice, "concat": _concat,
    "includes": _includes, "indexOf": _index_of,
    "sort": _sort, "reverse": _reverse, "join": _join,
    "map": _map, "filter": _filter, "reduce": _reduce,
    "find": _find, "findIndex": _findIndex,
    "some": _some, "every": _every, "forEach": _forEach,
    "flat": _flat,
}
