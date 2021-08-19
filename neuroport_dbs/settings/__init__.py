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
    if res is not None:
        return res
    res = settings.value(key)
    if res == 'false':
        return False
    elif res == 'true':
        return True
    return res
