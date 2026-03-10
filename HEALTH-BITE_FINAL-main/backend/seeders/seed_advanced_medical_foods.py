import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import FoodItem, Inventory

db = SessionLocal()

def food(name, category, calories, sugar, protein, fat, sodium, carbs, price, emoji,
         nuts=False, milk=False, seafood=False, gluten=False, soy=False,
         desc="", stock=50):
    return {
        "name": name,
        "category": category,
        "calories": calories,
        "sugar": sugar,
        "protein": protein,
        "fat": fat,
        "sodium": sodium,
        "carbs": carbs,
        "price": price,
        "image_emoji": emoji,
        "nut_allergy": nuts,
        "milk_allergy": milk,
        "seafood_allergy": seafood,
        "gluten_allergy": gluten,
        "soy_allergy": soy,
        "description": desc,
        "stock": stock
    }

FOODS = [

    # ── Diabetes Safe ────────────────────────────────────────────────────────────
    food("Palak Dal Advanced","Meals",260,3,14,5,310,35,99,"🥬",
         desc="Spinach lentil curry. Sugar 3g (SAFE for diabetes). Sodium 310mg (BP safe).",stock=80),
    food("Oats Upma Advanced","Meals",280,4,10,6,280,40,79,"🥣",gluten=False,
         desc="Oats based slow-carb meal. Sugar 4g (SAFE). Gluten-free oats.",stock=70),
    food("Grilled Chicken Salad Advanced","Healthy",290,2,32,8,320,18,179,"🥗",
         desc="High protein salad. Sugar 2g (diabetes safe). BP safe 320mg sodium.",stock=60),
    food("Millet Khichdi Advanced","Meals",300,5,11,7,300,45,89,"🌾",
         desc="Millet based low glycaemic dish. Sugar 5g (SAFE).",stock=70),

    # ── Diabetes Risk ────────────────────────────────────────────────────────────
    food("Mango Lassi Advanced","Beverages",310,40,6,4,95,52,79,"🥭",milk=True,
         desc="Very high sugar 40g (DIABETES RISK). Contains dairy.",stock=40),
    food("Gulab Jamun Advanced","Desserts",380,48,5,12,120,58,59,"🍮",milk=True,gluten=True,
         desc="Sugar 48g — EXTREME DIABETES RISK. Contains dairy and gluten.",stock=30),

    # ── Hypertension Safe ────────────────────────────────────────────────────────
    food("Steamed Idli Advanced","Meals",220,2,7,3,180,42,69,"🫔",
         desc="Sodium 180mg (HYPERTENSION SAFE). Sugar 2g (diabetes safe).",stock=90),
    food("Watermelon Juice Advanced","Beverages",90,18,1,0,20,22,49,"🍉",
         desc="Sodium only 20mg. L-citrulline supports blood pressure control.",stock=60),
    food("Raw Vegetable Salad","Healthy",160,5,4,5,130,22,69,"🥗",
         desc="Very low sodium 130mg. Zero allergens. Excellent for BP.",stock=70),

    # ── Hypertension Risk ────────────────────────────────────────────────────────
    food("Instant Ramen Advanced","Meals",490,6,12,18,1820,68,99,"🍜",gluten=True,soy=True,
         desc="Sodium 1820mg — EXTREME HYPERTENSION RISK. Contains gluten and soy.",stock=35),
    food("Chicken Burger Advanced","Meals",620,10,28,26,1140,58,199,"🍔",gluten=True,milk=True,
         desc="Sodium 1140mg (BP RISK). Contains gluten (bun) and dairy (cheese).",stock=40),
    food("Pepperoni Pizza Advanced","Meals",620,8,24,30,1200,64,219,"🍕",gluten=True,milk=True,
         desc="Sodium 1200mg (BP RISK). Dairy and gluten allergens present.",stock=30),

    # ── Nuts Allergy ─────────────────────────────────────────────────────────────
    food("Peanut Butter Toast Advanced","Snacks",420,10,14,22,290,42,89,"🥜",
         nuts=True,gluten=True,
         desc="PRIMARY PEANUT ALLERGEN. Contains peanut butter and wheat bread.",stock=30),
    food("Almond Granola Advanced","Breakfast",290,14,7,12,140,42,99,"🌰",
         nuts=True,
         desc="Contains almonds. NUT ALLERGY WARNING. Suitable for non-nut allergic.",stock=40),
    food("Cashew Stir Fry","Meals",340,5,12,16,380,38,149,"🥜",
         nuts=True,soy=True,
         desc="Contains cashews and soy sauce. Nut + soy allergens.",stock=40),
    food("Walnut Oatmeal","Breakfast",310,8,8,14,90,42,99,"🌰",
         nuts=True,
         desc="Contains walnuts. High omega-3. NUT ALLERGY caution.",stock=35),

    # ── Milk / Dairy Allergy ──────────────────────────────────────────────────
    food("Cheese Grilled Toast","Breakfast",310,4,12,14,480,36,89,"🧀",
         milk=True,gluten=True,
         desc="Contains cheddar cheese and wheat. DAIRY + GLUTEN allergens.",stock=45),
    food("Malai Paneer Curry","Meals",420,6,18,24,480,28,159,"🍛",
         milk=True,
         desc="Contains cream and paneer. DAIRY ALLERGY WARNING.",stock=40),
    food("Chocolate Brownie Advanced","Desserts",380,32,5,20,160,44,79,"🍫",
         milk=True,gluten=True,
         desc="Contains butter, milk, wheat. HIGH SUGAR 32g (diabetes risk). Dairy allergen.",stock=35),
    food("Creamy Mushroom Pasta","Meals",560,7,14,24,680,72,169,"🍝",
         milk=True,gluten=True,
         desc="Heavy cream (DAIRY) and pasta (GLUTEN). Sodium 680mg (BP moderate).",stock=35),

    # ── Seafood Allergy ───────────────────────────────────────────────────────
    food("Shrimp Fried Rice","Meals",430,5,22,10,680,52,179,"🦐",
         seafood=True,soy=True,
         desc="PRIMARY SHRIMP ALLERGEN. Contains soy sauce too.",stock=40),
    food("Fish Tacos","Meals",380,6,24,14,540,38,169,"🌮",
         seafood=True,gluten=True,
         desc="Contains fish fillet and corn tortillas. SEAFOOD allergen.",stock=35),
    food("Prawn Masala","Meals",320,5,28,10,560,18,189,"🦐",
         seafood=True,
         desc="Contains prawns. SEAFOOD ALLERGY RISK.",stock=30),
    food("Tuna Salad Bowl","Healthy",270,3,30,8,480,18,159,"🐟",
         seafood=True,
         desc="Contains canned tuna. SEAFOOD ALLERGEN. Good protein.",stock=40),

    # ── Gluten Allergy ────────────────────────────────────────────────────────
    food("Wheat Roti","Meals",120,1,4,2,20,24,29,"🫓",
         gluten=True,
         desc="PRIMARY GLUTEN (wheat). Extremely low sodium. Very suitable otherwise.",stock=90),
    food("Masala Pasta","Meals",480,8,14,16,620,66,139,"🍝",
         gluten=True,milk=True,
         desc="Contains wheat pasta (GLUTEN) and cream sauce (DAIRY).",stock=45),
    food("Whole Wheat Toast","Breakfast",200,3,8,4,280,36,49,"🍞",
         gluten=True,
         desc="Pure wheat bread. GLUTEN ALLERGY caution.",stock=60),
    food("Barley Vegetable Soup","Meals",210,5,8,4,260,36,79,"🍲",
         gluten=True,
         desc="Contains barley — gluten allergen. Good for BP otherwise.",stock=50),

    # ── Soy Allergy ───────────────────────────────────────────────────────────
    food("Tofu Stir Fry Advanced","Meals",310,5,20,12,820,24,149,"🥢",
         soy=True,
         desc="PRIMARY SOY ALLERGEN. Tofu and soy sauce. Sodium 820mg (BP risk too).",stock=30),
    food("Edamame Salad","Healthy",220,4,14,8,340,20,109,"🥗",
         soy=True,
         desc="Contains edamame (soy). HIGH soy content.",stock=40),
    food("Soy Milk Smoothie","Beverages",180,10,8,4,160,26,89,"🥛",
         soy=True,
         desc="Contains soy milk. SOY ALLERGY WARNING.",stock=35),
    food("Tempeh Rice Bowl","Meals",380,4,22,14,580,42,159,"🍚",
         soy=True,
         desc="Contains tempeh (fermented soy). Soy allergen.",stock=35),

]

added = 0
skipped = 0

for f in FOODS:
    stock = f.pop("stock")
    existing = db.query(FoodItem).filter_by(name=f["name"]).first()
    if existing:
        print(f"  SKIP (exists): {f['name']}")
        skipped += 1
        f["stock"] = stock
        continue

    item = FoodItem(**f)
    db.add(item)
    db.flush()
    db.add(Inventory(food_id=item.id, current_stock=stock))
    db.commit()
    print(f"  Added: {f['name']}")
    added += 1

db.close()
print(f"\nDone. Added: {added}  |  Skipped (duplicates): {skipped}")
