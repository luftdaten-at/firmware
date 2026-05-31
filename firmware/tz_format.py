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


def _effective_tz_name(settings):
    raw = settings.get("TZ") if settings is not None else None
    if raw is None:
        return _DEFAULT_TZ
    s = str(raw).strip()
    return s if s else _DEFAULT_TZ


def _normalize_tz_id(name):
    n = name.strip().lower()
    if n in ("utc", "gmt", "etc/utc", "etc/gmt", "etc/gmt+0", "etc/gmt-0", "zulu"):
        return "utc"
    if n in ("europe/vienna",):
        return "vienna"
    return "vienna"


def _is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _days_in_month(y, m):
    dim = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    d = dim[m - 1]
    if m == 2 and _is_leap(y):
        d += 1
    return d


def _timegm(y, mo, d, h, mi, s):
    """Seconds since 1970-01-01 00:00 UTC for the given UTC civil time."""
    days = 0
    for yy in range(1970, y):
        days += 366 if _is_leap(yy) else 365
    for mm in range(1, mo):
        days += _days_in_month(y, mm)
    days += d - 1
    return days * 86400 + h * 3600 + mi * 60 + s


def _weekday_from_utc_date(y, mo, d):
    """Monday=0 .. Sunday=6 (matches ``time.struct_time``)."""
    t = _timegm(y, mo, d, 12, 0, 0)
    days1970 = t // 86400
    w = (3 + days1970) % 7
    return w


def _last_sunday_dom(y, month):
    d = _days_in_month(y, month)
    while _weekday_from_utc_date(y, month, d) != 6:
        d -= 1
    return d


def _eu_dst_start_utc(y):
    """EU summer time begins: last Sunday in March at 01:00 UTC."""
    d = _last_sunday_dom(y, 3)
    return _timegm(y, 3, d, 1, 0, 0)


def _eu_dst_end_utc(y):
    """EU summer time ends: last Sunday in October at 01:00 UTC."""
    d = _last_sunday_dom(y, 10)
    return _timegm(y, 10, d, 1, 0, 0)


def _utc_ymd_from_epoch(secs):
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


def _day_of_year_utc(y, mo, d):
    """1-based day-of-year for a UTC calendar date."""
    n = d
    for mm in range(1, mo):
        n += _days_in_month(y, mm)
    return n


def utc_epoch_to_struct_time(secs):
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


def _vienna_offset_seconds(utc_epoch):
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


def _fmt_offset(offset_sec):
    if offset_sec == 0:
        return "Z"
    sign = "+" if offset_sec >= 0 else "-"
    o = abs(offset_sec)
    h = o // 3600
    mi = (o % 3600) // 60
    return "%s%02d:%02d" % (sign, h, mi)


def _format_naive_local_z():
    """Fallback if epoch math fails (should be rare)."""
    lt = time.localtime()
    return "%04d-%02d-%02dT%02d:%02d:%02d.000Z" % (
        lt.tm_year,
        lt.tm_mon,
        lt.tm_mday,
        lt.tm_hour,
        lt.tm_min,
        lt.tm_sec,
    )


def _format_iso_utc(y, mo, d, h, mi, s):
    return "%04d-%02d-%02dT%02d:%02d:%02d.000Z" % (y, mo, d, h, mi, s)


def _format_iso_with_offset(y, mo, d, h, mi, s, offset_sec):
    return "%04d-%02d-%02dT%02d:%02d:%02d.000%s" % (
        y,
        mo,
        d,
        h,
        mi,
        s,
        _fmt_offset(offset_sec),
    )


def format_iso8601_tz(settings=None):
    """
    Current instant as ``YYYY-MM-DDTHH:MM:SS.000Z`` (UTC) or
    ``...+01:00`` / ``...+02:00`` for Europe/Vienna.
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
        return _format_iso_utc(y, mo, d, h, mi, s)

    o = _vienna_offset_seconds(t)
    tw = t + o
    parts = _utc_ymd_from_epoch(tw)
    if parts is None:
        return _format_naive_local_z()
    y, mo, d, h, mi, s = parts
    return _format_iso_with_offset(y, mo, d, h, mi, s, o)
