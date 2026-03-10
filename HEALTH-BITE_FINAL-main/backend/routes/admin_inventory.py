"""Admin Inventory CRUD — /api/admin/inventory"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models import Inventory, FoodItem
from routes.admin_deps import get_current_admin
from routes.audit_helper import log_action
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/admin/inventory", tags=["admin-inventory"])


class InventoryUpdate(BaseModel):
    current_stock: Optional[int] = None
    reorder_level: Optional[int] = None


@router.get("/")
def list_inventory(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    # Sort priority: Out of Stock (stock=0) first, then Low Stock (stock < reorder), then Healthy
    # We use CASE statements for custom ordering in SQL
    q = db.query(Inventory).join(FoodItem).filter(
        FoodItem.canteen_id == admin.canteen_id
    ).order_by(
        text("CASE WHEN current_stock = 0 THEN 0 "
             "WHEN current_stock < reorder_level THEN 1 "
             "ELSE 2 END"),
        FoodItem.name
    )

    if search:
        q = q.filter(FoodItem.name.ilike(f"%{search}%"))

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for inv in items:
        status = "In Stock"
        if inv.current_stock == 0:
            status = "Out of Stock"
        # Use < here to mirror frontend filtering (and the dashboard query)
        elif inv.current_stock < inv.reorder_level:
            status = "Low Stock"

        results.append(
            {
                "id": inv.id,
                "food_id": inv.food_id,
                "food_name": inv.food.name if inv.food else "Unknown",
                "category": inv.food.category if inv.food else "Unknown",
                "current_stock": inv.current_stock,
                "reorder_level": inv.reorder_level,
                "unit": inv.unit,
                "status": status,
                "last_updated": inv.updated_at.isoformat() if inv.updated_at else None,
            }
        )

    # Global summary counts for the strip cards
    global_total = db.query(func.count(Inventory.id)).join(FoodItem).filter(
        FoodItem.canteen_id == admin.canteen_id
    ).scalar() or 0
    global_oos = db.query(func.count(Inventory.id)).join(FoodItem).filter(
        FoodItem.canteen_id == admin.canteen_id,
        Inventory.current_stock == 0
    ).scalar() or 0
    global_low = db.query(func.count(Inventory.id)).join(FoodItem).filter(
        FoodItem.canteen_id == admin.canteen_id,
        Inventory.current_stock > 0,
        Inventory.current_stock < Inventory.reorder_level
    ).scalar() or 0

    return {
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "summary": {
            "total": global_total,
            "lowStock": global_low,
            "outOfStock": global_oos
        },
        "items": results,
    }


@router.put("/{inv_id}")
def update_inventory(
    inv_id: int,
    body: InventoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    inv = db.query(Inventory).filter(Inventory.id == inv_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    before = {
        "current_stock": inv.current_stock,
        "reorder_level": inv.reorder_level,
    }

    if body.current_stock is not None:
        inv.current_stock = body.current_stock
    if body.reorder_level is not None:
        inv.reorder_level = body.reorder_level

    inv.updated_at = datetime.now()
    db.commit()
    db.refresh(inv)

    after = {
        "current_stock": inv.current_stock,
        "reorder_level": inv.reorder_level,
    }

    food_name = inv.food.name if inv.food else f"ID {inv.food_id}"
    log_action(
        db,
        admin.id,
        "UPDATE",
        "inventory",
        inv.id,
        f"Updated stock for {food_name}",
        before=before,
        after=after,
        request=request,
    )

    status_str = "In Stock"
    if inv.current_stock == 0:
        status_str = "Out of Stock"
    elif inv.current_stock < inv.reorder_level:
        status_str = "Low Stock"

    return {
        "id": inv.id,
        "current_stock": inv.current_stock,
        "reorder_level": inv.reorder_level,
        "status": status_str,
        "last_updated": inv.updated_at.isoformat(),
    }
