from ..runtime.values import (
    js_to_string, js_to_number, UNDEFINED, is_undefined,
)


def get_string_property(s, prop, interpreter):
    if prop == "length":
        return len(s)
    if isinstance(prop, (int, float)):
        idx = int(prop)
        return s[idx] if 0 <= idx < len(s) else UNDEFINED
    if isinstance(prop, str) and prop.isdigit():
        idx = int(prop)
        return s[idx] if 0 <= idx < len(s) else UNDEFINED
    fn = STRING_METHODS.get(prop)
    if fn is None: return UNDEFINED
    return lambda *args, _fn=fn, _s=s, _i=interpreter: _fn(_i, _s, list(args))


def _replace(i, s, args):
    a = js_to_string(args[0]) if args else ""
    b = js_to_string(args[1]) if len(args) > 1 else ""
    return s.replace(a, b, 1)

def _replaceAll(i, s, args):
    a = js_to_string(args[0]) if args else ""
    b = js_to_string(args[1]) if len(args) > 1 else ""
    return s.replace(a, b)

def _substring(i, s, args):
    start = int(js_to_number(args[0])) if args else 0
    end = int(js_to_number(args[1])) if len(args) > 1 and not is_undefined(args[1]) else len(s)
    start = max(0, min(start, len(s)))
    end = max(0, min(end, len(s)))
    if start > end: start, end = end, start
    return s[start:end]

def _slice(i, s, args):
    start = int(js_to_number(args[0])) if args else 0
    end = int(js_to_number(args[1])) if len(args) > 1 and not is_undefined(args[1]) else len(s)
    return s[start:end]

def _split(i, s, args):
    if not args or is_undefined(args[0]):
        return [s]
    sep = js_to_string(args[0])
    if sep == "":
        return list(s)
    limit = int(js_to_number(args[1])) if len(args) > 1 and not is_undefined(args[1]) else None
    parts = s.split(sep)
    if limit is not None: parts = parts[:limit]
    return parts

def _trim(i, s, args): return s.strip()
def _trimStart(i, s, args): return s.lstrip()
def _trimEnd(i, s, args): return s.rstrip()
def _toUpperCase(i, s, args): return s.upper()
def _toLowerCase(i, s, args): return s.lower()
def _includes(i, s, args): return js_to_string(args[0]) in s if args else False
def _startsWith(i, s, args): return s.startswith(js_to_string(args[0])) if args else False
def _endsWith(i, s, args): return s.endswith(js_to_string(args[0])) if args else False
def _indexOf(i, s, args):
    if not args: return -1
    return s.find(js_to_string(args[0]))
def _lastIndexOf(i, s, args):
    if not args: return -1
    return s.rfind(js_to_string(args[0]))
def _charAt(i, s, args):
    idx = int(js_to_number(args[0])) if args else 0
    return s[idx] if 0 <= idx < len(s) else ""
def _charCodeAt(i, s, args):
    idx = int(js_to_number(args[0])) if args else 0
    if 0 <= idx < len(s): return ord(s[idx])
    from ..runtime.values import NaN
    return NaN
def _repeat(i, s, args):
    n = int(js_to_number(args[0])) if args else 0
    if n < 0: raise Exception("Invalid count value")
    return s * n
def _concat(i, s, args):
    return s + "".join(js_to_string(a) for a in args)
def _padStart(i, s, args):
    n = int(js_to_number(args[0])) if args else 0
    pad = js_to_string(args[1]) if len(args) > 1 else " "
    if len(s) >= n or not pad: return s
    fill = (pad * ((n - len(s)) // len(pad) + 1))[: n - len(s)]
    return fill + s
def _padEnd(i, s, args):
    n = int(js_to_number(args[0])) if args else 0
    pad = js_to_string(args[1]) if len(args) > 1 else " "
    if len(s) >= n or not pad: return s
    fill = (pad * ((n - len(s)) // len(pad) + 1))[: n - len(s)]
    return s + fill


STRING_METHODS = {
    "replace": _replace, "replaceAll": _replaceAll,
    "substring": _substring, "slice": _slice, "split": _split,
    "trim": _trim, "trimStart": _trimStart, "trimEnd": _trimEnd,
    "toUpperCase": _toUpperCase, "toLowerCase": _toLowerCase,
    "includes": _includes, "startsWith": _startsWith, "endsWith": _endsWith,
    "indexOf": _indexOf, "lastIndexOf": _lastIndexOf,
    "charAt": _charAt, "charCodeAt": _charCodeAt,
    "repeat": _repeat, "concat": _concat,
    "padStart": _padStart, "padEnd": _padEnd,
}
