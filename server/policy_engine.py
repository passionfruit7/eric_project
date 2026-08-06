PROTECTED_PATHS = [

    "/etc",
    "/usr",
    "/bin",
    "/lib"

]


def validate(file):

    path = file["path"]

    uid = file["uid"]

    recommendation = file["recommendation"]

    for protected in PROTECTED_PATHS:

        if path.startswith(protected):

            return "ignore"

    if uid < 1000:

        return "ignore"

    if recommendation not in [

        "archive",

        "compress",

        "ignore"

    ]:

        return "ignore"

    return recommendation