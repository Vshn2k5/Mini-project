import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from chatbot_engine import HealthChatbot
from database import get_db
from dependencies import get_current_user
from models import ChatHistory, FoodItem, HealthProfile, User
from analytics import get_risk_prediction

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


def _load_recent_chat(db: Session, user_id: int, limit: int = 5) -> list[dict]:
    """Load the last N chat messages for conversation memory."""
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(limit)
        .all()
    )
    # Return in chronological order
    return [
        {"message": r.message, "response": r.response, "intent": r.intent}
        for r in reversed(rows)
    ]


def _save_chat(db: Session, user_id: int, message: str, response_text: str, intent: str = None):
    """Store a conversation turn in the database."""
    entry = ChatHistory(
        user_id=user_id,
        message=message,
        response=response_text,
        intent=intent,
    )
    db.add(entry)
    db.commit()


@router.post("/query")
async def chatbot_query(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await request.json()
        message = data.get("message", "")
        context = data.get("context", {})

        db_profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
        profile_data = {}
        if db_profile:
            try:
                diseases = json.loads(db_profile.disease) if db_profile.disease else []
            except Exception:
                diseases = []

            try:
                allergies = json.loads(db_profile.allergies) if db_profile.allergies else []
            except Exception:
                allergies = db_profile.allergies

            profile_data = {
                "age": db_profile.age,
                "bmi": db_profile.bmi,
                "gender": db_profile.gender,
                "disease": diseases,
                "allergies": allergies,
                "dietary_preference": db_profile.dietary_preference,
            }
            try:
                profile_data["analytics"] = await get_risk_prediction(current_user=current_user, db=db)
            except Exception as e:
                print(f"Failed to fetch analytics for chatbot: {e}")
                
        db_foods = db.query(FoodItem).filter(FoodItem.is_available == True).all()
        food_items = []
        for item in db_foods:
            food_items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "price": item.price,
                    "image": item.image_emoji,
                    "description": item.description or "",
                    "calories": item.calories,
                    "protein": item.protein,
                    "carbs": item.carbs,
                    "fat": item.fat,
                    "sugar": item.sugar,
                    "sodium": item.sodium,
                    "dietary_type": item.dietary_type or "Veg",
                    "nut_allergy": bool(getattr(item, "nut_allergy", False)),
                    "milk_allergy": bool(getattr(item, "milk_allergy", False)),
                    "seafood_allergy": bool(getattr(item, "seafood_allergy", False)),
                    "gluten_allergy": bool(getattr(item, "gluten_allergy", False)),
                    "soy_allergy": bool(getattr(item, "soy_allergy", False)),
                }
            )

        # Load conversation history for follow-up support
        conversation_history = _load_recent_chat(db, current_user.id)

        chatbot_engine = HealthChatbot({}, food_items, [])
        response = chatbot_engine.get_response(
            user_id=str(current_user.id),
            message=message,
            context=context,
            profile=profile_data,
            conversation_history=conversation_history,
        )

        # Save this conversation turn
        _save_chat(
            db,
            user_id=current_user.id,
            message=message,
            response_text=response.get("text", ""),
            intent=response.get("intent"),
        )

        return response
    except Exception as exc:
        print(f"Chatbot Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
