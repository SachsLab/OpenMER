def parse_ini_try_numeric(settings, key):
    try:
        res = settings.value(key, type=int)
    except TypeError:
        res = None
    if res is None:
        try:
            res = settings.value(key, type=float)
        except TypeError:
            res = None
    return res if res is not None else settings.value(key)
