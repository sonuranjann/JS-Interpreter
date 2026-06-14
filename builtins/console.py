import sys
from ..runtime.values import js_to_string, is_array, is_object, is_undefined, is_null, is_bool, is_string, is_number, JSFunction


def _format(value, seen=None):
    """Format a value for console.log similar to Node.js."""
    if seen is None: seen = set()
    if is_undefined(value): return "undefined"
    if is_null(value): return "null"
    if is_bool(value): return "true" if value else "false"
    if is_number(value): return js_to_string(value)
    if is_string(value): return value  # top-level strings printed as-is
    if isinstance(value, JSFunction):
        return f"[Function: {value.name or 'anonymous'}]"
    if callable(value):
        return "[Function (native)]"
    oid = id(value)
    if oid in seen:
        return "[Circular]"
    seen = seen | {oid}
    if is_array(value):
        parts = [_format_nested(v, seen) for v in value]
        return "[ " + ", ".join(parts) + " ]" if parts else "[]"
    if is_object(value):
        # date?
        if value.get("__type__") == "Date":
            from .date_object import date_to_iso
            return date_to_iso(value)
        parts = []
        for k, v in value.items():
            if k.startswith("__"): continue
            parts.append(f"{k}: {_format_nested(v, seen)}")
        return "{ " + ", ".join(parts) + " }" if parts else "{}"
    return js_to_string(value)


def _format_nested(value, seen):
    # Strings get quoted when nested inside arrays/objects, like Node
    if is_string(value):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return _format(value, seen)


def make_console():
    def log(*args):
        sys.stdout.write(" ".join(_format(a) for a in args) + "\n")
    def error(*args):
        sys.stderr.write(" ".join(_format(a) for a in args) + "\n")
    return {"log": log, "error": error, "warn": log, "info": log, "debug": log}
