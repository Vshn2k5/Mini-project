import sys
sys.path.insert(0, ".")
from chatbot_engine import HealthChatbot

print("Testing Entity Memory & Context Ranker...")

bot = HealthChatbot(user_profiles={"U1": {"disease": ["Diabetes"], "dietary_preference": "vegetarian"}}, menu_db=[], orders_db=[])

# Mock Menu
bot.menu_db = [
    {"name": "Tomato Soup No Cream", "tags": "healthy, veg", "calories": 100, "sugar": 2, "carbs": 10, "protein": 3, "sodium": 400, "fat": 1},
    {"name": "Pepperoni Pizza", "tags": "non-veg, high-calorie", "calories": 500, "sugar": 5, "carbs": 50, "protein": 20, "sodium": 1000, "fat": 20}
]

profile = {"disease": ["Diabetes"], "dietary_preference": "vegetarian"}

# Override rank menu to return mockup to ensure stable test
bot._rank_full_menu = lambda p: [
    {"food": bot.menu_db[0], "rule_score": 80, "final_score": 85, "ml_prob": 90, "status": "recommended", "positives": [], "cautions": [], "hard_reject": False},
    {"food": bot.menu_db[1], "rule_score": 20, "final_score": 20, "ml_prob": 10, "status": "not_recommended", "positives": [], "cautions": [], "hard_reject": True}
]

print("\n--- TURN 1 ---")
resp1 = bot.get_response("U1", "recommend healthy lunch", profile=profile, conversation_history=[])
print(f"User: recommend healthy lunch")
print(f"AI Intent: {resp1.get('intent')}")
print(f"AI Response Snippet: {resp1.get('text')[:100]}...")

history = [{"message": "recommend healthy lunch", "response": resp1['text']}]

print("\n--- TURN 2 ---")
resp2 = bot.get_response("U1", "can I order it?", profile=profile, conversation_history=history)
print(f"User: can I order it?")
print(f"AI Intent: {resp2.get('intent')} (Overridden by Entity Resolver)")
print(f"AI Response Snippet: {resp2.get('text')}")

history.append({"message": "can I order it?", "response": resp2['text']})

print("\n--- TURN 3 ---")
resp3 = bot.get_response("U1", "why?", profile=profile, conversation_history=history)
print(f"User: why?")
print(f"AI Intent: {resp3.get('intent')} (Ranked Context)")
history.append({"message": "why?", "response": resp3['text']})

print("\n--- TURN 4 ---")
resp4 = bot.get_response("U1", "Compare protein foods in the canteen", profile=profile, conversation_history=history)
print(f"User: Compare protein foods in the canteen")
print(f"AI Intent: {resp4.get('intent')} (Native Menu Handler)")
history.append({"message": "Compare protein foods in the canteen", "response": resp4['text']})

print("\n--- TURN 5 ---")
resp5 = bot.get_response("U1", "Check my health profile", profile=profile, conversation_history=history)
print(f"User: Check my health profile")
print(f"AI Intent: {resp5.get('intent')} (Native Profile Handler)")
print(f"AI Response Snippet: {resp5.get('text')[:200]}...")
