import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import FoodItem, Inventory

db = SessionLocal()

def food(name, category, calories, sugar, protein, fat, sodium, carbs, price, emoji, desc, stock):
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
        "description": desc,
        "stock": stock
    }

FOODS = [

    # =========================
    # DIABETES SAFE  (sugar ≤ 8g, sodium ≤ 400mg)
    # =========================
    food("Palak Dal","Meals",260,3,14,5,310,35,99,"🥬","Low glycaemic spinach lentil curry.",80),
    food("Oats Vegetable Upma","Meals",280,4,10,6,280,40,79,"🥣","Oats based breakfast with slow carbs.",70),
    food("Grilled Chicken Salad","Healthy",290,2,32,8,320,18,179,"🥗","High protein salad safe for diabetics.",60),
    food("Millet Khichdi","Meals",300,5,11,7,300,45,89,"🌾","Millet based meal with slow carbs.",70),
    food("Vegetable Idli 2","Breakfast",220,2,7,3,180,42,69,"🫔","Steamed fermented rice cakes.",90),
    food("Brown Rice Veg Bowl","Meals",310,6,9,4,250,50,109,"🍚","Brown rice bowl with vegetables.",80),
    food("Roasted Chickpea Snack","Snacks",200,3,9,4,150,30,59,"🫘","High fiber chickpea snack.",70),
    food("Lentil Vegetable Soup","Meals",180,4,10,3,240,25,69,"🍲","Protein rich soup safe for diabetics.",60),

    # =========================
    # DIABETES MODERATE  (sugar 8–20g)
    # =========================
    food("Fruit Yogurt Bowl","Snacks",220,14,8,5,80,28,89,"🍓","Yogurt bowl with seasonal fruits.",50),
    food("Corn Chickpea Salad","Healthy",310,12,12,7,240,46,129,"🌽","High fiber salad, moderate sugar.",45),
    food("Paneer Masala Roti","Meals",470,11,18,22,520,44,159,"🧀","Paneer curry with roti.",55),
    food("Sweet Corn Soup","Meals",190,10,6,4,360,34,79,"🌽","Corn based soup moderate sugar.",60),
    food("Granola Breakfast Bowl","Breakfast",320,16,9,10,220,48,119,"🥣","Granola oats breakfast.",50),
    food("Chicken Wrap Lite","Meals",420,13,26,14,480,38,149,"🌯","Whole wheat chicken wrap.",40),
    food("Protein Smoothie","Beverages",260,15,20,4,180,26,109,"🥤","Protein drink moderate sugar.",45),
    food("Vegetable Biryani","Meals",420,14,9,12,480,66,139,"🍛","Rice meal moderate sugar.",65),

    # =========================
    # DIABETES RISK  (sugar >20g)
    # =========================
    food("Mango Lassi","Beverages",310,40,6,4,95,52,79,"🥭","Very high sugar mango drink. Avoid if diabetic.",40),
    food("Gulab Jamun","Desserts",380,48,5,12,120,58,59,"🍮","Sugar syrup dessert. Extremely high sugar.",30),
    food("Nutella Banana Crepe","Desserts",520,38,8,18,140,72,149,"🫓","Chocolate crepe. High sugar dessert.",25),
    food("Chocolate Milkshake","Beverages",420,36,9,16,210,54,119,"🥤","High sugar milkshake.",35),
    food("Ice Cream Sundae","Desserts",460,42,7,22,180,60,129,"🍨","Sugary ice cream dessert.",30),
    food("Caramel Pancakes","Breakfast",500,35,10,18,340,70,139,"🥞","Sweet pancake breakfast.",25),
    food("Sweet Jalebi","Desserts",420,46,4,14,160,64,49,"🍯","Deep fried sugar dessert.",30),
    food("Chocolate Donut","Desserts",340,32,5,15,220,50,59,"🍩","Sugary bakery donut.",35),

    # =========================
    # HYPERTENSION SAFE  (sodium ≤ 400mg)
    # =========================
    food("Steamed Idli Plate","Meals",220,2,7,3,180,42,69,"🫔","Low sodium fermented rice cakes.",90),
    food("Watermelon Juice","Beverages",90,18,1,0,20,22,49,"🍉","Fresh fruit juice, BP friendly.",60),
    food("Vegetable Soup Lite","Meals",120,4,4,2,140,20,59,"🍲","Low sodium vegetable soup.",70),
    food("Grilled Fish Fillet","Meals",310,2,32,9,360,14,179,"🐟","Lean protein fish, BP safe.",45),
    food("Boiled Egg Snack","Snacks",140,1,12,10,160,1,49,"🥚","Simple egg snack.",60),
    food("Fresh Fruit Plate","Snacks",160,24,2,1,10,36,79,"🍎","Seasonal fruits, zero sodium.",70),
    food("Vegetable Salad Mix","Healthy",180,5,4,6,150,22,69,"🥗","Low sodium salad.",80),
    food("Roasted Chickpeas","Snacks",190,3,9,4,160,28,59,"🫘","Healthy potassium-rich snack.",70),

    # =========================
    # HYPERTENSION MODERATE  (sodium 400–800mg)
    # =========================
    food("Egg Fried Rice","Meals",390,3,14,10,610,54,129,"🍳","Brown rice fried with eggs.",55),
    food("Paneer Tikka","Snacks",280,5,22,16,490,8,119,"🧆","Grilled paneer cubes.",40),
    food("Tomato Soup","Meals",140,8,4,3,720,22,79,"🍅","Moderate sodium tomato soup.",50),
    food("Chicken Wrap","Meals",420,9,26,14,580,38,149,"🌯","Chicken wrap moderate sodium.",45),
    food("Veg Noodles","Meals",380,6,10,8,650,55,119,"🍜","Stir fried noodles.",50),
    food("Street Chowmein","Meals",410,5,12,11,690,58,109,"🍜","Street style noodles.",55),
    food("Veg Burger","Meals",450,9,14,17,700,48,129,"🍔","Vegetable burger.",45),
    food("Paneer Roll","Meals",440,8,16,18,650,46,139,"🌯","Paneer wrap snack.",40),

    # =========================
    # HYPERTENSION RISK  (sodium >800mg)
    # =========================
    food("Instant Masala Ramen","Meals",490,6,12,18,1820,68,99,"🍜","Extremely high sodium. Avoid with hypertension.",35),
    food("Chicken Burger Deluxe","Meals",620,10,28,26,1140,58,199,"🍔","Very high sodium fast food.",40),
    food("Cheese Loaded Nachos","Snacks",540,5,12,28,980,60,169,"🧀","High sodium cheese nachos.",30),
    food("Pepperoni Pizza","Meals",620,8,24,30,1200,64,219,"🍕","Processed meat pizza.",30),
    food("Hot Dog","Meals",450,7,18,22,1050,40,119,"🌭","Processed sausage sandwich.",40),
    food("Salted Fries","Snacks",420,1,5,22,950,50,89,"🍟","Salt heavy fries.",45),
    food("Cheese Pasta","Meals",560,7,14,24,920,72,169,"🍝","Cream cheese pasta.",35),
    food("Loaded Sandwich","Meals",480,6,20,19,980,52,139,"🥪","High sodium sandwich.",40),

    # =========================
    # NUTS ALLERGY (safe/moderate/risk)
    # =========================
    food("Peanut Butter Toast","Snacks",420,10,14,22,290,42,89,"🥜","PRIMARY PEANUT ALLERGEN. Contains peanut butter.",30),
    food("Almond Granola Bar","Snacks",280,12,6,10,140,38,79,"🌰","Contains almonds. Nut allergy caution.",35),
    food("Cashew Vegetable Stir Fry","Meals",340,5,12,16,380,38,149,"🥜","Contains cashews. Nut allergen.",40),
    food("Mixed Nut Energy Balls","Snacks",250,8,8,16,80,26,99,"🌰","Contains mixed nuts. Peanut free.",40),

    # =========================
    # MILK / DAIRY ALLERGY
    # =========================
    food("Cheese Grilled Toast","Breakfast",310,4,12,14,480,36,89,"🧀","Contains cheddar cheese. Dairy allergen.",45),
    food("Malai Paneer Curry","Meals",420,6,18,24,480,28,159,"🍛","Contains cream and paneer. High dairy.",40),
    food("Chocolate Brownie","Desserts",380,32,5,20,160,44,79,"🍫","Contains dairy butter and milk.",35),
    food("Creamy Mushroom Pasta","Meals",560,7,14,24,680,72,169,"🍝","Contains heavy cream and parmesan.",35),

    # =========================
    # SEAFOOD ALLERGY
    # =========================
    food("Shrimp Fried Rice","Meals",430,5,22,10,680,52,179,"🦐","PRIMARY SHRIMP ALLERGEN. Contains shrimp.",40),
    food("Fish Tacos","Meals",380,6,24,14,540,38,169,"🌮","Contains fish fillet. Seafood allergy.",35),
    food("Prawn Masala","Meals",320,5,28,10,560,18,189,"🦐","Contains prawns. Seafood allergen.",30),
    food("Tuna Salad Bowl","Healthy",270,3,30,8,480,18,159,"🐟","Contains canned tuna. Seafood.",40),

    # =========================
    # GLUTEN ALLERGY
    # =========================
    food("Wheat Roti","Meals",120,1,4,2,20,24,29,"🫓","Contains whole wheat. Primary gluten allergen.",90),
    food("Masala Pasta","Meals",480,8,14,16,620,66,139,"🍝","Contains wheat pasta. Gluten allergen.",45),
    food("Whole Wheat Bread Toast","Breakfast",200,3,8,4,280,36,49,"🍞","Contains wheat. Gluten allergy caution.",60),
    food("Barley Vegetable Soup","Meals",210,5,8,4,260,36,79,"🍲","Contains barley. Gluten allergen.",50),

    # =========================
    # SOY ALLERGY
    # =========================
    food("Tofu Stir Fry","Meals",310,5,20,12,820,24,149,"🥢","PRIMARY SOY ALLERGEN. Tofu and soy sauce.",30),
    food("Edamame Salad","Healthy",220,4,14,8,340,20,109,"🥗","Contains edamame (soy). Soy allergy risk.",40),
    food("Soy Milk Smoothie","Beverages",180,10,8,4,160,26,89,"🥛","Contains soy milk. Soy allergen.",35),
    food("Tempeh Rice Bowl","Meals",380,4,22,14,580,42,159,"🍚","Contains tempeh (fermented soy). Soy allergen.",35),

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

    food_item = FoodItem(**f)
    db.add(food_item)
    db.flush()
    db.add(Inventory(food_id=food_item.id, current_stock=stock))
    db.commit()
    print(f"  Added: {f['name']}")
    added += 1

db.close()
print(f"\nDone. Added: {added}  |  Skipped (duplicates): {skipped}")
