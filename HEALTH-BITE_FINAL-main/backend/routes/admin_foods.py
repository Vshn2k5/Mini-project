"""Admin Food CRUD — /api/admin/foods"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import FoodItem, Inventory, OrderItem
from routes.admin_deps import get_current_admin
from routes.audit_helper import log_action
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import re

router = APIRouter(prefix="/api/admin/foods", tags=["admin-foods"])


class FoodCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = ""
    price: float = 0.0
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    sugar: float = 0
    sodium: float = 0
    dietary_type: str = "Veg"
    ingredients: Optional[str] = ""
    image_url: Optional[str] = ""
    image_emoji: Optional[str] = ""
    stock: int = 100
    reorder_level: int = 20
    available: bool = True


class FoodUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    dietary_type: Optional[str] = None
    ingredients: Optional[str] = None
    image_url: Optional[str] = None
    image_emoji: Optional[str] = None
    stock: Optional[int] = None
    is_available: Optional[bool] = None
    available: Optional[bool] = None


def _normalize_dietary_type(value: Optional[str]) -> str:
    raw = (value or "Veg").strip().lower()
    if raw in {"plant-based", "plant based", "plant_based", "vegan"}:
        return "Plant-Based"
    if raw in {"non-veg", "non veg", "nonveg", "non_veg"}:
        return "Non-Veg"
    return "Veg"


def _infer_allergen_flags(ingredients: str) -> dict:
    text = f" {ingredients.lower()} " if ingredients else " "

    def hit(patterns):
        return any(re.search(rf"\b{p}\b", text) for p in patterns)

    return {
        "nut_allergy": hit(["nut", "nuts", "peanut", "peanuts", "almond", "almonds", "cashew", "cashews", "walnut", "walnuts", "pistachio", "hazelnut"]),
        "milk_allergy": hit(["milk", "dairy", "butter", "cheese", "paneer", "cream", "ghee", "yogurt", "curd"]),
        "seafood_allergy": hit(["fish", "prawn", "prawns", "shrimp", "crab", "seafood", "tuna", "salmon"]),
        "gluten_allergy": hit(["wheat", "maida", "atta", "bread", "pasta", "noodle", "noodles", "barley", "rye"]),
        "soy_allergy": hit(["soy", "soya", "tofu", "soybean", "soybeans", "soy sauce"]),
    }


def _food_dict(f: FoodItem) -> dict:
    raw_image = f.image_emoji or ""
    image_url = raw_image if isinstance(raw_image, str) and raw_image.lower().startswith(("http://", "https://")) else ""
    image_emoji = "" if image_url else raw_image
    return {
        "id": f.id,
        "name": f.name,
        "category": f.category,
        "description": f.description,
        "price": f.price,
        "calories": f.calories,
        "protein": f.protein,
        "carbs": f.carbs,
        "fat": f.fat,
        "sugar": f.sugar,
        "sodium": f.sodium,
        "dietary_type": f.dietary_type,
        "ingredients": f.ingredients or "",
        "image_emoji": image_emoji,
        "image_url": image_url,
        "is_available": f.is_available,
        "available": f.is_available, # for backward compatibility
        "stock": f.inventory.current_stock if f.inventory else 0,
        "reorder_level": f.inventory.reorder_level if f.inventory else 0,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("")
@router.get("/")
def list_foods(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(FoodItem).filter(FoodItem.canteen_id == admin.canteen_id)
    if search:
        q = q.filter(FoodItem.name.ilike(f"%{search}%"))
    if category:
        q = q.filter(FoodItem.category == category)
    if available_only:
        q = q.filter(FoodItem.is_available == True)

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "items": [_food_dict(f) for f in items],
    }


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_food(body: FoodCreate, request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # image_emoji field may come separately; fall back to URL for backwards compatibility
    image_emoji_in = (body.image_emoji if hasattr(body, "image_emoji") else "") or ""
    image_emoji_in = image_emoji_in.strip()
    image_url_in = (body.image_url or "").strip()
    # Prefer URL when provided; otherwise use emoji.
    emoji_val = image_url_in or image_emoji_in or "🍽️"
    normalized_diet = _normalize_dietary_type(body.dietary_type)
    ingredients_text = (body.ingredients or "").strip()
    allergen_flags = _infer_allergen_flags(ingredients_text)

    food = FoodItem(
        name=body.name, category=body.category, description=body.description,
        price=body.price, calories=body.calories, protein=body.protein,
        carbs=body.carbs, fat=body.fat, sugar=body.sugar, sodium=body.sodium,
        dietary_type=normalized_diet, ingredients=ingredients_text, image_emoji=emoji_val,
        nut_allergy=allergen_flags["nut_allergy"],
        milk_allergy=allergen_flags["milk_allergy"],
        seafood_allergy=allergen_flags["seafood_allergy"],
        gluten_allergy=allergen_flags["gluten_allergy"],
        soy_allergy=allergen_flags["soy_allergy"],
        is_available=body.available,
        canteen_id=admin.canteen_id,
    )
    db.add(food)
    db.flush()  # get food.id

    inv = Inventory(food_id=food.id, current_stock=body.stock, reorder_level=body.reorder_level)
    db.add(inv)
    db.commit()
    db.refresh(food)

    log_action(db, admin.id, "CREATE", "food_items", food.id,
               f"Created food item: {food.name}", {"name": food.name, "category": food.category}, request=request)

    return _food_dict(food)


@router.put("/{food_id}")
def update_food(food_id: int, body: FoodUpdate, request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    food = db.query(FoodItem).filter(FoodItem.id == food_id, FoodItem.canteen_id == admin.canteen_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    before = _food_dict(food)
    data = body.dict(exclude_none=True)
    
    # prefer explicit emoji field, otherwise allow old image_url behaviour
    image_emoji_in = data.pop("image_emoji", None) if "image_emoji" in data else None
    image_url_in = data.pop("image_url", None) if "image_url" in data else None
    image_emoji_in = image_emoji_in.strip() if isinstance(image_emoji_in, str) else image_emoji_in
    image_url_in = image_url_in.strip() if isinstance(image_url_in, str) else image_url_in
    # Prefer URL when provided; otherwise use emoji.
    if image_url_in:
        food.image_emoji = image_url_in
    elif image_emoji_in:
        food.image_emoji = image_emoji_in
    elif image_emoji_in is not None or image_url_in is not None:
        food.image_emoji = "🍽️"
    if "available" in data:
        food.is_available = data.pop("available")
    if "dietary_type" in data:
        food.dietary_type = _normalize_dietary_type(data.pop("dietary_type"))
    if "ingredients" in data:
        ingredients_text = (data.pop("ingredients") or "").strip()
        food.ingredients = ingredients_text
        allergen_flags = _infer_allergen_flags(ingredients_text)
        food.nut_allergy = allergen_flags["nut_allergy"]
        food.milk_allergy = allergen_flags["milk_allergy"]
        food.seafood_allergy = allergen_flags["seafood_allergy"]
        food.gluten_allergy = allergen_flags["gluten_allergy"]
        food.soy_allergy = allergen_flags["soy_allergy"]
    if "stock" in data:
        stock_val = data.pop("stock")
        if food.inventory:
            food.inventory.current_stock = stock_val
            food.inventory.updated_at = datetime.now()
            
    for field, val in data.items():
        setattr(food, field, val)
        
    food.updated_at = datetime.now()
    db.commit()
    db.refresh(food)

    log_action(db, admin.id, "UPDATE", "food_items", food.id,
               f"Updated food item: {food.name}", before=before, after=_food_dict(food), request=request)

    return _food_dict(food)


@router.delete("/{food_id}", status_code=204)
def delete_food(food_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    food = db.query(FoodItem).filter(FoodItem.id == food_id, FoodItem.canteen_id == admin.canteen_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    # Unlink active orders so that history is preserved and we don't break order invoices
    db.query(OrderItem).filter(OrderItem.food_id == food_id).update({"food_id": None})

    name = food.name
    if food.inventory:
        db.delete(food.inventory)
    db.delete(food)
    db.commit()

    log_action(db, admin.id, "DELETE", "food_items", food_id,
               f"Deleted food item: {name}", request=request)


@router.patch("/{food_id}/availability")
def toggle_availability(food_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    food = db.query(FoodItem).filter(FoodItem.id == food_id, FoodItem.canteen_id == admin.canteen_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    food.is_available = not food.is_available
    food.updated_at = datetime.now()
    db.commit()

    log_action(db, admin.id, "STATUS_CHANGE", "food_items", food.id,
               f"{'Enabled' if food.is_available else 'Disabled'} food: {food.name}", request=request)

    return {"id": food.id, "is_available": food.is_available}
