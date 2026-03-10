"""
health_scoring.py — Explainable AI Health Risk Scoring
=======================================================
Calculates a 0-100 health score for any food item based on
clinical nutrition thresholds (Diabetes, Hypertension, Allergy).
Returns a detailed explanation for demo / evaluator use.
"""


# ─── Medical Thresholds ────────────────────────────────────────────────────────

DIABETES_SAFE_SUGAR     = 10   # g — SAFE  ≤ 10
DIABETES_MODERATE_SUGAR = 15   # g — MODERATE 11–15
DIABETES_RISK_SUGAR     = 30   # g — RISK 16–30, SEVERE > 30

HBP_SAFE_SODIUM         = 200  # mg — SAFE  ≤ 200
HBP_MODERATE_SODIUM     = 400  # mg — MODERATE 201–400
HBP_RISK_SODIUM         = 800  # mg — RISK 401–800, SEVERE > 800


def get_diabetes_risk(sugar: float) -> tuple[str, int]:
    """Returns (risk_label, penalty_points)"""
    if sugar > DIABETES_RISK_SUGAR:
        return "SEVERE", 50
    elif sugar > DIABETES_MODERATE_SUGAR:
        return "RISK", 35
    elif sugar > DIABETES_SAFE_SUGAR:
        return "MODERATE", 15
    return "SAFE", 0


def get_hypertension_risk(sodium: float) -> tuple[str, int]:
    """Returns (risk_label, penalty_points)"""
    if sodium > HBP_RISK_SODIUM:
        return "SEVERE", 50
    elif sodium > HBP_MODERATE_SODIUM:
        return "RISK", 35
    elif sodium > HBP_SAFE_SODIUM:
        return "MODERATE", 15
    return "SAFE", 0


def get_allergy_risk(food: dict, user_allergies: list[str]) -> tuple[str, list[str], int]:
    """
    user_allergies: list of strings from ["nuts", "milk", "seafood", "gluten", "soy"]
    Returns (risk_label, triggered_allergens, penalty_points)
    """
    allergen_map = {
        "nuts":    food.get("nut_allergy", False),
        "milk":    food.get("milk_allergy", False),
        "seafood": food.get("seafood_allergy", False),
        "gluten":  food.get("gluten_allergy", False),
        "soy":     food.get("soy_allergy", False),
    }
    triggered = [name.upper() for name, is_present in allergen_map.items()
                 if is_present and name in user_allergies]

    if triggered:
        return "DANGER", triggered, 50
    return "SAFE", [], 0


def calculate_health_score(food: dict, user_allergies: list[str] = None) -> dict:
    """
    Main scoring function.
    Returns a rich dict with score, labels, and explanation strings
    suitable for direct rendering in the recommendation card.

    food dict must have: sugar, sodium, nut_allergy, milk_allergy,
                         seafood_allergy, gluten_allergy, soy_allergy
    """
    if user_allergies is None:
        user_allergies = []

    score = 100
    reasons = []
    warnings = []

    # ── Diabetes ──
    diabetes_label, diabetes_penalty = get_diabetes_risk(food.get("sugar", 0))
    score -= diabetes_penalty
    sugar_g = food.get("sugar", 0)
    if diabetes_label == "SAFE":
        reasons.append(f"sugar {sugar_g}g (diabetes safe ✓)")
    elif diabetes_label == "MODERATE":
        warnings.append(f"sugar {sugar_g}g (moderate for diabetes)")
    else:
        warnings.append(f"sugar {sugar_g}g — HIGH DIABETES RISK ⚠")

    # ── Hypertension ──
    hbp_label, hbp_penalty = get_hypertension_risk(food.get("sodium", 0))
    score -= hbp_penalty
    sodium_mg = food.get("sodium", 0)
    if hbp_label == "SAFE":
        reasons.append(f"sodium {sodium_mg}mg (BP safe ✓)")
    elif hbp_label == "MODERATE":
        warnings.append(f"sodium {sodium_mg}mg (moderate for BP)")
    else:
        warnings.append(f"sodium {sodium_mg}mg — HIGH BP RISK ⚠")

    # ── Allergen ──
    allergy_label, triggered, allergy_penalty = get_allergy_risk(food, user_allergies)
    score -= allergy_penalty
    if allergy_label == "DANGER":
        warnings.append(f"Contains allergens: {', '.join(triggered)}")
    else:
        reasons.append("allergen free ✓")

    final_score = max(0, min(100, score))

    # Determine overall risk tier
    if final_score >= 75:
        overall_label = "SAFE"
        overall_color = "green"
    elif final_score >= 45:
        overall_label = "MODERATE"
        overall_color = "orange"
    else:
        overall_label = "RISK"
        overall_color = "red"

    return {
        "score": final_score,
        "overall_label": overall_label,
        "overall_color": overall_color,
        "diabetes_risk": diabetes_label,
        "hypertension_risk": hbp_label,
        "allergy_risk": allergy_label,
        "triggered_allergens": triggered,
        "reasons": reasons,
        "warnings": warnings,
        "explanation": _build_explanation(food.get("name", ""), final_score, reasons, warnings)
    }


def _build_explanation(name: str, score: int, reasons: list, warnings: list) -> str:
    """Build a human-readable explanation string for display."""
    lines = [f"Health Score: {score}/100"]
    if reasons:
        lines.append("✓ " + " · ".join(reasons))
    if warnings:
        lines.append("⚠ " + " · ".join(warnings))
    return "\n".join(lines)
