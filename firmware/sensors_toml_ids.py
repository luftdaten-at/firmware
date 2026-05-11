"""Parse `SENSOR_MODEL_IDS` comma-separated string (no I2C / sensor imports)."""


def parse_comma_separated_ints(raw):
    """
    Split on commas, strip, parse each token with ``int(x, 0)``.
    Returns ``(values, invalid_tokens)``.
    """
    if raw is None:
        return [], []
    s = str(raw).strip()
    if not s:
        return [], []
    out = []
    bad = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part, 0))
        except ValueError:
            bad.append(part)
    return out, bad
