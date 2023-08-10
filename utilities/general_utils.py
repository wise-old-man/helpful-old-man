import datetime as dt


def get_current_datetime_str():
    try:
        return str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except:
        return None


def get_current_datetime_str_short():
    try:
        return str(dt.datetime.now().strftime('%Y-%m-%d'))
    except:
        return ''
