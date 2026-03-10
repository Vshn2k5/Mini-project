"""Admin Dashboard endpoints — /api/admin/*"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models import User, Order, FoodItem, Inventory, HealthProfile, Canteen
from routes.admin_deps import get_current_admin
from datetime import datetime, date, timedelta

router = APIRouter(prefix="/api/admin", tags=["admin-dashboard"])


def _today_range():
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return start.isoformat(), end.isoformat()


@router.get("/canteen-info")
def canteen_info(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Return the canteen info for the logged-in admin."""
    canteen = db.query(Canteen).filter(Canteen.id == admin.canteen_id).first()
    if not canteen:
        return {"canteen_name": "Unknown", "institution_name": "Unknown", "canteen_code": "N/A"}
    return {
        "canteen_name": canteen.canteen_name,
        "institution_name": canteen.institution_name,
        "canteen_code": canteen.canteen_code,
    }


@router.get("/overview")
def overview(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    cid = admin.canteen_id
    today_start, today_end = _today_range()

    # Revenue today — scoped to canteen
    revenue_today = db.query(func.coalesce(func.sum(Order.total_price), 0)).filter(
        Order.canteen_id == cid,
        Order.created_at >= today_start, Order.created_at <= today_end
    ).scalar() or 0

    # Same period last week
    last_week_start = (datetime.combine(datetime.now().date(), datetime.min.time()) - timedelta(days=7)).isoformat()
    last_week_end = (datetime.combine(datetime.now().date(), datetime.max.time()) - timedelta(days=7)).isoformat()
    revenue_last_week = db.query(func.coalesce(func.sum(Order.total_price), 0)).filter(
        Order.canteen_id == cid,
        Order.created_at >= last_week_start, Order.created_at <= last_week_end
    ).scalar() or 0

    revenue_change = 0
    if revenue_last_week > 0:
        revenue_change = round((revenue_today - revenue_last_week) / revenue_last_week * 100, 1)

    # Orders today
    orders_today = db.query(func.count(Order.id)).filter(
        Order.canteen_id == cid,
        Order.created_at >= today_start, Order.created_at <= today_end
    ).scalar() or 0

    orders_pending = db.query(func.count(Order.id)).filter(
        Order.canteen_id == cid,
        Order.status == "pending",
        Order.created_at >= today_start, Order.created_at <= today_end
    ).scalar() or 0

    # Users — scoped to canteen
    total_users = db.query(func.count(User.id)).filter(
        User.canteen_id == cid, User.role == "USER", User.disabled == 0
    ).scalar() or 0

    month_start_dt = datetime.combine(datetime.now().date().replace(day=1), datetime.min.time())
    new_this_month = db.query(func.count(User.id)).filter(
        User.canteen_id == cid,
        User.role == "USER",
        User.created_at >= month_start_dt
    ).scalar() or 0

    # Low stock — scoped to canteen foods
    low_stock = db.query(func.count(Inventory.id)).join(FoodItem).filter(
        FoodItem.canteen_id == cid,
        Inventory.current_stock > 0,
        Inventory.current_stock < Inventory.reorder_level
    ).scalar() or 0

    out_of_stock = db.query(func.count(Inventory.id)).join(FoodItem).filter(
        FoodItem.canteen_id == cid,
        Inventory.current_stock == 0
    ).scalar() or 0

    revenue_change_str = f"{'+' if revenue_change >= 0 else ''}{revenue_change}%"

    return {
        "revenue": {"value": round(revenue_today, 2), "change": revenue_change_str},
        "orders": {"value": orders_today, "pending": orders_pending},
        "users": {"value": total_users, "newThisMonth": new_this_month},
        "lowStock": {"value": low_stock, "outOfStock": out_of_stock},
    }


@router.get("/analytics/orders-by-hour-today")
def orders_by_hour(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    today_start, today_end = _today_range()
    orders = db.query(Order).filter(
        Order.canteen_id == admin.canteen_id,
        Order.created_at >= today_start, Order.created_at <= today_end
    ).all()

    hour_counts = {}
    for order in orders:
        try:
            dt = datetime.fromisoformat(order.created_at)
            h = dt.hour
            hour_counts[h] = hour_counts.get(h, 0) + 1
        except Exception:
            pass

    canteen_hours = range(8, min(datetime.now().hour + 1, 22))
    labels = [f"{h % 12 or 12}{'AM' if h < 12 else 'PM'}" for h in canteen_hours]
    counts = [hour_counts.get(h, 0) for h in canteen_hours]

    return {"hours": labels, "counts": counts}


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Return food items with high sodium or sugar as risk alerts."""
    risky = db.query(FoodItem).filter(
        FoodItem.canteen_id == admin.canteen_id,
        FoodItem.is_available == True,
        (FoodItem.sodium > 800) | (FoodItem.sugar > 15)
    ).limit(10).all()

    alerts = []
    for f in risky:
        if f.sodium > 800:
            flag = f"High Sodium ({f.sodium}mg)"
            risk = "High" if f.sodium > 1200 else "Medium"
        else:
            flag = f"High Sugar ({f.sugar}g)"
            risk = "High" if f.sugar > 25 else "Medium"

        alerts.append({
            "id": f.id,
            "message": f"{f.name}: {flag}",
            "time": "System Alert",
            "type": "warn" if risk == "Medium" else "error"
        })

    return {"alerts": alerts}


@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Legacy endpoint — keep for admin.html gateway compatibility."""
    ov = overview(db, admin)
    return {
        "orders_today": ov["orders"]["value"],
        "revenue_today": ov["revenue"]["value"],
        "risk_alerts": len(get_alerts(db, admin)),
        "system_health": 98,
        "user_health_trend": [],
    }
