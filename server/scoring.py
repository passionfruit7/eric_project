def calculate_score(file):

    score = 0

    size_mb = file["size_mb"]
    age_days = file["days_old"]
    file_type = file["type"]

    if size_mb > 100:
        score += 40

    elif size_mb > 10:
        score += 20

    if age_days > 180:
        score += 30

    elif age_days > 90:
        score += 15

    if file_type in ["log", "tmp", "iso", "bak"]:
        score += 30

    if score >= 70:
        risk = "high"

    elif score >= 40:
        risk = "medium"

    else:
        risk = "low"

    return {
        "score": score,
        "risk": risk
    }