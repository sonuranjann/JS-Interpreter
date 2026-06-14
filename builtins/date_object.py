import time, datetime


def _now_dict():
    t = time.time()
    dt = datetime.datetime.fromtimestamp(t)
    return _from_dt(dt, t * 1000)


def _from_dt(dt: datetime.datetime, ms: float):
    return {
        "__type__": "Date",
        "__ms__": ms,
        "year": dt.year, "month": dt.month - 1, "day": dt.day,
        "hours": dt.hour, "minutes": dt.minute, "seconds": dt.second,
        "ms": int(dt.microsecond / 1000),
    }


def date_to_iso(d):
    dt = datetime.datetime.fromtimestamp(d["__ms__"] / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(dt.microsecond/1000):03d}Z"


def DateClass(*args):
    """Called as `new Date(...)`. Returns a Date object dict with bound methods."""
    if not args:
        d = _now_dict()
    elif len(args) == 1:
        a = args[0]
        if isinstance(a, (int, float)):
            dt = datetime.datetime.fromtimestamp(a / 1000)
            d = _from_dt(dt, a)
        else:
            d = _now_dict()
    else:
        # year, month, day, ...
        year = int(args[0])
        month = int(args[1]) + 1 if len(args) > 1 else 1
        day = int(args[2]) if len(args) > 2 else 1
        hour = int(args[3]) if len(args) > 3 else 0
        minute = int(args[4]) if len(args) > 4 else 0
        sec = int(args[5]) if len(args) > 5 else 0
        dt = datetime.datetime(year, month, day, hour, minute, sec)
        d = _from_dt(dt, dt.timestamp() * 1000)

    # Attach methods bound to this date
    d["getFullYear"] = lambda: d["year"]
    d["getMonth"] = lambda: d["month"]
    d["getDate"] = lambda: d["day"]
    d["getHours"] = lambda: d["hours"]
    d["getMinutes"] = lambda: d["minutes"]
    d["getSeconds"] = lambda: d["seconds"]
    d["getTime"] = lambda: d["__ms__"]
    d["toISOString"] = lambda: date_to_iso(d)
    d["toString"] = lambda: date_to_iso(d)
    return d


def make_date_global():
    """Returns the Date global which also has Date.now()."""
    obj = DateClass
    # We can't easily attach members to a function in dict-land; the interpreter
    # treats Date as constructable. Date.now is handled via wrapping below.
    return obj
