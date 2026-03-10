"""Admin Users Management — /api/admin/users"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User
from routes.admin_deps import get_current_admin
from routes.audit_helper import log_action
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter(prefix="/api/admin", tags=["admin-users"])


class UserUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None  # Active | Deactivated


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(User).filter(User.canteen_id == admin.canteen_id)

    if search:
        q = q.filter((User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    if role and role != "all":
        q = q.filter(User.role == role)

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    # print(f"DEBUG: admin_users.list_users - Query result: total={total}, items_returned={len(items)}")

    results = []
    for u in items:
        # Get risk level if profile exists
        risk_level = "Unknown"
        risk_score = 0
        conditions = []
        dietary_preferences = []
        
        if u.health_profile:
            risk_level = u.health_profile.risk_level or "Unknown"
            risk_score = u.health_profile.risk_score or 0
            # Parse disease string (assuming it's a JSON list string like "['Diabetes']")
            try:
                disease_str = u.health_profile.disease or "[]"
                # Handle potential single quotes if not pure JSON
                if "'" in disease_str and '"' not in disease_str:
                    disease_str = disease_str.replace("'", '"')
                conditions = json.loads(disease_str)
            except:
                conditions = [u.health_profile.disease] if u.health_profile.disease and u.health_profile.disease != "None" else []
            
            dietary_preferences = [u.health_profile.dietary_preference] if u.health_profile.dietary_preference else []

        # Order Stats
        total_orders = len(u.orders)
        total_spent = sum(o.total_price for o in u.orders) if u.orders else 0
        avg_value = round(total_spent / total_orders, 2) if total_orders > 0 else 0

        # Mock AI Insights (to be replaced by real engine later)
        compliance = 100 - (risk_score // 2) if risk_score < 100 else 10
        top_cat = "Salads & Proteins" if risk_level == "Low" else "Controlled Grains"
        
        results.append(
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "disabled": u.disabled,
                "joined_at": u.created_at.isoformat() if u.created_at else None,
                "conditions": conditions,
                "dietary_preferences": dietary_preferences,
                "order_stats": {
                    "total_orders": total_orders,
                    "total_spent": total_spent,
                    "avg_order_value": avg_value
                },
                "ai_insights": {
                    "top_category": top_cat,
                    "flagged_items": "High Sodium Snacks" if risk_level == "High" else "None",
                    "compliance_rate": compliance
                }
            }
        )

    return {
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "items": results,
    }


@router.put("/users/{user_id}")
def update_user_general(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Unified endpoint for Role and Status updates as expected by frontend"""
    user = db.query(User).filter(User.id == user_id, User.canteen_id == admin.canteen_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = []
    before = {}
    after = {}

    # Update Role
    if body.role:
        valid_roles = {"USER", "ADMIN"}
        if body.role not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role. Must be USER or ADMIN.")
        
        if user.id == admin.id and body.role != user.role:
            raise HTTPException(status_code=403, detail="Cannot change your own role")
            
        old_role = user.role
        if old_role != body.role:
            before["role"] = old_role
            after["role"] = body.role
            user.role = body.role
            changes.append(f"Changed role from {old_role} to {body.role}")

    # Update Status
    if body.status:
        if body.status not in ["Active", "Deactivated"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        new_disabled = 1 if body.status == "Deactivated" else 0
        if user.id == admin.id and new_disabled == 1:
            raise HTTPException(status_code=400, detail="Cannot disable your own account")
            
        old_status = "Deactivated" if user.disabled == 1 else "Active"
        if old_status != body.status:
            before["disabled"] = user.disabled
            after["disabled"] = new_disabled
            user.disabled = new_disabled
            changes.append(f"Changed status to {body.status}")

    if changes:
        db.commit()
        log_action(
            db,
            admin.id,
            "UPDATE",
            "users",
            user.id,
            "; ".join(changes),
            before=before,
            after=after,
            request=request,
        )

    return {
        "id": user.id,
        "role": user.role,
        "status": "Deactivated" if user.disabled == 1 else "Active",
        "email": user.email
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    body: UserUpdate, # Reuse schema
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return update_user_general(user_id, body, request, db, admin)


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    body: UserUpdate, # Reuse schema
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return update_user_general(user_id, body, request, db, admin)
