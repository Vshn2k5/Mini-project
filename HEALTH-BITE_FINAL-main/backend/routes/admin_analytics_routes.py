"""Admin Analytics endpoints — /api/admin/analytics"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text
from database import get_db
from models import Order, HealthProfile, User, FoodItem, OrderItem
from routes.admin_deps import get_current_admin
from typing import Optional
from datetime import datetime, date, timedelta

router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


def _get_date_range(period: str):
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    start_dt = datetime.combine(datetime.now().date() - timedelta(days=days), datetime.min.time())
    return start_dt.isoformat()
    
    
def _apply_dates(query, model, from_date: Optional[str], to_date: Optional[str]):
    is_str = getattr(model, '__tablename__', '') == 'orders'
    if from_date and from_date != 'undefined':
        try:
            start_dt = datetime.fromisoformat(from_date[:10]).replace(hour=0, minute=0, second=0)
            query = query.filter(model.created_at >= (start_dt.isoformat() if is_str else start_dt))
        except Exception: pass
    if to_date and to_date != 'undefined':
        try:
            end_dt = datetime.fromisoformat(to_date[:10]).replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(model.created_at <= (end_dt.isoformat() if is_str else end_dt))
        except Exception: pass
    return query

@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    cid = admin.canteen_id
    
    # Base queries
    order_query = db.query(Order).filter(Order.canteen_id == cid, Order.status == 'completed')
    order_query = _apply_dates(order_query, Order, from_date, to_date)
    
    user_query = db.query(User).filter(User.canteen_id == cid, User.role == 'USER')
    user_query = _apply_dates(user_query, User, from_date, to_date)
    
    # Calculate totals
    orders = order_query.all()
    total_rev = sum((o.total_price or 0) for o in orders)
    total_orders = len(orders)
    avg_val = round(total_rev / total_orders, 2) if total_orders > 0 else 0
    new_users = user_query.count()
    
    return {
        "revenue": {"value": total_rev, "change": 12.5},
        "orders": {"value": total_orders, "change": 8.2},
        "avg_order_value": {"value": avg_val, "change": 4.1},
        "new_users": {"value": new_users, "change": 15.0}
    }


@router.get("/sales")
def sales_trend(
    period: str = Query("30d"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    today = datetime.now()
    end_date = today
    
    # Calculate days based on from/to if provided
    if from_date and from_date != 'undefined' and to_date and to_date != 'undefined':
        try:
            start_dt = datetime.fromisoformat(from_date[:10])
            end_dt = datetime.fromisoformat(to_date[:10])
            days = max(1, (end_dt - start_dt).days + 1)
            end_date = end_dt
        except Exception:
            days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    else:
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        
    # Cap days to prevent massive queries if user selects 10 years
    days = min(days, 365)
        
    labels = []
    revenue_data = []
    orders_data = []
    
    for i in range(days - 1, -1, -1):
        d = end_date - timedelta(days=i)
        date_str = d.strftime("%m-%d") # Use MM-DD for label
        labels.append(date_str)
        
        # Start and end of this day
        d_start = d.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        d_end = d.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        
        # Query orders for this specific day
        daily_orders = db.query(Order).filter(
            Order.canteen_id == admin.canteen_id,
            Order.created_at >= d_start,
            Order.created_at <= d_end,
            Order.status == 'completed'
        ).all()
        
        rev = sum(o.total_price or 0 for o in daily_orders)
        orders_data.append(len(daily_orders))
        revenue_data.append(round(rev, 2))
        
    return {
        "labels": labels,
        "revenue": revenue_data,
        "orders": orders_data
    }


@router.get("/revenue-by-category")
def revenue_by_category(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    from models import FoodItem, OrderItem
    
    query = db.query(
        func.coalesce(FoodItem.category, "Uncategorized").label("category"),
        func.sum(OrderItem.subtotal).label("revenue")
    ).select_from(OrderItem)\
     .join(Order, OrderItem.order_id == Order.id)\
     .outerjoin(FoodItem, FoodItem.id == OrderItem.food_id)\
     .filter(Order.canteen_id == admin.canteen_id, Order.status == "completed")
     
    query = _apply_dates(query, Order, from_date, to_date)
    stats = query.group_by(func.coalesce(FoodItem.category, "Uncategorized")).all()
     
    labels = []
    data = []
    for s in stats:
        if s.category:
            labels.append(s.category)
            data.append(round(s.revenue, 2))
            
    return {
        "labels": labels,
        "data": data
    }


@router.get("/popular-foods")
def popular_foods(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    from models import FoodItem, OrderItem
    
    query = db.query(
        FoodItem.name,
        func.count(OrderItem.id).label("orders"),
        func.sum(OrderItem.subtotal).label("revenue")
    ).join(OrderItem, FoodItem.id == OrderItem.food_id)\
     .join(Order, OrderItem.order_id == Order.id)\
     .filter(Order.canteen_id == admin.canteen_id, Order.status == "completed")
     
    query = _apply_dates(query, Order, from_date, to_date)
    stats = query.group_by(FoodItem.id)\
                 .order_by(text("orders DESC"))\
                 .limit(5).all()
     
    if not stats:
        return []
        
    return [{"name": s.name, "orders": s.orders, "revenue": round(s.revenue, 2), "trend": 10} for s in stats]


@router.get("/category-heatmap")
def category_heatmap(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    query = db.query(Order).filter(
        Order.canteen_id == admin.canteen_id, Order.status == "completed"
    )
    query = _apply_dates(query, Order, from_date, to_date)
    orders = query.all()
    
    from models import OrderItem, FoodItem
    
    order_ids = [o.id for o in orders]
    if not order_ids:
        return {
            "days": days,
            "categories": [],
            "data": []
        }
        
    items = db.query(OrderItem, Order.created_at, FoodItem.category).select_from(OrderItem).join(
        Order, OrderItem.order_id == Order.id
    ).outerjoin(
        FoodItem, OrderItem.food_id == FoodItem.id
    ).filter(
        Order.id.in_(order_ids)
    ).all()

    # Collect unique categories dynamically
    categories_set = set()
    for item in items:
        if item.category:
            categories_set.add(item.category)
    categories = sorted(list(categories_set))
    
    # matrix[day_idx][cat_idx]
    matrix = [[0 for _ in range(len(categories))] for _ in range(len(days))]
    
    for item, created_at, category in items:
        try:
            if not category:
                continue
            dt = datetime.fromisoformat(created_at)
            day_idx = dt.weekday() # 0-6 (Mon-Sun)
            cat_idx = categories.index(category)
            matrix[day_idx][cat_idx] += item.qty
        except:
            continue
            
    data = []
    for d in range(len(days)):
        for c in range(len(categories)):
            if matrix[d][c] > 0:
                data.append([d, c, matrix[d][c]])
    
    return {
        "days": days,
        "categories": categories,
        "data": data
    }


@router.get("/disease-distribution")
def disease_distribution(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    profiles = db.query(HealthProfile).join(User).filter(User.canteen_id == admin.canteen_id).all()
    dist = {"Diabetes": 0, "Hypertension": 0, "Obesity": 0, "Anemia": 0, "Heart Disease": 0}
    
    for p in profiles:
        import json
        try:
            diseases = json.loads(p.disease)
            if not isinstance(diseases, list):
                diseases = []
        except:
            diseases = []
            
        for d in diseases:
            if d.title() in dist:
                dist[d.title()] += 1
                
    # Remove fallback data
        
    return {
        "labels": list(dist.keys()),
        "data": list(dist.values())
    }


@router.get("/risk-trends")
def risk_trends(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # Return empty trends instead of hardcoded mock data
    return {
        "labels": [],
        "datasets": [
            {"label": "High Risk", "data": []},
            {"label": "Medium Risk", "data": []},
            {"label": "Low Risk", "data": []}
        ]
    }


@router.get("/peak-hours")
def peak_hours(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    query = db.query(Order).filter(
        Order.canteen_id == admin.canteen_id, Order.status == "completed"
    )
    query = _apply_dates(query, Order, from_date, to_date)
    orders = query.all()
    
    hour_counts = {h: 0 for h in range(24)}
    for o in orders:
        if o.created_at:
            try:
                dt = datetime.fromisoformat(o.created_at)
                hour_counts[dt.hour] += 1
            except:
                pass
                
    data = [hour_counts[h] for h in range(24)]
        
    return {
        "labels": [f"{i}:00" for i in range(24)],
        "data": data
    }


@router.get("/top-spenders")
def top_spenders(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    query = db.query(Order).options(joinedload(Order.user, innerjoin=False)).filter(
        Order.canteen_id == admin.canteen_id, Order.status == "completed"
    )
    query = _apply_dates(query, Order, from_date, to_date)
    orders = query.all()
    user_spend = {}
    for o in orders:
        uid = o.user_id or 0
        if uid not in user_spend:
            name = o.user.name if o.user else f"Guest {uid}"
            user_spend[uid] = {"name": name, "spent": 0, "orders": 0}
        user_spend[uid]["spent"] += o.total_price or 0
        user_spend[uid]["orders"] += 1
        
    top = sorted(user_spend.values(), key=lambda x: x["spent"], reverse=True)[:5]
    if not top:
        top = []
    return top


@router.get("/top-items")
def top_items(
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    """Provide top selling items for dashboard table"""
    # Calculate from all completed orders
    from models import FoodItem, OrderItem
    
    query = db.query(Order.id).filter(
        Order.canteen_id == admin.canteen_id, Order.status == "completed"
    )
    query = _apply_dates(query, Order, from_date, to_date)
    
    # Get all completed order IDs
    completed_order_ids = [o.id for o in query.all()]
    
    if not completed_order_ids:
        return {"items": []}

    # Aggregate quantities and revenue per food item
    stats = db.query(
        func.coalesce(FoodItem.name, OrderItem.food_name, "Deleted Food").label("name"),
        func.coalesce(FoodItem.category, "Uncategorized").label("category"),
        func.sum(OrderItem.qty).label("sold"),
        func.sum(OrderItem.subtotal).label("revenue")
    ).select_from(OrderItem)\
     .outerjoin(FoodItem, FoodItem.id == OrderItem.food_id)\
     .filter(OrderItem.order_id.in_(completed_order_ids))\
     .group_by(
         func.coalesce(FoodItem.name, OrderItem.food_name, "Deleted Food"),
         func.coalesce(FoodItem.category, "Uncategorized"),
         FoodItem.id
      )\
     .order_by(text("sold DESC"))\
     .limit(5).all()

    total_revenue = sum(s.revenue for s in stats) or 1
    
    items = []
    for i, s in enumerate(stats):
        items.append({
            "rank": i + 1,
            "name": s.name,
            "category": s.category,
            "sold": s.sold,
            "revenue": round(s.revenue, 2),
            "share": round((s.revenue / total_revenue) * 100, 1)
        })

    return {"items": items}


@router.get("/ai-impact")
def ai_impact(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    return {
        "recommendations_served": 0,
        "acceptance_rate": 0,
        "health_improvement_score": +0,
        "top_item_recommended": "N/A"
    }
