import pwd


def get_owner(uid):

    try:

        return pwd.getpwuid(uid).pw_name

    except:

        return "unknown"


def is_system_user(uid):

    return uid < 1000