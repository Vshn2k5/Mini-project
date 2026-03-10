import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import FoodItem, Inventory
from datetime import datetime

db = SessionLocal()

FOODS = [
  # ── DIABETES SAFE ─────────────────────────────────────────────────
  {"name":"Grilled Chicken Bowl","category":"Meals","calories":320,"sugar":2,
   "protein":38,"fat":8,"sodium":380,"carbs":22,"price":199,"image_emoji":"🍗",
   "description":"Grilled chicken breast with steamed brown rice and sautéed greens. Low sugar, high protein — ideal for diabetics.","stock":60},

  {"name":"Palak Dal","category":"Meals","calories":260,"sugar":3,
   "protein":14,"fat":5,"sodium":320,"carbs":35,"price":99,"image_emoji":"🥬",
   "description":"Slow-cooked yellow lentils with fresh spinach, turmeric and cumin. High fiber, low glycaemic load — excellent for blood sugar control.","stock":80},

  {"name":"Mixed Vegetable Oats Upma","category":"Meals","calories":280,"sugar":4,
   "protein":10,"fat":6,"sodium":290,"carbs":40,"price":79,"image_emoji":"🥣",
   "description":"Steel-cut oats cooked with seasonal vegetables and mild spices. Slow-digesting carbs — minimal blood sugar spike.","stock":70},

  # ── DIABETES MODERATE ──────────────────────────────────────────────
  {"name":"Paneer Butter Masala with Roti","category":"Meals","calories":480,"sugar":12,
   "protein":18,"fat":22,"sodium":520,"carbs":44,"price":159,"image_emoji":"🧀",
   "description":"Cottage cheese in mildly spiced tomato-butter gravy with 2 rotis. Moderate sugar from tomato base — consume in half portions.","stock":55},

  {"name":"Fruit and Nut Yoghurt Bowl","category":"Snacks","calories":220,"sugar":16,
   "protein":8,"fat":5,"sodium":80,"carbs":28,"price":89,"image_emoji":"🍓",
   "description":"Plain yoghurt with seasonal fruits and mixed nuts. Natural sugars — moderate for diabetics.","stock":50},

  {"name":"Corn and Chickpea Salad","category":"Healthy","calories":310,"sugar":14,
   "protein":12,"fat":7,"sodium":240,"carbs":46,"price":129,"image_emoji":"🌽",
   "description":"Boiled corn and chickpeas with lime dressing and herbs. Natural sugars from corn — high fibre offsets glycaemic impact.","stock":45},

  # ── DIABETES RISKY ─────────────────────────────────────────────────
  {"name":"Mango Lassi Large","category":"Beverages","calories":310,"sugar":42,
   "protein":6,"fat":4,"sodium":95,"carbs":52,"price":79,"image_emoji":"🥭",
   "description":"Full-cream yoghurt blended with Alphonso mango pulp and sugar. Very high sugar — strongly avoid if diabetic.","stock":40},

  {"name":"Gulab Jamun 2 pcs","category":"Desserts","calories":380,"sugar":48,
   "protein":5,"fat":12,"sodium":120,"carbs":58,"price":59,"image_emoji":"🍮",
   "description":"Deep-fried milk dumplings soaked in sugar syrup. Extremely high sugar — not suitable for diabetics.","stock":30},

  {"name":"Nutella Banana Crepe","category":"Desserts","calories":520,"sugar":38,
   "protein":8,"fat":18,"sodium":140,"carbs":72,"price":149,"image_emoji":"🫓",
   "description":"Thin wheat crepe filled with Nutella and fresh banana. High sugar from both hazelnut spread and banana — avoid for diabetes.","stock":25},

  # ── HYPERTENSION SAFE ─────────────────────────────────────────────
  {"name":"Steamed Idli with Coconut Chutney","category":"Meals","calories":220,"sugar":2,
   "protein":7,"fat":3,"sodium":180,"carbs":42,"price":69,"image_emoji":"🫔",
   "description":"Freshly steamed rice-lentil idli with homemade coconut chutney. Naturally low sodium — one of the safest options for hypertension.","stock":90},

  {"name":"Roasted Chickpea Bowl","category":"Snacks","calories":190,"sugar":3,
   "protein":9,"fat":4,"sodium":160,"carbs":28,"price":59,"image_emoji":"🫘",
   "description":"Oven-roasted chickpeas with turmeric, cumin and lime zest. No added salt. High potassium supports healthy blood pressure.","stock":70},

  {"name":"Fresh Watermelon Juice","category":"Beverages","calories":90,"sugar":18,
   "protein":1,"fat":0,"sodium":20,"carbs":22,"price":49,"image_emoji":"🍉",
   "description":"Cold-pressed watermelon juice, no added sugar or salt. L-citrulline in watermelon supports blood vessel relaxation.","stock":60},

  # ── HYPERTENSION MODERATE ─────────────────────────────────────────
  {"name":"Egg Fried Brown Rice","category":"Meals","calories":390,"sugar":3,
   "protein":14,"fat":10,"sodium":610,"carbs":54,"price":129,"image_emoji":"🍳",
   "description":"Wok-tossed brown rice with whole eggs and mixed vegetables. Moderate sodium from soy sauce — half portion recommended.","stock":55},

  {"name":"Grilled Paneer Tikka","category":"Snacks","calories":280,"sugar":5,
   "protein":22,"fat":16,"sodium":490,"carbs":8,"price":119,"image_emoji":"🧆",
   "description":"Marinated paneer cubes grilled with peppers and onions. Moderate sodium from marinade — occasional use acceptable.","stock":40},

  {"name":"Tomato Soup No Cream","category":"Meals","calories":140,"sugar":8,
   "protein":4,"fat":3,"sodium":720,"carbs":22,"price":79,"image_emoji":"🍲",
   "description":"Blended tomato soup with basil and black pepper. On the higher end for hypertension — consume occasionally.","stock":50},

  # ── HYPERTENSION RISKY ────────────────────────────────────────────
  {"name":"Instant Masala Ramen","category":"Meals","calories":490,"sugar":6,
   "protein":12,"fat":18,"sodium":1820,"carbs":68,"price":99,"image_emoji":"🍜",
   "description":"Masala-flavoured instant noodles with rich soup base. One bowl exceeds 75% of daily sodium limit — avoid with hypertension.","stock":35},

  {"name":"Gourmet Chicken Burger","category":"Meals","calories":620,"sugar":10,
   "protein":28,"fat":26,"sodium":1140,"carbs":58,"price":199,"image_emoji":"🍔",
   "description":"Crispy fried chicken patty with cheese, pickles, and sriracha mayo. Very high sodium from cheese and pickles — avoid with hypertension.","stock":40},

  {"name":"Cheese Loaded Nachos","category":"Snacks","calories":540,"sugar":5,
   "protein":12,"fat":28,"sodium":980,"carbs":60,"price":169,"image_emoji":"🧀",
   "description":"Corn tortilla chips with cheddar cheese sauce and jalapeños. High sodium from cheese sauce — not suitable for hypertension management.","stock":30},

  # ── ALLERGY SAFE ──────────────────────────────────────────────────
  {"name":"Plain Rice with Sambar","category":"Meals","calories":290,"sugar":4,
   "protein":9,"fat":2,"sodium":310,"carbs":58,"price":69,"image_emoji":"🍚",
   "description":"Plain white rice with South Indian lentil sambar. Free from soy, dairy, and peanuts — one of the cleanest canteen options.","stock":100},

  {"name":"Grilled Fish with Steamed Vegetables","category":"Meals","calories":310,"sugar":2,
   "protein":32,"fat":9,"sodium":360,"carbs":14,"price":179,"image_emoji":"🐟",
   "description":"Grilled basa fillet with steamed broccoli and carrots. Completely free from soy, dairy, and peanuts.","stock":45},

  {"name":"Fresh Fruit Platter","category":"Snacks","calories":140,"sugar":26,
   "protein":2,"fat":1,"sodium":10,"carbs":34,"price":89,"image_emoji":"🍎",
   "description":"Seasonal fruits — papaya, watermelon, guava, banana. Zero allergen risk. High in vitamins and antioxidants.","stock":60},

  # ── ALLERGY MODERATE ─────────────────────────────────────────────
  {"name":"Veg Biryani","category":"Meals","calories":420,"sugar":5,
   "protein":9,"fat":12,"sodium":480,"carbs":66,"price":139,"image_emoji":"🍛",
   "description":"Fragrant basmati rice with vegetables and whole spices. May contain traces of soy sauce. Processed near milk and nut products.","stock":65},

  {"name":"Chocolate Brownie","category":"Desserts","calories":380,"sugar":32,
   "protein":5,"fat":20,"sodium":160,"carbs":44,"price":79,"image_emoji":"🍫",
   "description":"Dense chocolate brownie. Contains dairy. May contain soy lecithin and traces of peanuts from shared equipment.","stock":35},

  {"name":"Hummus and Pita Bread","category":"Snacks","calories":320,"sugar":3,
   "protein":10,"fat":14,"sodium":410,"carbs":38,"price":109,"image_emoji":"🫓",
   "description":"Chickpea hummus with tahini and olive oil, served with pita. No dairy or peanut. Soy-free. Sesame allergy caution.","stock":40},

  # ── ALLERGY RISKY ────────────────────────────────────────────────
  {"name":"Peanut Butter Toast","category":"Snacks","calories":420,"sugar":10,
   "protein":14,"fat":22,"sodium":290,"carbs":42,"price":89,"image_emoji":"🥜",
   "description":"Thick-cut white bread with natural peanut butter and honey. PRIMARY peanut allergen — severe risk for peanut allergy. Processed near dairy.","stock":30},

  {"name":"Creamy Mushroom Pasta","category":"Meals","calories":560,"sugar":7,
   "protein":14,"fat":24,"sodium":680,"carbs":72,"price":169,"image_emoji":"🍝",
   "description":"Penne in heavy cream-mushroom sauce with Parmesan. Contains dairy (cream, Parmesan). May contain soy emulsifiers. Not suitable for dairy or soy allergy.","stock":35},

  {"name":"Tofu Stir Fry with Edamame","category":"Meals","calories":310,"sugar":5,
   "protein":20,"fat":12,"sodium":820,"carbs":24,"price":149,"image_emoji":"🥢",
   "description":"Wok-tossed tofu and edamame with soy sauce and sesame oil. PRIMARY soy allergen — tofu, edamame, and soy sauce are all soy-derived. Not suitable for soy allergy.","stock":30},
]

added = 0
skipped = 0

for f in FOODS:
    stock = f.pop("stock")
    existing = db.query(FoodItem).filter_by(name=f["name"]).first()
    if existing:
        print(f"  SKIP (exists): {f['name']}")
        skipped += 1
        f["stock"] = stock  # restore for re-runs
        continue

    food = FoodItem(**f)
    db.add(food)
    db.flush()
    db.add(Inventory(food_id=food.id, current_stock=stock))
    db.commit()
    print(f"  ✅ Added: {f['name']}")
    added += 1

db.close()
print(f"\nDone. Added: {added}  |  Skipped (duplicates): {skipped}")