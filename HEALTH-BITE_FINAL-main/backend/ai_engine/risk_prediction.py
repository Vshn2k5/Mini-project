"""
HealthBite — AI Risk Prediction Engine
=======================================
Applies medical-grade threshold rules to classify individual foods
as SAFE / MODERATE / DANGER based on a user's health profile,
then aggregates per-order history into pattern alerts and advice.

No external LLM — fully deterministic.
"""

from __future__ import annotations
from typing import Any


# ─── MEDICAL THRESHOLDS ────────────────────────────────────────────────────────

DIABETES_SAFE_SUGAR     = 8    # g — SAFE  ≤ 8
DIABETES_MODERATE_SUGAR = 20   # g — MODERATE 8–20, RISK >20

HBP_SAFE_SODIUM         = 400  # mg — SAFE  ≤ 400
HBP_MODERATE_SODIUM     = 800  # mg — MODERATE 400–800, RISK >800


def get_diabetes_risk(sugar: float) -> tuple[str, int]:
    """Returns (risk_label, penalty_points)"""
    if sugar > DIABETES_MODERATE_SUGAR:
        return "RISK", 30
    elif sugar > DIABETES_SAFE_SUGAR:
        return "MODERATE", 10
    return "SAFE", 0


def get_hypertension_risk(sodium: float) -> tuple[str, int]:
    """Returns (risk_label, penalty_points)"""
    if sodium > HBP_MODERATE_SODIUM:
        return "RISK", 25
    elif sodium > HBP_SAFE_SODIUM:
        return "MODERATE", 10
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
    
    # Also handle alternate names
    alt_map = {
        "nut": "nuts", "peanut": "nuts", "peanuts": "nuts",
        "dairy": "milk", "fish": "seafood", "wheat": "gluten"
    }
    normalized_allergies = [alt_map.get(a, a) for a in user_allergies]

    triggered = [name.upper() for name, is_present in allergen_map.items()
                 if is_present and name in normalized_allergies]

    if triggered:
        return "DANGER", triggered, 50
    return "SAFE", [], 0


def calculate_health_score(food: dict[str, Any], user_profile: dict[str, Any]) -> dict:
    """
    Main scoring function.
    Returns a rich dict with score, labels, and explanation strings
    suitable for direct rendering in the recommendation card.
    """
    
    raw_allergies = user_profile.get("allergies", "") or ""
    if isinstance(raw_allergies, list):
        user_allergies = [a.lower().strip() for a in raw_allergies]
    else:
        user_allergies = [a.lower().strip() for a in raw_allergies.split(",") if a.strip()]

    score = 100
    reasons = []
    warnings = []

    # ── Diabetes ──
    conditions = [c.lower() for c in (user_profile.get("conditions") or [])]
    
    sugar_g = float(food.get("sugar", 0) or 0)
    if "diabetes" in conditions:
        diabetes_label, diabetes_penalty = get_diabetes_risk(sugar_g)
        score -= diabetes_penalty
        if diabetes_label == "SAFE":
            reasons.append(f"sugar {sugar_g}g (diabetes safe ✓)")
        elif diabetes_label == "MODERATE":
            warnings.append(f"sugar {sugar_g}g (moderate for diabetes)")
        else:
            warnings.append(f"sugar {sugar_g}g — HIGH DIABETES RISK ⚠")
    else:
        diabetes_label = "SAFE"

    # ── Hypertension ──
    sodium_mg = float(food.get("sodium", 0) or 0)
    if "hypertension" in conditions:
        hbp_label, hbp_penalty = get_hypertension_risk(sodium_mg)
        score -= hbp_penalty
        if hbp_label == "SAFE":
            reasons.append(f"sodium {sodium_mg}mg (BP safe ✓)")
        elif hbp_label == "MODERATE":
            warnings.append(f"sodium {sodium_mg}mg (moderate for BP)")
        else:
            warnings.append(f"sodium {sodium_mg}mg — HIGH BP RISK ⚠")
    else:
        hbp_label = "SAFE"

    # ── Allergen ──
    allergy_label, triggered, allergy_penalty = get_allergy_risk(food, user_allergies)
    score -= allergy_penalty
    if allergy_label == "DANGER":
        warnings.append(f"Contains allergens: {', '.join(triggered)}")
    else:
        if user_allergies:
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
        overall_label = "RISK" # Note: mapped from previous RISK to map with frontend DANGER, handled later
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


def classify_risk_level(score: int) -> str:
    """Map the 0-100 score to the frontend DANGER/MODERATE/SAFE labels."""
    if score < 45:
        return "DANGER"
    elif score < 75:
        return "MODERATE"
    return "SAFE"


# ─── DIETARY ADVICE GENERATOR ──────────────────────────────────────────────────

def generate_advice(
    avg_score: float, # Now it's a 0-100 score
    conditions: list[str],
    risky_foods: list[dict],
    avg_daily_sugar: float,
    avg_daily_sodium: float,
    avg_daily_calories: float,
) -> list[str]:
    """
    Return a list of deterministic dietary advice strings based on
    real nutrition data and known health conditions.
    """
    advice: list[str] = []
    conditions_lower = [c.lower() for c in conditions]

    # Score intro (using new 0-100 scale, <45 is danger)
    if avg_score < 45:
        advice.append("Your recent food choices show a HIGH risk pattern. Immediate dietary adjustment is recommended.")
    elif avg_score < 75:
        advice.append("Your recent diet shows MODERATE risk. Small adjustments can significantly improve your health outcomes.")
    else:
        advice.append("Your current diet pattern is within a SAFE range. Keep maintaining these healthy choices.")

    # Condition-specific advice
    if "diabetes" in conditions_lower:
        if avg_daily_sugar > 30:
            advice.append(f"Diabetes Alert: Your average daily sugar ({avg_daily_sugar:.0f}g) exceeds the safe limit of 30g. Avoid sweetened beverages, desserts, and sugary snacks.")
        else:
            advice.append(f"Diabetes: Sugar intake is well controlled ({avg_daily_sugar:.0f}g avg/day). Continue avoiding high-GI foods.")

    if "hypertension" in conditions_lower:
        if avg_daily_sodium > 1500:
            advice.append(f"Hypertension Alert: Average sodium ({avg_daily_sodium:.0f}mg/day) is high. Avoid processed foods, pickles, and salty snacks.")
        else:
            advice.append(f"Hypertension: Sodium intake is acceptable ({avg_daily_sodium:.0f}mg avg/day). Continue choosing low-sodium options.")

    if "obesity" in conditions_lower:
        if avg_daily_calories > 1600:
            advice.append(f"Calorie Watch: Average daily intake ({avg_daily_calories:.0f} kcal) exceeds the 1600 kcal limit for your profile. Opt for grilled or steamed preparations.")

    # Healthy alternatives for high-risk foods
    if risky_foods:
        high_risk_names = [f["name"] for f in risky_foods[:3] if f.get("risk_level") == "DANGER"]
        if high_risk_names:
            advice.append(f"Replace these high-risk items: {', '.join(high_risk_names)}. Consider: Vegetable Idli, Palak Dal, or Grilled Chicken Salad as healthy swaps.")

    # Pattern alert
    if len(risky_foods) >= 4:
        advice.append(f"Pattern Detected: You consumed {len(risky_foods)} high-risk food items in the past 7 days. This pattern increases your health risk by an estimated 20–35% if continued.")

    return advice


# ─── CONSUMPTION PATTERN ANALYSIS ─────────────────────────────────────────────

def analyze_consumption_pattern(
    risky_foods_last_week: list[dict],
    conditions: list[str],
    avg_daily_sugar: float,
    avg_daily_sodium: float,
) -> dict:
    """
    Detect unhealthy eating patterns and project future risk.
    Returns a dict with alert, projection, and severity.
    """
    count = len(risky_foods_last_week)
    severity = "low"
    alert = None
    projection = None

    if count >= 4:
        severity = "high"
        alert = f"Frequent unhealthy consumption detected — {count} high-risk food items in the past 7 days."
    elif count >= 2:
        severity = "moderate"
        alert = f"Moderate risk detected — {count} high-risk food items in the past 7 days."

    # 30-day projection
    risk_increase_pct = 0
    conditions_lower = [c.lower() for c in conditions]

    if "diabetes" in conditions_lower and avg_daily_sugar > 30:
        risk_increase_pct += min(35, int((avg_daily_sugar - 30) * 1.5))
    if "hypertension" in conditions_lower and avg_daily_sodium > 1500:
        risk_increase_pct += min(25, int((avg_daily_sodium - 1500) / 80))

    if risk_increase_pct > 0:
        projection = (
            f"If this eating pattern continues for 30 days, your health risk score may "
            f"increase by approximately {risk_increase_pct}%. "
            f"Switch to lower-risk alternatives now to reverse this trend."
        )

    return {
        "severity": severity,
        "alert":    alert,
        "risky_count_last_7_days": count,
        "projection": projection,
        "risk_increase_estimate_pct": risk_increase_pct,
    }
