import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os, sys
sys.path.insert(0, ".")

# Delete old model
model_path = os.path.join("ai_engine", "intent_model.pkl")
if os.path.exists(model_path):
    os.remove(model_path)
    print("Old model deleted.")

from ai_engine.intent_classifier import train_intent_model, classify_intent

# Train
result = train_intent_model()
print(f"Samples: {result['training_samples']}, Accuracy: {result['cv_accuracy']:.0%}")
print()

# Test cases
tests = [
    "hello",
    "recommend a healthy meal",
    "why is this food recommended",
    "show me the menu",
    "what is protein",
    "suggest low calorie lunch",
    "hey there",
    "why not recommended foods",
    "is pizza available today",
    "thank you for the help",
    "why",
    "what else",
    "recomend food",
]

print("--- Intent Predictions ---")
for msg in tests:
    intent, conf = classify_intent(msg)
    print(f"  {msg:40s} -> {intent:20s} ({conf:.0%})")

print("\n--- Context Resolution Test ---")
history = [{"message": "suggest a meal", "response": "Palak Dal is good", "intent": "recommendation"}]
msg = "can I order it?"
intent, conf = classify_intent(msg, conversation_history=history)
print(f"  '{msg}' (after recommendation) -> {intent} ({conf:.0%})")
