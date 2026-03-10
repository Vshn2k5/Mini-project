"""
explainable_ai.py — Explainable AI Reasoning Engine
====================================================
Generates human-readable explanation reasons for food recommendations
based on the user's health profile, dietary preferences, and goals.

Used by chatbot_engine.py to enrich RAG context before sending to the LLM.
"""


def explain_recommendation(food: dict, profile: dict, eval_result: dict) -> list[str]:
    """
    Build a list of human-readable reasons explaining why a food
    is or isn't suitable for this user's profile.

    Args:
        food:        Dict with keys like name, calories, sugar, sodium, protein, carbs, fat, dietary_type
        profile:     Normalized user profile dict with disease, dietary_preference, allergies, goal, etc.
        eval_result: Output from _evaluate_food() with score, status, positives, cautions, hard_reject

    Returns:
        List of explanation strings (e.g. ["Matches your vegetarian diet preference", ...])
    """
    reasons: list[str] = []
    food_name = food.get("name", "This food")
    diseases = profile.get("disease", [])
    diet_pref = profile.get("dietary_preference", "")
    goal = profile.get("goal", "")
    activity = profile.get("activity_level", "")
    bmi = profile.get("bmi", 0)
    calorie_target = profile.get("calorie_target", 0)
    protein_req = profile.get("protein_requirement", 0)

    calories = float(food.get("calories") or 0)
    sugar = float(food.get("sugar") or 0)
    sodium = float(food.get("sodium") or 0)
    protein = float(food.get("protein") or 0)
    carbs = float(food.get("carbs") or 0)
    fat = float(food.get("fat") or 0)
    item_diet = str(food.get("dietary_type", "")).lower()

    score = eval_result.get("score", 0)
    status = eval_result.get("status", "")

    # ── Diet preference match ──
    if diet_pref:
        pref_lower = diet_pref.lower()
        if pref_lower in {"veg", "vegetarian"} and item_diet in {"veg", "plant-based", "vegan"}:
            reasons.append(f"Matches your {diet_pref} diet preference")
        elif pref_lower in {"vegan", "plant-based"} and item_diet in {"vegan", "plant-based"}:
            reasons.append(f"Matches your {diet_pref} diet preference")
        elif pref_lower in {"non-veg", "non veg", "nonveg", "omnivore"} and item_diet in {"non-veg", "non veg", "nonveg"}:
            reasons.append(f"Matches your non-vegetarian diet preference")
        elif eval_result.get("hard_reject"):
            reasons.append(f"Does not match your {diet_pref} diet — dietary conflict")

    # ── Health condition analysis ──
    for disease in diseases:
        d = disease.lower()
        if "diab" in d:
            if sugar <= 8:
                reasons.append("Low sugar content supports diabetes/glucose management")
            elif sugar > 15:
                reasons.append(f"High sugar ({sugar}g) may affect blood glucose levels")
            else:
                reasons.append(f"Moderate sugar ({sugar}g) — consume with caution for diabetes")

        if "hyper" in d or "pressure" in d:
            if sodium <= 350:
                reasons.append("Low sodium content is blood-pressure friendly")
            elif sodium > 900:
                reasons.append(f"High sodium ({sodium}mg) may raise blood pressure")
            else:
                reasons.append(f"Moderate sodium ({sodium}mg) — monitor intake for hypertension")

        if "obes" in d:
            if calories <= 350:
                reasons.append("Low calorie content supports weight management goals")
            elif calories > 550:
                reasons.append(f"High calorie content ({calories} kcal) may slow weight-loss progress")

        if "heart" in d or "cardio" in d:
            if fat <= 15:
                reasons.append("Low fat content is heart-friendly")
            elif fat > 30:
                reasons.append(f"High fat ({fat}g) may not be ideal for heart health")

        if "anemi" in d:
            if protein >= 15:
                reasons.append("Good protein content supports iron absorption and recovery")

    # ── Goal-based reasoning ──
    if goal:
        goal_lower = goal.lower()
        if "weight" in goal_lower or "loss" in goal_lower:
            if calories <= 400:
                reasons.append(f"Fits your weight-loss goal ({calories} kcal per serving)")
            elif calories > 550:
                reasons.append(f"Higher calories ({calories} kcal) may not align with weight-loss goals")

        if "muscle" in goal_lower or "gain" in goal_lower:
            if protein >= 18:
                reasons.append(f"High protein ({protein}g) supports muscle building")
            elif protein < 10:
                reasons.append(f"Low protein ({protein}g) may not support muscle-gain goals")

        if "maintain" in goal_lower or "balance" in goal_lower:
            if 300 <= calories <= 600 and protein >= 10:
                reasons.append("Balanced nutrition supports your maintenance goals")

    # ── Calorie target alignment ──
    if calorie_target and calorie_target > 0:
        meal_target = calorie_target / 3  # rough per-meal estimate
        if calories <= meal_target * 1.1:
            reasons.append(f"Fits within your estimated meal calorie budget (~{int(meal_target)} kcal)")
        elif calories > meal_target * 1.3:
            reasons.append(f"Exceeds your estimated meal calorie budget (~{int(meal_target)} kcal)")

    # ── Protein requirement ──
    if protein_req and protein_req > 0:
        meal_protein = protein_req / 3
        if protein >= meal_protein * 0.8:
            reasons.append(f"Provides adequate protein for your daily requirement")

    # ── Macronutrient highlights ──
    if protein >= 18 and "protein" not in " ".join(reasons).lower():
        reasons.append(f"Good protein content ({protein}g) for satiety and recovery")

    if carbs <= 40 and "carb" not in " ".join(reasons).lower():
        reasons.append(f"Moderate carbs ({carbs}g) fit most balanced diet plans")

    if fat > 30 and "fat" not in " ".join(reasons).lower():
        reasons.append(f"Higher fat content ({fat}g) — consider a smaller portion")

    # ── Allergen warnings ──
    allergen_names = []
    allergy_map = {
        "nuts": "nut_allergy", "nut": "nut_allergy",
        "milk": "milk_allergy", "dairy": "milk_allergy",
        "seafood": "seafood_allergy", "fish": "seafood_allergy",
        "gluten": "gluten_allergy", "soy": "soy_allergy",
    }
    for allergy, field in allergy_map.items():
        if allergy in profile.get("allergies", []) and bool(food.get(field, False)):
            allergen_names.append(allergy)
    if allergen_names:
        reasons.append(f"Contains allergens you're sensitive to: {', '.join(allergen_names)}")

    # ── Overall compatibility statement ──
    if not reasons:
        if status == "recommended":
            reasons.append("Generally compatible with your health profile")
        elif status == "caution":
            reasons.append("May require caution based on your health profile")
        else:
            reasons.append("May not align well with your current dietary needs")

    return reasons


def format_explanation_text(food_name: str, reasons: list[str], score: float,
                            ml_confidence: float, status: str,
                            alternatives: list[str] = None) -> str:
    """
    Format the XAI reasons into a structured text block that the LLM
    can use as additional context, or that can be shown directly.
    """
    lines = [f"I analyzed **{food_name}** against your health profile.\n"]

    if status == "recommended":
        lines.append("This food is a good match for your dietary needs because:\n")
    elif status == "caution":
        lines.append("This food can be consumed occasionally, with some considerations:\n")
    else:
        lines.append("This food may not be the best choice right now because:\n")

    for reason in reasons:
        lines.append(f"• {reason}")

    lines.append(f"\n**Health Compatibility Score:** {score}/100")
    lines.append(f"**AI Model Confidence:** {ml_confidence}%")

    if alternatives:
        lines.append(f"\nHealthier alternatives: **{', '.join(alternatives)}**")

    return "\n".join(lines)
