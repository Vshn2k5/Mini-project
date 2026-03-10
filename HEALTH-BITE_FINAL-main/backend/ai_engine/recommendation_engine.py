import joblib
import os
import pandas as pd

# Import the explainable health scoring module
from ai_engine.health_scoring import calculate_health_score

# Paths
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "food_recommender.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "label_encoders.pkl")


class RecommendationEngine:
    def __init__(self):
        try:
            self.model = joblib.load(MODEL_PATH)
            self.encoders = joblib.load(ENCODER_PATH)
            print("[AI Engine] ML model and encoders loaded successfully.")
        except Exception as e:
            print(f"[AI Engine] Warning loading model/encoders: {e}")
            self.model = None
            self.encoders = None

    def health_filter(self, menu_list, health_condition, user_allergies, diet_type):
        """
        Filter 1: Remove foods that are DANGEROUS for the user's health condition
        or violate their strict dietary preferences (e.g., Vegans getting meat).
        Uses medical thresholds aligned with health_scoring.py.
        """
        filtered = []
        diet_type_lower = diet_type.lower() if diet_type else ""

        for food in menu_list:
            # --- STRICT DIETARY FILTER ---
            food_diet = food.get("dietary_type", "").lower()

            # Vegan users: only Plant-Based foods.
            if diet_type_lower in {"vegan", "plant-based", "plant based", "plant_based"} and food_diet not in {"plant-based", "vegan"}:
                continue

            # Vegetarian users: Veg + Plant-Based foods.
            if diet_type_lower in {"veg", "vegetarian"} and food_diet not in {"veg", "plant-based", "vegan"}:
                continue

            # Omnivore / Non-Veg users: only Non-Veg foods.
            if diet_type_lower in {"non-veg", "non veg", "nonveg", "non_veg", "omnivore"} and food_diet not in {"non-veg", "non veg", "nonveg", "non_veg"}:
                continue


            # --- HEALTH / MEDICAL FILTERS ---
            # Diabetes: skip foods with very high sugar
            if health_condition == "diabetes" and food.get("sugar", 0) > 20:
                continue
            
            # Hypertension: skip foods with very high sodium
            if health_condition == "hypertension" and food.get("sodium", 0) > 800:
                continue
            
            # Allergy: skip foods with any triggered allergen
            allergen_fields = {
                "nuts":    "nut_allergy",
                "milk":    "milk_allergy",
                "seafood": "seafood_allergy",
                "gluten":  "gluten_allergy",
                "soy":     "soy_allergy",
            }
            allergen_hit = False
            for allergy_key, field in allergen_fields.items():
                if allergy_key in user_allergies and food.get(field, False):
                    allergen_hit = True
                    break
            if allergen_hit:
                continue

            filtered.append(food)
        return filtered

    def nutrition_score(self, food, user_profile):
        """Lower score = better nutritional match."""
        cal_diff  = abs(food.get("calories", 0) - user_profile["calorie_target"]) / 500
        prot_diff = abs(food.get("protein",  0) - user_profile["protein_requirement"]) / 50
        carb_diff = abs(food.get("carbs",    0) - user_profile["carbs_limit"]) / 100
        return cal_diff + prot_diff + carb_diff

    def recommend_food(self, user_profile, all_menu_items):
        """
        Hybrid recommendation pipeline:
        1. Health Filter (remove dangerous foods)
        2. Health Scoring (explainable AI score per food)
        3. Nutrition Scoring (macro distance)
        4. ML Ranking (Random Forest refinement)
        5. Return top 5 with full explanations
        """
        health_cond    = user_profile.get("health_condition", "normal").lower()
        user_allergies = [a.lower() for a in user_profile.get("allergies", [])]
        diet_type      = user_profile.get("diet_type", "veg")

        # ── Step 1: Hard Filter ─────────────────────────────────────────────────
        filtered_menu = self.health_filter(all_menu_items, health_cond, user_allergies, diet_type)
        if not filtered_menu:
            return [], "No safe foods found for your current health profile."

        # ── Step 2: Explainable Health Scoring ─────────────────────────────────
        recommendations = []
        for food in filtered_menu:
            # Full explainable health score
            health_score_data = calculate_health_score(food, user_allergies)
            # Nutrition distance (lower is better match)
            nutrition_dist = self.nutrition_score(food, user_profile)
            # Combined match percentage: 50% health score + 50% nutrition fit
            nutrition_fit_pct = max(0, min(100, 100 - (nutrition_dist * 10)))
            combined_score = 0.5 * health_score_data["score"] + 0.5 * nutrition_fit_pct

            recommendations.append({
                "food":            food,
                "score":           nutrition_dist,
                "match_pct":       round(combined_score, 1),
                "health_score":    health_score_data["score"],
                "overall_label":   health_score_data["overall_label"],
                "overall_color":   health_score_data["overall_color"],
                "diabetes_risk":   health_score_data["diabetes_risk"],
                "hbp_risk":        health_score_data["hypertension_risk"],
                "allergy_risk":    health_score_data["allergy_risk"],
                "triggered_allergens": health_score_data["triggered_allergens"],
                "reasons":         health_score_data["reasons"],
                "warnings":        health_score_data["warnings"],
                "explanation":     health_score_data["explanation"],
            })

        # Sort by combined score descending
        recommendations.sort(key=lambda x: x["match_pct"], reverse=True)

        # ── Step 3: ML Ranking Refinement ──────────────────────────────────────
        if self.model and self.encoders:
            try:
                input_data = {
                    "age":              user_profile.get("age", 25),
                    "bmi":              user_profile.get("bmi", 22.0),
                    "gender":           user_profile.get("gender", "male"),
                    "activity_level":   user_profile.get("activity_level", "medium"),
                    "diet_type":        user_profile.get("diet_type", "veg"),
                    "goal":             user_profile.get("goal", "maintain"),
                    "health_condition": health_cond if health_cond in ["diabetes", "hypertension"] else "normal",
                    "calorie_target":       user_profile.get("calorie_target", 2000),
                    "protein_requirement":  user_profile.get("protein_requirement", 80),
                    "carbs_limit":          user_profile.get("carbs_limit", 250),
                    "fat_limit":            user_profile.get("fat_limit", 65),
                }

                # Added bmi_category to match new model feature set
                bmi_val = input_data["bmi"]
                if bmi_val < 18.5: bmi_cat = "underweight"
                elif bmi_val < 25: bmi_cat = "normal"
                elif bmi_val < 30: bmi_cat = "overweight"
                else: bmi_cat = "obese"
                input_data["bmi_category"] = bmi_cat

                categorical_cols = ["gender", "activity_level", "diet_type", "goal", "health_condition", "bmi_category"]
                for col in categorical_cols:
                    le = self.encoders.get(col)
                    if le:
                        try:
                            input_data[col] = le.transform([input_data[col]])[0]
                        except Exception:
                            input_data[col] = 0

                feature_order = ["age", "bmi", "bmi_category", "gender", "activity_level", "diet_type", "goal",
                                 "health_condition", "calorie_target", "protein_requirement",
                                 "carbs_limit", "fat_limit"]
                X = pd.DataFrame([input_data])[feature_order]
                pred_label_id = self.model.predict(X)[0]
                target_le = self.encoders.get("recommended_food")
                ml_recommended_name = target_le.inverse_transform([pred_label_id])[0]

                # Boost the ML-predicted item if it's in the filtered list
                for rec in recommendations:
                    if rec["food"]["name"] == ml_recommended_name:
                        rec["match_pct"] = min(100, rec["match_pct"] + 5)
                        rec["ml_match"] = True

                recommendations.sort(key=lambda x: (not x.get("ml_match", False), -x["match_pct"]))

            except Exception as e:
                print(f"[AI Engine] ML prediction failed (non-critical): {e}")

        return recommendations[:5], None


# Singleton: model loads once at server startup (CHECK 6 of audit)
engine = RecommendationEngine()
