"""
ISO-8601 timestamps with a real UTC offset suffix for API and logs.

CircuitPython has no ``time.gmtime`` in the usual build; we use integer calendar
math from the Unix epoch. ``Europe/Vienna`` follows EU daylight saving (last
Sunday of March / October at 01:00 UTC).

RTC should track **UTC** when set via NTP (``tz_offset=0`` in ``wifi_client``).
If the RTC is wrong, formatted times are wrong.
"""

import time

_DEFAULT_TZ = "Europe/Vienna"


def _effective_tz_name(settings) -> str:
    raw = settings.get("TZ") if settings is not None else None
    if raw is None:
        return _DEFAULT_TZ
    s = str(raw).strip()
    return s if s else _DEFAULT_TZ


def _normalize_tz_id(name: str) -> str:
    n = name.strip().lower()
    if n in ("utc", "gmt", "etc/utc", "etc/gmt", "etc/gmt+0", "etc/gmt-0", "zulu"):
        return "utc"
    if n in ("europe/vienna",):
        return "vienna"
    return "vienna"


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _days_in_month(y: int, m: int) -> int:
    dim = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    d = dim[m - 1]
    if m == 2 and _is_leap(y):
        d += 1
    return d


def _timegm(y: int, mo: int, d: int, h: int, mi: int, s: int) -> int:
    """Seconds since 1970-01-01 00:00 UTC for the given UTC civil time."""
    days = 0
    for yy in range(1970, y):
        days += 366 if _is_leap(yy) else 365
    for mm in range(1, mo):
        days += _days_in_month(y, mm)
    days += d - 1
    return days * 86400 + h * 3600 + mi * 60 + s


def _weekday_from_utc_date(y: int, mo: int, d: int) -> int:
    """Monday=0 .. Sunday=6 (matches ``time.struct_time``)."""
    t = _timegm(y, mo, d, 12, 0, 0)
    days1970 = t // 86400
    w = (3 + days1970) % 7
    return w


def _last_sunday_dom(y: int, month: int) -> int:
    d = _days_in_month(y, month)
    while _weekday_from_utc_date(y, month, d) != 6:
        d -= 1
    return d


def _eu_dst_start_utc(y: int) -> int:
    """EU summer time begins: last Sunday in March at 01:00 UTC."""
    d = _last_sunday_dom(y, 3)
    return _timegm(y, 3, d, 1, 0, 0)


def _eu_dst_end_utc(y: int) -> int:
    """EU summer time ends: last Sunday in October at 01:00 UTC."""
    d = _last_sunday_dom(y, 10)
    return _timegm(y, 10, d, 1, 0, 0)


def _utc_ymd_from_epoch(secs: int):
    """Break non-negative epoch seconds into UTC calendar components."""
    if secs < 0:
        return None
    days, sod = divmod(secs, 86400)
    y = 1970
    while True:
        dy = 366 if _is_leap(y) else 365
        if days < dy:
            break
        days -= dy
        y += 1
    m = 1
    while m <= 12:
        dm = _days_in_month(y, m)
        if days < dm:
            break
        days -= dm
        m += 1
    d = days + 1
    h, rem = divmod(sod, 3600)
    mi, s = divmod(rem, 60)
    return (y, m, d, h, mi, s)


def _day_of_year_utc(y: int, mo: int, d: int) -> int:
    """1-based day-of-year for a UTC calendar date."""
    n = d
    for mm in range(1, mo):
        n += _days_in_month(y, mm)
    return n


def utc_epoch_to_struct_time(secs: int) -> time.struct_time:
    """
    UTC ``time.struct_time`` from Unix epoch seconds (non-negative).

    Use this for ``rtc.RTC().datetime`` after NTP: ``adafruit_ntp.NTP.datetime``
    uses ``time.localtime(...)``, which can shift wall fields when the port
    applies a non-zero local offset. ``NTP.utc_ns`` is true UTC.
    """
    parts = _utc_ymd_from_epoch(int(secs))
    if parts is None:
        return time.localtime(0)
    y, mo, d, h, mi, s = parts
    wday = _weekday_from_utc_date(y, mo, d)
    yday = _day_of_year_utc(y, mo, d)
    return time.struct_time((y, mo, d, h, mi, s, wday, yday, -1))


def _vienna_offset_seconds(utc_epoch: int) -> int:
    """CET +3600 s, CEST +7200 s (EU rules)."""
    if utc_epoch < 0:
        return 3600
    parts = _utc_ymd_from_epoch(utc_epoch)
    if parts is None:
        return 3600
    y = parts[0]
    for yy in (y - 1, y, y + 1):
        if yy < 1970:
            continue
        start = _eu_dst_start_utc(yy)
        end = _eu_dst_end_utc(yy)
        if start <= utc_epoch < end:
            return 7200
    return 3600


def _fmt_offset(offset_sec: int) -> str:
    if offset_sec == 0:
        return "Z"
    sign = "+" if offset_sec >= 0 else "-"
    o = abs(offset_sec)
    h = o // 3600
    mi = (o % 3600) // 60
    return f"{sign}{h:02d}:{mi:02d}"


def _format_naive_local_z() -> str:
    """Fallback if epoch math fails (should be rare)."""
    lt = time.localtime()
    return (
        f"{lt.tm_year:04d}-{lt.tm_mon:02d}-{lt.tm_mday:02d}T"
        f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}.000Z"
    )


def format_iso8601_tz(settings=None) -> str:
    """
    Current instant as ``YYYY-MM-DDTHH:MM:SS.000Z`` (UTC) or
    ``…000+01:00`` / ``…000+02:00`` for Europe/Vienna.
    """
    if settings is None:
        from config import Config

        settings = Config.settings
    tz = _normalize_tz_id(_effective_tz_name(settings))
    try:
        t = int(time.time())
    except (TypeError, ValueError):
        t = 0

    if tz == "utc":
        parts = _utc_ymd_from_epoch(t)
        if parts is None:
            return _format_naive_local_z()
        y, mo, d, h, mi, s = parts
        return f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}.000Z"

    o = _vienna_offset_seconds(t)
    tw = t + o
    parts = _utc_ymd_from_epoch(tw)
    if parts is None:
        return _format_naive_local_z()
    y, mo, d, h, mi, s = parts
    return f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}.000{_fmt_offset(o)}"
