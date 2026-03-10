import json
import os
import traceback
from typing import Dict, List, Optional, Tuple

import joblib
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

from ai_engine.explainable_ai import explain_recommendation, format_explanation_text
from ai_engine.intent_classifier import classify_intent

# ── Entity Memory & Context Ranker ───────────────────────────────────────
session_memory = {}

def store_last_food(user_id, food_name):
    if user_id not in session_memory:
        session_memory[user_id] = {}
    session_memory[user_id]["last_food"] = food_name

FOLLOWUP_PRONOUNS = ["it", "that", "this", "the meal", "the food", "that option"]

def resolve_food_reference(user_id, message):
    msg = (message or "").lower()
    if any(p in msg for p in FOLLOWUP_PRONOUNS):
        if user_id in session_memory:
            return session_memory[user_id].get("last_food")
    return None

FOLLOWUP_WORDS = ["why", "how", "what about", "is it", "can i"]

def context_ranker(intent, confidence, message, last_response, user_id):
    msg = (message or "").lower()
    
    # ── Interpret Profile Queries ──
    if "profile" in msg or "health data" in msg or "analytics" in msg or "trend" in msg:
        if "my" in msg or "check" in msg or "predict" in msg or "show" in msg:
            return "profile_query"

    # ── Interpret Menu Queries ──
    if "menu" in msg or "canteen" in msg or "protein" in msg or "calorie" in msg:
        if "compare" in msg or "list" in msg or "show" in msg or "what" in msg or "foods" in msg:
            return "menu_query"
            
    # ── Interpret Follow-up Reasoning ──
    if confidence < 0.55 or len(msg.split()) <= 4:
        if any(w in msg for w in FOLLOWUP_WORDS):
            active_food = session_memory.get(user_id, {}).get("last_food")
            if active_food or (last_response and any(kw in last_response.lower() for kw in ["recommend", "score", "alternatives"])):
                return "reasoning"
                
    return intent
# ──────────────────────────────────────────────────────────────────────────

AI_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "ai_engine")
MODEL_PATH = os.path.join(AI_ENGINE_DIR, "food_recommender.pkl")
ENCODER_PATH = os.path.join(AI_ENGINE_DIR, "label_encoders.pkl")


class HealthChatbot:
    def __init__(self, user_profiles, menu_db, orders_db):
        self.user_profiles = user_profiles
        self.menu_db = menu_db or []
        self.orders_db = orders_db
        self.model = None
        self.encoders = None
        self._load_ml_assets()

    def _load_ml_assets(self):
        try:
            self.model = joblib.load(MODEL_PATH)
            self.encoders = joblib.load(ENCODER_PATH)
            print("[Chatbot] ML model loaded.")
        except Exception as exc:
            print(f"[Chatbot] ML model unavailable, using rule mode: {exc}")
            self.model = None
            self.encoders = None

    def detect_intent(self, message: str) -> Tuple[str, float]:
        """Hybrid intent detection: SVM + Rules + Context."""
        history = getattr(self, '_conversation_history', None)
        return classify_intent(message, conversation_history=history)

    def _normalize_profile(self, profile: Optional[dict]) -> dict:
        profile = profile or {}
        diseases = profile.get("disease", [])
        if isinstance(diseases, str):
            try:
                diseases = json.loads(diseases)
            except Exception:
                diseases = []

        allergy_set = set()
        raw_allergies = profile.get("allergies", [])
        if isinstance(raw_allergies, str):
            try:
                raw_allergies = json.loads(raw_allergies)
            except Exception:
                raw_allergies = [raw_allergies]
        if isinstance(raw_allergies, list):
            for allergy in raw_allergies:
                if isinstance(allergy, dict):
                    allergy_name = str(allergy.get("name", "")).strip().lower()
                else:
                    allergy_name = str(allergy).strip().lower()
                if allergy_name:
                    allergy_set.add(allergy_name)

        return {
            "age": int(profile.get("age", 25) or 25),
            "bmi": float(profile.get("bmi", 22.0) or 22.0),
            "gender": str(profile.get("gender", "male") or "male").lower(),
            "activity_level": str(profile.get("activity_level", "medium") or "medium").lower(),
            "dietary_preference": str(profile.get("dietary_preference", "veg") or "veg").lower(),
            "disease": [str(d).strip().lower() for d in diseases if str(d).strip()],
            "allergies": allergy_set,
        }

    def _build_ml_features(self, profile: dict) -> Dict[str, object]:
        diseases = profile.get("disease", [])
        health_condition = "normal"
        for d in diseases:
            if "diab" in d:
                health_condition = "diabetes"
                break
            if "hyper" in d or "pressure" in d:
                health_condition = "hypertension"
                break
            if "obes" in d:
                health_condition = "obesity"
                break

        diet_pref = profile.get("dietary_preference", "veg")
        if diet_pref in {"plant-based", "plant based", "plant_based", "vegan"}:
            diet_pref = "vegan"  # map to ML-trained class
        elif diet_pref in {"non-veg", "non veg", "nonveg", "non_veg", "omnivore"}:
            diet_pref = "normal"
        if diet_pref not in {"veg", "vegan", "high_protein", "normal"}:
            diet_pref = "normal"

        bmi_val = float(profile.get("bmi", 22.0))
        if bmi_val < 18.5:
            bmi_cat = "underweight"
        elif bmi_val < 25:
            bmi_cat = "normal"
        elif bmi_val < 30:
            bmi_cat = "overweight"
        else:
            bmi_cat = "obese"

        return {
            "age": profile.get("age", 25),
            "bmi": bmi_val,
            "bmi_category": bmi_cat,
            "gender": profile.get("gender", "male"),
            "activity_level": profile.get("activity_level", "medium"),
            "diet_type": diet_pref,
            "goal": "maintain",
            "health_condition": health_condition,
            "calorie_target": 2000,
            "protein_requirement": 80,
            "carbs_limit": 250,
            "fat_limit": 65,
        }

    def _ml_probabilities(self, profile: dict) -> Dict[str, float]:
        if not self.model or not self.encoders:
            return {}

        try:
            features = self._build_ml_features(profile)
            categorical_cols = ["gender", "activity_level", "diet_type", "goal", "health_condition", "bmi_category"]
            for col in categorical_cols:
                le = self.encoders.get(col)
                if le:
                    raw_value = str(features[col])
                    if raw_value in le.classes_:
                        features[col] = le.transform([raw_value])[0]
                    else:
                        features[col] = 0

            default_feature_order = [
                "age",
                "bmi",
                "bmi_category",
                "gender",
                "activity_level",
                "diet_type",
                "goal",
                "health_condition",
                "calorie_target",
                "protein_requirement",
                "carbs_limit",
                "fat_limit",
            ]
            feature_order = list(getattr(self.model, "feature_names_in_", default_feature_order))
            x_row = {name: features.get(name, 0) for name in feature_order}
            x_frame = pd.DataFrame([x_row])[feature_order]
            proba = self.model.predict_proba(x_frame)[0]

            target_encoder = self.encoders.get("recommended_food")
            if target_encoder is None:
                return {}

            mapping = {}
            for idx, class_id in enumerate(self.model.classes_):
                try:
                    food_name = target_encoder.inverse_transform([class_id])[0]
                    mapping[str(food_name).lower()] = float(proba[idx])
                except Exception:
                    continue
            return mapping
        except Exception as exc:
            print(f"[Chatbot] ML probability generation failed: {exc}")
            return {}

    def _evaluate_food(self, food: dict, profile: dict) -> dict:
        score = 100.0
        positives: List[str] = []
        cautions: List[str] = []
        hard_reject = False

        diseases = profile.get("disease", [])
        diet_pref = profile.get("dietary_preference", "veg")
        item_diet = str(food.get("dietary_type", "veg")).lower()
        sugar = float(food.get("sugar") or 0)
        sodium = float(food.get("sodium") or 0)
        calories = float(food.get("calories") or 0)
        protein = float(food.get("protein") or 0)
        carbs = float(food.get("carbs") or 0)
        fat = float(food.get("fat") or 0)

        if diet_pref in {"vegan", "plant-based", "plant based", "plant_based"} and item_diet not in {"plant-based", "vegan"}:
            hard_reject = True
            score -= 80
            cautions.append("Not plant-based.")
        elif diet_pref in {"veg", "vegetarian"} and item_diet not in {"veg", "plant-based", "vegan"}:
            hard_reject = True
            score -= 80
            cautions.append("Not vegetarian-friendly.")

        allergy_map = {
            "nuts": "nut_allergy",
            "nut": "nut_allergy",
            "milk": "milk_allergy",
            "dairy": "milk_allergy",
            "seafood": "seafood_allergy",
            "fish": "seafood_allergy",
            "gluten": "gluten_allergy",
            "soy": "soy_allergy",
        }
        for allergy, field in allergy_map.items():
            if allergy in profile["allergies"] and bool(food.get(field, False)):
                hard_reject = True
                score -= 95
                cautions.append(f"Contains {allergy}.")

        if any("diab" in d for d in diseases):
            if sugar > 30:
                score -= 50
                cautions.append("Severe Risk: Extremely high sugar for diabetes.")
            elif sugar > 15:
                score -= 35
                cautions.append("Risk: High sugar for diabetes management.")
            elif sugar > 10:
                score -= 15
                cautions.append("Moderate: Monitor sugar intake carefully.")
            else:
                positives.append("Safe: Low sugar supports glucose control.")

        if any(("hyper" in d) or ("pressure" in d) for d in diseases):
            if sodium > 800:
                score -= 50
                cautions.append("Severe Risk: Extremely high sodium increases blood pressure.")
            elif sodium > 400:
                score -= 35
                cautions.append("High Risk: High sodium content.")
            elif sodium > 200:
                score -= 15
                cautions.append("Moderate: Manage portion size for sodium control.")
            else:
                positives.append("Safe: Low sodium is blood-pressure friendly.")

        if any("obes" in d for d in diseases):
            if calories > 550:
                score -= 28
                cautions.append("High calories may slow weight-loss goals.")
            elif calories <= 350:
                positives.append("Moderate calories support weight goals.")

        if protein > 20:
            positives.append("High protein meal for satiety and recovery.")
            score += 6
        elif protein >= 10:
            positives.append("Balanced protein content.")
            score += 3
        else:
            cautions.append("Low protein.")
            score -= 2
            
        if carbs <= 40:
            positives.append("Moderate carbs fit most balanced plans.")
            score += 4
        if fat > 30:
            cautions.append("Higher fat portion; use smaller serving.")
            score -= 8

        final_score = max(0.0, min(100.0, score))
        status = "recommended" if (final_score >= 65 and not hard_reject) else "not_recommended"
        if status == "not_recommended" and final_score >= 45 and not hard_reject:
            status = "caution"

        return {
            "score": round(final_score, 1),
            "status": status,
            "positives": positives,
            "cautions": cautions,
            "hard_reject": hard_reject,
        }

    def _rank_full_menu(self, profile: dict) -> List[dict]:
        ml_probs = self._ml_probabilities(profile)
        ranked = []

        for food in self.menu_db:
            eval_result = self._evaluate_food(food, profile)
            ml_prob = ml_probs.get(str(food.get("name", "")).lower(), 0.0)
            
            if eval_result.get("hard_reject"):
                final_score = eval_result["score"]
            else:
                final_score = max(0.0, min(100.0, (eval_result["score"] * 0.75) + (ml_prob * 25.0)))
                
            ranked.append(
                {
                    "food": food,
                    "rule_score": eval_result["score"],
                    "ml_prob": round(ml_prob * 100, 2),
                    "final_score": round(final_score, 1),
                    "status": eval_result["status"],
                    "positives": eval_result["positives"],
                    "cautions": eval_result["cautions"],
                    "hard_reject": eval_result["hard_reject"],
                }
            )

        ranked.sort(key=lambda x: x["final_score"], reverse=True)
        return ranked

    def _match_food_from_message(self, message: str) -> Optional[str]:
        msg = (message or "").lower()
        best_match = None
        best_len = 0
        for food in self.menu_db:
            name = str(food.get("name", "")).strip()
            lower_name = name.lower()
            if lower_name and lower_name in msg and len(lower_name) > best_len:
                best_match = name
                best_len = len(lower_name)
        return best_match

    def _build_explanation_card(self, item: dict, title: str):
        chip_list = [
            {
                "label": "Health Match",
                "value": f"{item['final_score']}/100",
                "type": "impact",
                "color": "green" if item["final_score"] >= 75 else "orange",
                "icon": "activity",
            },
            {
                "label": "ML Confidence",
                "value": f"{item['ml_prob']}%",
                "type": "nutrient",
                "color": "blue",
                "icon": "sparkles",
            },
        ]

        if item["positives"]:
            chip_list.append(
                {
                    "label": "Why Recommended",
                    "value": item["positives"][0],
                    "type": "impact",
                    "color": "green",
                    "icon": "check-circle",
                }
            )
        elif item["cautions"]:
            chip_list.append(
                {
                    "label": "Why Not Recommended",
                    "value": item["cautions"][0],
                    "type": "warning",
                    "color": "red",
                    "icon": "alert-triangle",
                }
            )

        return {"title": title, "chips": chip_list}

    def _specific_food_response(self, food_name: str, ranked: List[dict]) -> dict:
        selected = next((x for x in ranked if x["food"]["name"].lower() == food_name.lower()), None)
        if not selected:
            return {
                "text": "I could not find that food in the current menu.",
                "type": "text",
                "chips": ["Recommend healthy food", "Why not recommended foods?"],
            }

        if selected["status"] == "recommended":
            text = f"{selected['food']['name']} is recommended for you."
        elif selected["status"] == "caution":
            text = f"{selected['food']['name']} can be taken occasionally, with caution."
        else:
            text = f"{selected['food']['name']} is not recommended for your profile right now."

        reason_yes = selected["positives"] or ["No strong positive signals from your profile."]
        reason_no = selected["cautions"] or ["No major restrictions detected."]
        top_alternatives = [x["food"]["name"] for x in ranked if x["status"] == "recommended" and x["food"]["name"] != selected["food"]["name"]][:3]

        detail = (
            f"{text}\n"
            f"Why recommended: {reason_yes[0]}\n"
            f"Why not recommended: {reason_no[0]}"
        )

        response = {
            "text": detail,
            "type": "explanation",
            "intent": "reasoning",
            "confidence": 0.95,
            "explanation_card": self._build_explanation_card(selected, selected["food"]["name"]),
            "chips": top_alternatives or ["Recommend healthy food", "Show foods to avoid"],
        }
        return response

    def get_recommendation(self, profile: dict, context: dict) -> dict:
        ranked = self._rank_full_menu(profile)
        recommended = [x for x in ranked if x["status"] == "recommended"][:3]
        cautions = [x for x in ranked if x["status"] in {"caution", "not_recommended"}][-2:]

        if not ranked:
            return {"text": "I could not read menu data right now.", "type": "text"}

        if not recommended:
            best = ranked[0]
            return {
                "text": f"No fully safe option found. Closest choice is {best['food']['name']} with caution.",
                "type": "explanation",
                "intent": "recommendation",
                "confidence": 0.86,
                "explanation_card": self._build_explanation_card(best, "Closest Safe Match"),
                "chips": ["Why not recommended foods?", "Show menu-safe options"],
            }

        top = recommended[0]
        alt_names = [x["food"]["name"] for x in recommended[1:]]
        avoid_text = ", ".join([x["food"]["name"] for x in cautions]) if cautions else "none right now"
        text = (
            f"Best healthy choice right now: {top['food']['name']}. "
            f"Also good: {', '.join(alt_names) if alt_names else 'no close alternatives yet'}. "
            f"Foods to avoid for your profile: {avoid_text}."
        )

        return {
            "text": text,
            "type": "explanation",
            "intent": "recommendation",
            "confidence": 0.93,
            "explanation_card": self._build_explanation_card(top, f"Top Pick: {top['food']['name']}"),
            "chips": [
                f"Why {top['food']['name']} recommended?",
                "Why not recommended foods?",
                "Show 3 healthy options",
            ],
        }

    # ── RAG-powered LLM response generator ──────────────────────────────
    def generate_unified_rag_response(self, message, profile, rag_context):
        """Send the user message + grounded RAG context to Groq LLM."""
        try:
            from groq import Groq
        except ImportError:
            print("[Chatbot] groq package not installed – pip install groq")
            return None

        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            print("[Chatbot] GROQ_API_KEY not set in environment.")
            return None

        client = Groq(api_key=api_key)

        diseases = profile.get("disease", [])
        diet_pref = profile.get("dietary_preference", "not specified")

        # Build conversation context if available
        conv_context = ""
        if hasattr(self, '_conversation_history') and self._conversation_history:
            conv_context = "Previous conversation:\n"
            for turn in self._conversation_history[-5:]:
                conv_context += f"User: {turn.get('message', '')}\n"
                conv_context += f"AI: {turn.get('response', '')[:200]}\n"
            conv_context += "---\n"

        prompt = f"""You are a helpful nutrition assistant for a smart canteen.
{conv_context}User message: "{message}"
User health profile:
Diseases: {diseases}
Diet preference: {diet_pref}
Retrieved Database Context:
{rag_context}
Instructions:
1. Answer in a warm, conversational tone like a real AI assistant.
2. Format your response beautifully using Markdown. Use **bold** text for food names and key metrics.
3. If XAI explanation reasons are provided, list them clearly as bullet points for easy reading.
4. After the explanation, mention the Health Compatibility Score and AI Confidence naturally.
5. If healthier alternatives are mentioned, suggest them conversationally.
6. Do NOT invent medical facts or nutritional values.
7. If the user references something from a previous message (like "it", "that food", "why?"), use the conversation history to understand the reference."""

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as exc:
            print(f"[Chatbot] Groq API error: {exc}")
            traceback.print_exc()
            return None

    # ── Main response handler (RAG-augmented) ─────────────────────────
    def get_response(self, user_id, message, context=None, profile=None, conversation_history=None):
        _ = context or {}
        self._conversation_history = conversation_history or []
        normalized_profile = self._normalize_profile(profile)

        # ── 1. Entity Resolver & Context Ranker Pipeline ─────────────
        food_reference = resolve_food_reference(user_id, message)
        intent, confidence = self.detect_intent(message)
        
        last_response = self._conversation_history[-1].get("response", "") if self._conversation_history else ""
        intent = context_ranker(intent, confidence, message, last_response, user_id)

        print(f"\\n--- PIPELINE DIAGNOSTIC ---")
        print(f"MESSAGE: {message}")
        print(f"INTENT: {intent}")
        print(f"CONF: {confidence}")
        print(f"ACTIVE FOOD: {session_memory.get(user_id, {}).get('last_food')}")
        print(f"---------------------------\\n")

        # ── Pronoun/Order Resolver Override ──
        if food_reference and any(w in (message or "").lower() for w in ["order", "can i"]):
            rag_context = f"The user wants to order '{food_reference}'. Confirm warmly that it is available in the canteen and they can order it via the app."
            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            return {
                "text": llm_text or f"Yes, {food_reference} is available in the canteen and you can order it.",
                "type": "text",
                "intent": "general_chat",
                "confidence": 0.99,
                "chips": ["Show full menu", "Check my health profile"],
            }

        # ── Greeting: handle explicitly before anything else ──────────
        if intent == "greeting":
            food_names = [f["name"] for f in self.menu_db[:10]] if self.menu_db else ["menu items"]
            rag_context = (
                f"The user is greeting the assistant. "
                f"Smart Canteen Menu includes items like: {', '.join(food_names)}. "
                f"Greet the user warmly and let them know you can help with food recommendations, "
                f"nutrition questions, and health-based meal analysis."
            )
            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)

            greeting_fallback = (
                "Hello! 👋 I'm your HealthBite AI assistant. I can analyze today's menu against "
                "your health profile, recommend safe meals, and answer nutrition questions. "
                "What would you like to know?"
            )

            return {
                "text": llm_text or greeting_fallback,
                "type": "text",
                "intent": "greeting",
                "confidence": confidence,
                "chips": ["Recommend healthy food", "Why not recommended foods?"],
            }

        # ── Follow-up Question Handler (Fallback Context) ──────────────
        msg_low = (message or "").lower().strip()
        is_short_followup = len(msg_low.split()) <= 5
        has_followup_keywords = any(w in msg_low for w in ["it", "that", "this", "yes", "order", "why", "how come", "what about"])
        
        if self._conversation_history and is_short_followup and has_followup_keywords and intent == "general_chat":
            rag_context = "User is asking a contextual follow-up question. " + (f"The topic revolves around {food_reference}." if food_reference else "")
            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            if llm_text:
                return {
                    "text": llm_text,
                    "type": "text",
                    "intent": intent,
                    "confidence": confidence,
                    "chips": ["Recommend healthy food", "Show full menu"],
                }

        ranked = self._rank_full_menu(normalized_profile)
        msg_food = self._match_food_from_message(message)
        
        # ── Inject Contextual Entity into Engine ──
        active_food = session_memory.get(user_id, {}).get("last_food")
        if not msg_food and intent == "reasoning" and active_food:
            msg_food = active_food

        # ── Scenario A: User asked about a specific food ──────────────
        if msg_food:
            selected = next(
                (x for x in ranked if x["food"]["name"].lower() == msg_food.lower()),
                None,
            )
            if not selected:
                return {
                    "text": "I could not find that food in the current menu.",
                    "type": "text",
                    "chips": ["Recommend healthy food", "Why not recommended foods?"],
                }

            food = selected["food"]
            eval_result = {"score": selected["rule_score"], "status": selected["status"],
                           "positives": selected["positives"], "cautions": selected["cautions"],
                           "hard_reject": selected["hard_reject"]}

            # XAI: generate profile-based explanation reasons
            xai_reasons = explain_recommendation(food, normalized_profile, eval_result)
            top_alternatives = [
                x["food"]["name"]
                for x in ranked
                if x["status"] == "recommended" and x["food"]["name"] != food["name"]
            ][:3]

            rag_context = (
                f"User inquired about food: {food['name']}\n"
                f"Calories: {food.get('calories')}, Sugar: {food.get('sugar')}, "
                f"Protein: {food.get('protein')}, Sodium: {food.get('sodium')}, "
                f"Fat: {food.get('fat')}, Carbs: {food.get('carbs')}\n"
                f"Calculated Health Score: {selected['final_score']}/100\n"
                f"ML Confidence: {selected['ml_prob']}%\n"
                f"Status: {selected['status']}\n"
                f"XAI Explanation Reasons:\n"
                + "\n".join(f"• {r}" for r in xai_reasons) + "\n"
                f"Healthier Alternatives: {', '.join(top_alternatives) if top_alternatives else 'None available'}"
            )

            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            fallback = format_explanation_text(
                food["name"], xai_reasons, selected["final_score"],
                selected["ml_prob"], selected["status"], top_alternatives
            )

            store_last_food(user_id, food["name"])

            return {
                "text": llm_text or fallback,
                "type": "explanation",
                "intent": "reasoning",
                "confidence": 0.95,
                "explanation": xai_reasons,
                "health_score": selected["final_score"],
                "ml_confidence": selected["ml_prob"],
                "alternatives": top_alternatives,
                "explanation_card": self._build_explanation_card(selected, food["name"]),
                "chips": top_alternatives or ["Recommend healthy food", "Show foods to avoid"],
            }

        # ── Scenario: "not recommended" / "why not" queries ────────────
        if "not recommended" in msg_low or ("why not" in msg_low):
            bottom = [x for x in ranked if x["status"] in {"not_recommended", "caution"}][:3]
            if not bottom:
                return {
                    "text": "I do not see strongly unsafe items for your profile in the current menu.",
                    "type": "text",
                    "intent": "reasoning",
                    "confidence": 0.88,
                    "chips": ["Recommend healthy food"],
                }

            rag_context = "Foods NOT recommended for this user:\n"
            all_reasons = []
            for i, item in enumerate(bottom):
                f = item["food"]
                eval_r = {"score": item["rule_score"], "status": item["status"],
                          "positives": item["positives"], "cautions": item["cautions"],
                          "hard_reject": item["hard_reject"]}
                item_reasons = explain_recommendation(f, normalized_profile, eval_r)
                rag_context += (
                    f"{i+1}. {f['name']} (Score: {item['final_score']}, Confidence: {item['ml_prob']}%)\n"
                    f"   Reasons: {'; '.join(item_reasons)}\n"
                )
                all_reasons.extend(item_reasons[:2])

            safe_foods = [x["food"]["name"] for x in ranked if x["status"] == "recommended"][:3]
            if safe_foods:
                rag_context += f"Healthier alternatives: {', '.join(safe_foods)}\n"

            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            first = bottom[0]
            store_last_food(user_id, first["food"]["name"])

            return {
                "text": llm_text or f"Foods currently less suitable: {', '.join([x['food']['name'] for x in bottom])}.",
                "type": "explanation",
                "intent": "reasoning",
                "confidence": 0.92,
                "explanation": all_reasons,
                "health_score": first["final_score"],
                "ml_confidence": first["ml_prob"],
                "alternatives": safe_foods,
                "explanation_card": self._build_explanation_card(first, "Why Not Recommended"),
                "chips": safe_foods or ["Recommend healthy food"],
            }

        # ── Scenario B: Recommendation intent ─────────────────────────
        if intent == "recommendation":
            recommended = [x for x in ranked if x["status"] == "recommended"][:3]

            if not recommended and ranked:
                best = ranked[0]
                eval_r = {"score": best["rule_score"], "status": best["status"],
                          "positives": best["positives"], "cautions": best["cautions"],
                          "hard_reject": best["hard_reject"]}
                xai_reasons = explain_recommendation(best["food"], normalized_profile, eval_r)
                rag_context = (
                    f"No fully safe option found. Closest match:\n"
                    f"1. {best['food']['name']} (Score: {best['final_score']}, Confidence: {best['ml_prob']}%)\n"
                    f"XAI Reasons: {'; '.join(xai_reasons)}\n"
                )
                llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
                store_last_food(user_id, best['food']['name'])
                return {
                    "text": llm_text or f"No fully safe option found. Closest choice is {best['food']['name']} with caution.",
                    "type": "explanation",
                    "intent": "recommendation",
                    "confidence": 0.86,
                    "explanation": xai_reasons,
                    "health_score": best["final_score"],
                    "ml_confidence": best["ml_prob"],
                    "explanation_card": self._build_explanation_card(best, "Closest Safe Match"),
                    "chips": ["Why not recommended foods?", "Show menu-safe options"],
                }

            if not ranked:
                return {"text": "I could not read menu data right now.", "type": "text"}

            rag_context = "Top recommended foods from database for this user:\n"
            top_reasons = []
            for i, item in enumerate(recommended):
                f = item["food"]
                eval_r = {"score": item["rule_score"], "status": item["status"],
                          "positives": item["positives"], "cautions": item["cautions"],
                          "hard_reject": item["hard_reject"]}
                item_reasons = explain_recommendation(f, normalized_profile, eval_r)
                if i == 0:
                    top_reasons = item_reasons
                rag_context += (
                    f"{i+1}. {f['name']} (Score: {item['final_score']}, Confidence: {item['ml_prob']}%)\n"
                    f"   XAI Reasons: {'; '.join(item_reasons[:3])}\n"
                )

            avoid_foods = [x["food"]["name"] for x in ranked if x["status"] in {"caution", "not_recommended"}][-2:]
            if avoid_foods:
                rag_context += f"Foods to avoid: {', '.join(avoid_foods)}\n"

            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            top = recommended[0]
            store_last_food(user_id, top["food"]["name"])

            return {
                "text": llm_text or self.get_recommendation(normalized_profile, context or {}).get("text", ""),
                "type": "explanation",
                "intent": "recommendation",
                "confidence": 0.93,
                "explanation": top_reasons,
                "health_score": top["final_score"],
                "ml_confidence": top["ml_prob"],
                "alternatives": [x["food"]["name"] for x in recommended[1:]],
                "explanation_card": self._build_explanation_card(top, f"Top Pick: {top['food']['name']}"),
                "chips": [
                    f"Why {top['food']['name']} recommended?",
                    "Why not recommended foods?",
                    "Show 3 healthy options",
                ],
            }

        # ── Scenario C: Menu Query ──────────────────────────────────────────
        if intent == "menu_query":
            msg = (message or "").lower()
            sorted_menu = list(self.menu_db)
            if "protein" in msg:
                sorted_menu = sorted(sorted_menu, key=lambda x: x.get("protein", 0) or 0, reverse=True)
            elif "calorie" in msg:
                sorted_menu = sorted(sorted_menu, key=lambda x: x.get("calories", 999) or 999)
                
            top_items = sorted_menu[:5]
            rag_context = "User asked about the menu. Top items:\n"
            for f in top_items:
                rag_context += f"- {f['name']} (Protein: {f.get('protein')}g, Calories: {f.get('calories')}kcal)\n"
                
            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            
            fallback = "Here are some menu highlights based on your query:\n" + "\n".join(f"• **{f['name']}** (Protein: {f.get('protein')}g, Calories: {f.get('calories')}kcal)" for f in top_items)
            
            return {
                "text": llm_text or fallback,
                "type": "text",
                "intent": "menu_query",
                "confidence": confidence,
                "chips": ["Recommend healthy food", "Show full menu"],
            }

        # ── Scenario E: Profile Query ─────────────────────────────────────
        if intent == "profile_query":
            diseases = ", ".join(normalized_profile.get("disease", ["None"]))
            allergies = ", ".join(normalized_profile.get("allergies", ["None"]))
            diet = normalized_profile.get("dietary_preference", "None")
            analytics_data = profile.get("analytics", {})
            
            rag_context = (
                f"User asked about their health profile and analytics. "
                f"Diseases: {diseases}. Allergies: {allergies}. Diet: {diet}. "
            )
            
            if analytics_data:
                avg = analytics_data.get("avg_daily", {})
                score = analytics_data.get("health_score", 0)
                rag_context += f"Analytics Dashboard Data - Health Score: {score}/100. Avg Daily Sugar: {avg.get('sugar', 0)}g, Sodium: {avg.get('sodium', 0)}mg, Calories: {avg.get('calories', 0)}kcal. "
                
                risky_foods = analytics_data.get("risky_foods", [])
                if risky_foods:
                    insights = "\n".join([f"- {r['name']} ({r['risk_level']}): {r['explanation']}" for r in risky_foods[:3]])
                    rag_context += f"Top Risky Foods Recently Consumed:\n{insights}\n"
            
            rag_context += (
                f"Explain how these conditions interact, predict health trends if they don't eat well, "
                f"and give a highly analytical response about managing intensity of {diseases} by reviewing their actual data."
            )
            
            llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)
            
            fallback = (
                f"**Your Health Profile Analysis**\n\n"
                f"• **Dietary Preference:** {diet}\n"
                f"• **Active Conditions:** {diseases}\n"
                f"• **Allergies:** {allergies}\n\n"
                f"*Note: I am in offline mode. If you enable the LLM connection, I can predict your long-term health trends and condition intensities!*"
            )
            
            return {
                "text": llm_text or fallback,
                "type": "text",
                "intent": "profile_query",
                "confidence": 0.99,
                "chips": ["Recommend healthy food", "Show full menu"],
            }

        # ── Scenario F: General Chat (LLM with menu context) ────────────
        food_names = [f["name"] for f in self.menu_db[:15]] if self.menu_db else ["menu items"]
        rag_context = (
            f"General conversation. Smart Canteen Menu includes items like: "
            f"{', '.join(food_names)}. Connect with the user based on their profile."
        )

        llm_text = self.generate_unified_rag_response(message, profile or {}, rag_context)

        fallback = (
            "I am currently operating in offline mode so my conversational abilities are limited. "
            "However, my core engine is fully active! Try asking me to **Recommend a healthy lunch** "
            "or ask **Is the Palak Dal healthy?** to see my health analysis engine in action."
        )

        return {
            "text": llm_text or fallback,
            "type": "text",
            "intent": intent,
            "confidence": confidence,
            "chips": ["Recommend healthy food", "Why not recommended foods?"],
        }
