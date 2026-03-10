from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
from models import User, HealthProfile, FoodItem, Inventory, Order, OrderItem

from schemas import OrderCreate, OrderResponse
from chatbot_engine import HealthChatbot
import json

router = APIRouter(
    prefix="/api/menu",
    tags=["menu"]
)

@router.get("/intelligent")
async def get_intelligent_menu(
    strict: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Intelligent Menu API.
    If strict=True (Dashboard/Recommendation view): 
       Only returns food items that strictly match the user's dietary preference.
    If strict=False (Full Menu view):
       Returns all foods, but uses the AI scoring engine to apply restricted tags to non-compliant items.
    """
    db_foods = db.query(FoodItem).join(Inventory).filter(
        FoodItem.canteen_id == current_user.canteen_id,
        FoodItem.is_available == True,
        Inventory.current_stock > 0
    ).all()
    
    food_items = []
    for f in db_foods:
        food_items.append({
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "price": f.price,
            "image": f.image_emoji,
            "calories": f.calories,
            "sugar": f.sugar,
            "protein": f.protein,
            "carbs": f.carbs,
            "fat": f.fat,
            "sodium": f.sodium,
            "dietary_type": f.dietary_type,
            "description": f.description or "",
            "stock": f.inventory.current_stock if f.inventory else 0
        })

    # Get user profile
    profile_db = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    
    diseases = []
    allergies = []
    profile = {
        "age": 25,
        "disease": [],
        "allergies": [],
        "dietary_preference": "Non-Veg",
        "target_calories": 2000 
    }
    
    if profile_db:
        try:
            diseases = json.loads(profile_db.disease) if profile_db.disease else []
            allergies = json.loads(profile_db.allergies) if profile_db.allergies and profile_db.allergies != "None" else []
        except:
            diseases = []
            allergies = []
        
        profile = {
            "age": profile_db.age,
            "disease": diseases,
            "allergies": allergies,
            "dietary_preference": profile_db.dietary_preference or "Non-Veg",
            "target_calories": 2000 
        }

    # Initialize Chatbot Engine for analysis
    engine = HealthChatbot({}, food_items, [])
    
    intelligent_menu = []
    diet_pref = profile.get("dietary_preference", "Non-Veg").lower()
    
    # Generate Hybrid ML Probabilities for all foods based on patient profile!
    norm_profile = engine._normalize_profile(profile)
    ml_probs = engine._ml_probabilities(norm_profile)
    max_ml_prob = max(ml_probs.values()) if ml_probs else 1.0
    
    for item in food_items:
        # --- Dietary Filter ---
        item_diet = item.get("dietary_type", "Veg").lower()
        is_plant_based = item_diet in {"plant-based", "plant based", "plant_based", "vegan"}
        is_veg = item_diet in {"veg", "vegetarian"} or is_plant_based
        is_non_veg = item_diet in {"non-veg", "non veg", "nonveg", "non_veg"}
        
        # In strict mode, we skip anything that doesn't match the diet.
        if strict:
            # Vegan users -> only Plant-Based
            if diet_pref in {"vegan", "plant-based", "plant based", "plant_based"} and not is_plant_based:
                continue
            # Vegetarian users -> Veg + Plant-Based
            if diet_pref in {"veg", "vegetarian"} and not is_veg:
                continue
            
        # Use AI scoring engine to get Match Score and Insights
        eval_result = engine._evaluate_food(item, norm_profile)
        base_score = float(eval_result.get("score", 0))
        
        # HYBRID INJECTION: Blend rule-based safety with ML preference matching!
        if base_score >= 45 and max_ml_prob > 0:
            food_name_key = item.get("name", "").lower()
            if food_name_key in ml_probs:
                raw_prob = ml_probs[food_name_key]
                # Normalize the ML softmax probability relative to the absolute best ML match
                ml_scaled_score = (raw_prob / max_ml_prob) * 100
                # True Hybrid Match: 70% Rules (Medical Safety) + 30% ML (Personalization)
                score = round((base_score * 0.70) + (ml_scaled_score * 0.30))
            else:
                score = round(base_score)
        else:
            score = round(base_score)
            
        penalties = eval_result.get("cautions", [])
        
        # In strict mode, we also skip items that are NOT highly recommended (Safe)
        if strict and score < 82:
            continue
            
        item_copy = item.copy()
        item_copy['match_score'] = score
        
        if score >= 82:
            item_copy['risk_level'] = 0
            item_copy['insight'] = "Perfect match for your health profile."
        elif score >= 50:
            item_copy['risk_level'] = 1
            item_copy['insight'] = f"Caution: {', '.join(penalties)}" if penalties else "Moderate nutrition match."
        else:
            item_copy['risk_level'] = 2
            item_copy['insight'] = f"Restricted: {', '.join(penalties)}" if penalties else "High risk for your profile."
        
        # --- NUTRITIONAL SMART TAGS (Threshold Based) ---
        if item.get('protein', 0) > 15:
            item_copy['tag'] = "High Protein"
        elif item.get('carbs', 0) < 20: 
            item_copy['tag'] = "Low Carb"
        elif item.get('sugar', 0) == 0: 
            item_copy['tag'] = "Sugar Free"
        elif item.get('sugar', 0) < 5: 
            item_copy['tag'] = "Low Sugar"
        else: 
            item_copy['tag'] = "Balanced"
        
        intelligent_menu.append(item_copy)
        
    return intelligent_menu


@router.post("/order", response_model=OrderResponse)
async def place_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new order, saves items, and decrements inventory stock.
    """
    # 1. Create Order record
    # For legacy compatibility, we also store items as a JSON string
    items_json = json.dumps([{"food_id": i.food_id, "quantity": i.quantity} for i in payload.items])
    
    new_order = Order(
        user_id=current_user.id,
        canteen_id=current_user.canteen_id,
        items=items_json,
        total_price=payload.total_price,
        total_calories=payload.total_calories,
        total_sugar=payload.total_sugar,
        total_sodium=payload.total_sodium,
        status="completed",
        payment_method=payload.payment_method,
        created_at=datetime.now().isoformat()
    )
    db.add(new_order)
    db.flush() # Get order ID

    # 2. Add OrderItems and update Inventory
    for item in payload.items:
        food = db.query(FoodItem).filter(FoodItem.id == item.food_id).first()
        if not food:
            continue
            
        # Create OrderItem entry
        order_item = OrderItem(
            order_id=new_order.id,
            food_id=food.id,
            food_name=food.name,
            qty=item.quantity,
            unit_price=food.price,
            subtotal=food.price * item.quantity,
            health_flag=False # Can be set based on health score if needed
        )
        db.add(order_item)
        
        # Decrement Inventory
        inventory = db.query(Inventory).filter(Inventory.food_id == food.id).first()
        if inventory:
            inventory.current_stock = max(0, inventory.current_stock - item.quantity)

    db.commit()
    db.refresh(new_order)
    return new_order


@router.get("/history", response_model=list[OrderResponse])
async def get_order_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the order history for the current logged-in user."""
    orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.id.desc()).all()
    return orders
