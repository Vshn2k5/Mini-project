"""
intent_classifier.py — Hybrid Intent Classification Engine
============================================================
Production-grade NLP pipeline: TF-IDF + LinearSVC + Rules + Context.

Architecture:
  User Message → Preprocess → SVM Classifier → Rule Validator → Context Resolver → Intent

Supports 5 intent classes (50 samples each, balanced):
  greeting, recommendation, reasoning, menu_query, general_chat
"""

import os
import re
import joblib
from typing import Tuple

# ── Paths ──────────────────────────────────────────────────────────────
AI_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(AI_ENGINE_DIR, "intent_model.pkl")


# ── Text Preprocessing ────────────────────────────────────────────────
def preprocess(text: str) -> str:
    """Normalize text: lowercase, strip, remove punctuation."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


# ── Balanced Training Dataset (50 samples per intent = 250 total) ─────
TRAINING_DATA = [
    # ══════════════════════════════════════════════════════════════════
    # ── greeting (50 samples) ──
    # ══════════════════════════════════════════════════════════════════
    ("hello", "greeting"),
    ("hi", "greeting"),
    ("hey", "greeting"),
    ("hey there", "greeting"),
    ("good morning", "greeting"),
    ("good afternoon", "greeting"),
    ("good evening", "greeting"),
    ("hi there", "greeting"),
    ("hello there", "greeting"),
    ("howdy", "greeting"),
    ("whats up", "greeting"),
    ("yo", "greeting"),
    ("hola", "greeting"),
    ("greetings", "greeting"),
    ("sup", "greeting"),
    ("hey buddy", "greeting"),
    ("hello assistant", "greeting"),
    ("hi assistant", "greeting"),
    ("good day", "greeting"),
    ("morning", "greeting"),
    ("evening", "greeting"),
    ("hey ai", "greeting"),
    ("hi bot", "greeting"),
    ("hello bot", "greeting"),
    ("hey healthbite", "greeting"),
    ("hi healthbite", "greeting"),
    ("hello healthbite", "greeting"),
    ("namaste", "greeting"),
    ("hey how are you", "greeting"),
    ("hi how are you doing", "greeting"),
    ("hello good morning", "greeting"),
    ("hey good evening", "greeting"),
    ("wassup", "greeting"),
    ("hello hello", "greeting"),
    ("hey hey", "greeting"),
    ("hi hi", "greeting"),
    ("good night", "greeting"),
    ("hey whats going on", "greeting"),
    ("hii", "greeting"),
    ("hiii", "greeting"),
    ("helloo", "greeting"),
    ("hellooo", "greeting"),
    ("heyyy", "greeting"),
    ("hey assistant how are you", "greeting"),
    ("hello how are you today", "greeting"),
    ("hi good afternoon", "greeting"),
    ("good morning healthbite", "greeting"),
    ("hey good morning", "greeting"),
    ("well hello there", "greeting"),
    ("hi there healthbite", "greeting"),

    # ══════════════════════════════════════════════════════════════════
    # ── recommendation (50 samples) ──
    # ══════════════════════════════════════════════════════════════════
    ("recommend a healthy meal", "recommendation"),
    ("suggest a lunch option", "recommendation"),
    ("what should I eat today", "recommendation"),
    ("recommend healthy food", "recommendation"),
    ("any healthy lunch options", "recommendation"),
    ("suggest something healthy", "recommendation"),
    ("what is a good meal for me", "recommendation"),
    ("suggest a breakfast", "recommendation"),
    ("recommend food for diabetes", "recommendation"),
    ("what can I eat safely", "recommendation"),
    ("give me a healthy option", "recommendation"),
    ("best food for me today", "recommendation"),
    ("suggest low calorie food", "recommendation"),
    ("recommend a snack", "recommendation"),
    ("what should I order", "recommendation"),
    ("healthy meal suggestions", "recommendation"),
    ("show me healthy choices", "recommendation"),
    ("I need food suggestions", "recommendation"),
    ("which food is best for me", "recommendation"),
    ("whats healthy on the menu", "recommendation"),
    ("recommend lunch", "recommendation"),
    ("suggest dinner", "recommendation"),
    ("what food is safe for diabetes", "recommendation"),
    ("healthy options please", "recommendation"),
    ("best meal for weight loss", "recommendation"),
    ("suggest a healthy snack for me", "recommendation"),
    ("recommend breakfast for hypertension", "recommendation"),
    ("what food should a diabetic eat", "recommendation"),
    ("give me low sodium options", "recommendation"),
    ("suggest low sugar food", "recommendation"),
    ("recommend something with protein", "recommendation"),
    ("high protein meal suggestions", "recommendation"),
    ("best food for my health", "recommendation"),
    ("what is safe to eat with my condition", "recommendation"),
    ("quick healthy meal suggestion", "recommendation"),
    ("recommend a balanced meal", "recommendation"),
    ("suggest a light lunch", "recommendation"),
    ("whats the healthiest thing on the menu", "recommendation"),
    ("suggest food under 400 calories", "recommendation"),
    ("recommend veg food for me", "recommendation"),
    ("best vegetarian option", "recommendation"),
    ("suggest a plant based meal", "recommendation"),
    ("give me your best recommendation", "recommendation"),
    ("what should I eat for lunch", "recommendation"),
    ("pick a meal for me", "recommendation"),
    ("find me a healthy food", "recommendation"),
    ("I want healthy food", "recommendation"),
    ("tell me what to eat", "recommendation"),
    ("whats good for me", "recommendation"),
    ("choose a food for me", "recommendation"),

    # ══════════════════════════════════════════════════════════════════
    # ── reasoning (50 samples) ──
    # ══════════════════════════════════════════════════════════════════
    ("why is palak dal good", "reasoning"),
    ("explain why this food is healthy", "reasoning"),
    ("why was this recommended", "reasoning"),
    ("why not recommended foods", "reasoning"),
    ("why is it not safe for me", "reasoning"),
    ("why should I avoid this", "reasoning"),
    ("explain this recommendation", "reasoning"),
    ("what makes this food healthy", "reasoning"),
    ("why is this food bad for me", "reasoning"),
    ("reason for this recommendation", "reasoning"),
    ("why is this score low", "reasoning"),
    ("why not this food", "reasoning"),
    ("explain the health score", "reasoning"),
    ("why avoid this meal", "reasoning"),
    ("tell me why this is recommended", "reasoning"),
    ("how is this food scored", "reasoning"),
    ("why is this not recommended", "reasoning"),
    ("whats wrong with this food", "reasoning"),
    ("why did you choose this", "reasoning"),
    ("explain the score", "reasoning"),
    ("why this food and not another", "reasoning"),
    ("reason it is not recommended", "reasoning"),
    ("why is the health score so low", "reasoning"),
    ("what makes this bad for my health", "reasoning"),
    ("explain why I should avoid this", "reasoning"),
    ("why is pizza not good for me", "reasoning"),
    ("why did you suggest palak dal", "reasoning"),
    ("how did you calculate the score", "reasoning"),
    ("why are these foods not safe", "reasoning"),
    ("explain the compatibility score", "reasoning"),
    ("why is the confidence low", "reasoning"),
    ("whats the reasoning behind this", "reasoning"),
    ("why should I eat this instead", "reasoning"),
    ("how was this recommendation made", "reasoning"),
    ("why is biryani not safe", "reasoning"),
    ("tell me why this score is bad", "reasoning"),
    ("why is this harmful for diabetes", "reasoning"),
    ("why is sodium bad for hypertension", "reasoning"),
    ("explain why sugar is dangerous", "reasoning"),
    ("why not recommended", "reasoning"),
    ("why was this food avoided", "reasoning"),
    ("why is this food unsuitable", "reasoning"),
    ("what is wrong with eating this", "reasoning"),
    ("explain the ai confidence value", "reasoning"),
    ("how does the scoring work", "reasoning"),
    ("why does this food have a low score", "reasoning"),
    ("can you explain the health match", "reasoning"),
    ("why is this rated poorly", "reasoning"),
    ("what factors affected the score", "reasoning"),
    ("how was the health compatibility calculated", "reasoning"),

    # ══════════════════════════════════════════════════════════════════
    # ── menu_query (50 samples) ──
    # ══════════════════════════════════════════════════════════════════
    ("show menu", "menu_query"),
    ("what foods are available", "menu_query"),
    ("whats on the menu today", "menu_query"),
    ("show me the menu", "menu_query"),
    ("list available foods", "menu_query"),
    ("what can I order today", "menu_query"),
    ("menu items please", "menu_query"),
    ("show food options", "menu_query"),
    ("whats available right now", "menu_query"),
    ("todays menu", "menu_query"),
    ("can I see the menu", "menu_query"),
    ("is paneer tikka available", "menu_query"),
    ("do you have biryani", "menu_query"),
    ("is pizza available today", "menu_query"),
    ("what items do you have", "menu_query"),
    ("display the menu", "menu_query"),
    ("list all food items", "menu_query"),
    ("show all available dishes", "menu_query"),
    ("what dishes are served today", "menu_query"),
    ("menu for today", "menu_query"),
    ("is there any veg food available", "menu_query"),
    ("do you serve non veg today", "menu_query"),
    ("any breakfast items available", "menu_query"),
    ("show lunch options", "menu_query"),
    ("what snacks do you have", "menu_query"),
    ("list all items in the canteen", "menu_query"),
    ("is dal available", "menu_query"),
    ("do you have idli", "menu_query"),
    ("is chicken available", "menu_query"),
    ("what beverages do you have", "menu_query"),
    ("show dessert options", "menu_query"),
    ("are there salads on the menu", "menu_query"),
    ("open the menu", "menu_query"),
    ("whats for lunch today", "menu_query"),
    ("whats cooking today", "menu_query"),
    ("any new items today", "menu_query"),
    ("show me todays specials", "menu_query"),
    ("is dosa available", "menu_query"),
    ("do you have pasta today", "menu_query"),
    ("any soups available", "menu_query"),
    ("show the full menu", "menu_query"),
    ("list breakfast items", "menu_query"),
    ("what veg items are there", "menu_query"),
    ("do you have sandwiches", "menu_query"),
    ("check if rice is available", "menu_query"),
    ("is samosa available today", "menu_query"),
    ("any non veg items on the menu", "menu_query"),
    ("show all veg options", "menu_query"),
    ("list desserts available", "menu_query"),
    ("what drinks are available", "menu_query"),

    # ══════════════════════════════════════════════════════════════════
    # ── general_chat (50 samples) ──
    # ══════════════════════════════════════════════════════════════════
    ("thank you", "general_chat"),
    ("thanks", "general_chat"),
    ("okay got it", "general_chat"),
    ("thats helpful", "general_chat"),
    ("nice", "general_chat"),
    ("cool", "general_chat"),
    ("how are you", "general_chat"),
    ("who are you", "general_chat"),
    ("what can you do", "general_chat"),
    ("help me", "general_chat"),
    ("tell me about yourself", "general_chat"),
    ("are you an AI", "general_chat"),
    ("what is a healthy protein source", "general_chat"),
    ("how much protein should I eat", "general_chat"),
    ("is paneer healthy", "general_chat"),
    ("what foods reduce blood pressure", "general_chat"),
    ("is tofu good for diabetes", "general_chat"),
    ("how many calories should I eat", "general_chat"),
    ("what is BMI", "general_chat"),
    ("tips for healthy eating", "general_chat"),
    ("thanks a lot", "general_chat"),
    ("thank you so much", "general_chat"),
    ("that was useful", "general_chat"),
    ("great thanks", "general_chat"),
    ("ok thanks", "general_chat"),
    ("got it thanks", "general_chat"),
    ("alright", "general_chat"),
    ("okay", "general_chat"),
    ("sure", "general_chat"),
    ("understood", "general_chat"),
    ("makes sense", "general_chat"),
    ("I see", "general_chat"),
    ("what are the benefits of fiber", "general_chat"),
    ("how does protein help the body", "general_chat"),
    ("is brown rice better than white rice", "general_chat"),
    ("what vitamins should I take", "general_chat"),
    ("how much water should I drink daily", "general_chat"),
    ("what is a balanced diet", "general_chat"),
    ("how to eat healthy on a budget", "general_chat"),
    ("what are superfoods", "general_chat"),
    ("is fasting healthy", "general_chat"),
    ("what is intermittent fasting", "general_chat"),
    ("how to lose weight naturally", "general_chat"),
    ("what foods boost immunity", "general_chat"),
    ("bye", "general_chat"),
    ("goodbye", "general_chat"),
    ("see you later", "general_chat"),
    ("what is the difference between carbs and sugar", "general_chat"),
    ("how important is breakfast", "general_chat"),
    ("what is a calorie deficit", "general_chat"),
]


# ── Rule-Based Validators ─────────────────────────────────────────────
# Strong keyword rules that override SVM when pattern is unambiguous

_RULE_OVERRIDES = [
    # (keywords, required_intent, min_score_override)
    ({"hello", "hi", "hey", "howdy", "namaste", "hola", "greetings"}, "greeting", 0.98),
    ({"bye", "goodbye", "see you"}, "general_chat", 0.95),
    ({"recommend", "suggest", "suggestion"}, "recommendation", 0.95),
    ({"why not recommended", "not recommended"}, "reasoning", 0.97),
    ({"show menu", "open menu", "todays menu", "menu items"}, "menu_query", 0.97),
]


def _rule_check(message: str) -> Tuple[str, float] | None:
    """Check if a strong keyword rule matches. Returns (intent, confidence) or None."""
    msg = message.lower().strip()
    # Multi-word rules first (more specific)
    for keywords, intent, confidence in _RULE_OVERRIDES:
        for kw in keywords:
            if " " in kw and kw in msg:
                return intent, confidence
    # Single-word rules
    words = set(msg.split())
    for keywords, intent, confidence in _RULE_OVERRIDES:
        single_kws = {kw for kw in keywords if " " not in kw}
        if words & single_kws:
            return intent, confidence
    return None


# ── Context Resolver ───────────────────────────────────────────────────

def resolve_with_context(message: str, svm_intent: str, svm_conf: float,
                         conversation_history: list = None) -> Tuple[str, float]:
    """
    Resolve follow-up intents using conversation context.
    Handles: "why?", "it", "that food", "can I order it?"
    """
    msg = message.lower().strip()
    short = len(msg.split()) <= 3

    if not conversation_history:
        return svm_intent, svm_conf

    last_intent = None
    for turn in reversed(conversation_history):
        if turn.get("intent"):
            last_intent = turn["intent"]
            break

    # Follow-up patterns: short messages that reference previous context
    if short:
        # "why?" / "why not?" → reasoning about previous topic
        if msg in {"why", "why not", "but why", "how come", "explain"}:
            return "reasoning", 0.95

        # "yes" / "order it" / "can i" → continue previous intent
        if any(w in msg for w in ["yes", "yeah", "order", "ok do it", "go ahead"]):
            if last_intent in {"recommendation", "menu_query"}:
                return last_intent, 0.90

        # "what else" / "more options" → repeat recommendation
        if any(p in msg for p in ["what else", "more options", "another", "anything else", "other options"]):
            return "recommendation", 0.92

    return svm_intent, svm_conf


# ── Training ───────────────────────────────────────────────────────────

def train_intent_model() -> dict:
    """Train TF-IDF + LinearSVC intent classifier and save to disk."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score
    import numpy as np

    texts = [preprocess(t[0]) for t in TRAINING_DATA]
    labels = [t[1] for t in TRAINING_DATA]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 3),
            stop_words="english",
            max_features=5000,
            sublinear_tf=True,
        )),
        ("svm", LinearSVC(
            max_iter=10000,
            C=5.0,
            class_weight="balanced",
        )),
    ])

    pipeline.fit(texts, labels)

    cv_folds = min(5, min(labels.count(l) for l in set(labels)))
    scores = cross_val_score(pipeline, texts, labels, cv=max(2, cv_folds), scoring="accuracy")
    accuracy = float(np.mean(scores))

    joblib.dump(pipeline, MODEL_PATH)
    print(f"[IntentClassifier] Model saved to {MODEL_PATH}")
    print(f"[IntentClassifier] Training samples: {len(texts)} (balanced: 50/class)")
    print(f"[IntentClassifier] Cross-val accuracy: {accuracy:.2%}")

    return {
        "model_path": MODEL_PATH,
        "training_samples": len(texts),
        "intents": sorted(set(labels)),
        "cv_accuracy": round(accuracy, 4),
    }


# ── Model Loading ──────────────────────────────────────────────────────
_model = None


def load_intent_model():
    """Load the trained intent model from disk (cached after first load)."""
    global _model
    if _model is not None:
        return _model
    try:
        _model = joblib.load(MODEL_PATH)
        print("[IntentClassifier] ML intent model loaded.")
        return _model
    except Exception as exc:
        print(f"[IntentClassifier] Model not found, will use keyword fallback: {exc}")
        return None


# ── Keyword Fallback ───────────────────────────────────────────────────

def _keyword_fallback(message: str) -> Tuple[str, float]:
    """Original keyword-based intent detection as safety net."""
    msg = (message or "").lower()
    if any(w in msg for w in ["hello", "hi", "hey"]):
        return "greeting", 1.0
    if any(w in msg for w in ["recommend", "suggest", "healthy", "what should i eat", "best food"]):
        return "recommendation", 0.92
    if any(w in msg for w in ["why", "reason", "recommended", "not recommended", "avoid"]):
        return "reasoning", 0.90
    if any(w in msg for w in ["menu", "available", "show", "list"]):
        return "menu_query", 0.85
    return "general_chat", 0.60


# ── Main Classification Function ──────────────────────────────────────

def classify_intent(message: str, conversation_history: list = None) -> Tuple[str, float]:
    """
    Hybrid Intent Detection: SVM + Rules + Context Resolver

    Pipeline:
      1. Preprocess message
      2. Rule check (strong patterns override SVM)
      3. SVM classification
      4. Context resolution (follow-up questions)

    Returns:
        (intent_label, confidence)
    """
    message = (message or "").strip()
    if not message:
        return "general_chat", 0.50

    # Step 1: Rule-based override for unambiguous patterns
    rule_result = _rule_check(message)
    if rule_result:
        return rule_result

    # Step 2: ML classification
    model = load_intent_model()
    if model is None:
        return _keyword_fallback(message)

    try:
        predicted = model.predict([preprocess(message)])[0]

        # Confidence from decision function
        decision = model.decision_function([preprocess(message)])[0]
        import numpy as np
        if hasattr(decision, "__len__"):
            # Temperature=1.0 softmax (natural calibration)
            exp_scores = np.exp(decision - np.max(decision))
            probs = exp_scores / exp_scores.sum()
            confidence = float(np.max(probs))
        else:
            confidence = float(1 / (1 + np.exp(-abs(decision))))

        confidence = round(confidence, 2)

        # Step 3: Context resolution for follow-up questions
        final_intent, final_conf = resolve_with_context(
            message, predicted, confidence, conversation_history
        )

        return final_intent, final_conf

    except Exception as exc:
        print(f"[IntentClassifier] Prediction error: {exc}")
        return _keyword_fallback(message)


# ── Auto-train on first import if model doesn't exist ──────────────────
if not os.path.exists(MODEL_PATH):
    try:
        print("[IntentClassifier] No model found — training now...")
        train_intent_model()
    except ImportError:
        print("[IntentClassifier] scikit-learn not available, using keyword fallback only.")
