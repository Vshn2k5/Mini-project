from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from dependencies import get_current_user
from models import User, Order, OrderItem, HealthProfile, FoodItem
from datetime import datetime, timedelta
import json

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"]
)

# ─── PYDANTIC SCHEMAS ──────────────────────────────────────────────────────────

class BudgetLimitUpdate(BaseModel):
    weekly_budget: float

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def _get_conditions(profile: HealthProfile) -> list[str]:
    """Parse conditions from health profile."""
    if not profile or not profile.disease:
        return []
    try:
        raw = json.loads(profile.disease)
        return [c.title() if isinstance(c, str) else c for c in raw]
    except Exception:
        return []


def _get_orders_in_range(db: Session, user_id: int, days: int):
    """Fetch orders within the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    return db.query(Order).filter(
        Order.user_id == user_id,
        Order.created_at >= cutoff
    ).all()


def _map_order_items(db: Session, order_ids: list[int]):
    """Fetch and map order items with food details."""
    if not order_ids:
        return []
    return db.query(OrderItem, FoodItem).join(
        FoodItem, OrderItem.food_id == FoodItem.id
    ).filter(OrderItem.order_id.in_(order_ids)).all()

# ─── BUDGET LIMIT ENDPOINTS ────────────────────────────────────────────────────

@router.get("/budget/limit")
async def get_budget_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's current weekly budget limit."""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        return {"weekly_budget": 500.0}
    return {"weekly_budget": profile.weekly_budget or 500.0}


@router.post("/budget/limit")
async def set_budget_limit(
    payload: BudgetLimitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set or update the user's weekly budget limit."""
    if payload.weekly_budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0.")

    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        profile = HealthProfile(user_id=current_user.id, weekly_budget=payload.weekly_budget)
        db.add(profile)
    else:
        profile.weekly_budget = payload.weekly_budget

    db.commit()
    return {"message": "Budget updated successfully.", "weekly_budget": payload.weekly_budget}

# ─── NUTRITION (DAILY DASHBOARD) ───────────────────────────────────────────────

@router.get("/nutrition")
async def get_nutrition_analytics(
    days: int = Query(7),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now()
    cutoff_date = (today - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Initialize all days
    daily_stats = {}
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        daily_stats[date_str] = {
            "day": date_str,
            "day_name": d.strftime("%a"),
            "calories": 0, "protein": 0, "carbs": 0,
            "fat": 0, "sugar": 0, "sodium": 0
        }

    orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.created_at >= cutoff_date.isoformat()
    ).all()

    order_date_map = {}
    for o in orders:
        try:
            dt = datetime.fromisoformat(str(o.created_at).replace('Z', ''))
            order_date_map[o.id] = dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    items = _map_order_items(db, list(order_date_map.keys()))
    for oi, food in items:
        date_str = order_date_map.get(oi.order_id)
        if date_str and date_str in daily_stats:
            qty = oi.qty or 1
            daily_stats[date_str]["calories"] += (food.calories or 0) * qty
            daily_stats[date_str]["protein"]  += (food.protein or 0) * qty
            daily_stats[date_str]["carbs"]    += (food.carbs or 0) * qty
            daily_stats[date_str]["fat"]      += (food.fat or 0) * qty
            daily_stats[date_str]["sugar"]    += (food.sugar or 0) * qty
            daily_stats[date_str]["sodium"]   += (food.sodium or 0) * qty

    # Limits based on HealthProfile conditions
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    conditions = _get_conditions(profile)

    sugar_limit  = 30 if "Diabetes" in conditions else 50
    sodium_limit = 1500 if "Hypertension" in conditions else 2300
    cal_limit    = 1600 if "Obesity" in conditions else 2000

    return {
        "daily_data": list(daily_stats.values()),
        "limits": {
            "calories": cal_limit, "sugar": sugar_limit, "sodium": sodium_limit,
            "protein": 60, "carbs": 250, "fat": 70
        },
        "macro_distribution": {"protein": 25, "carbs": 50, "fat": 25}
    }


# ─── DASHBOARD NUTRITION (TODAY ONLY, USED BY user.html & analysis-daily.html) ─

@router.get("/dashboard")
async def get_dashboard_nutrition(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns today's real nutrition totals calculated from actual OrderItems × FoodItem records.
    Also returns condition-adjusted daily limits and deterministic health insights.
    No mock / hardcoded values.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Fetch all of today's orders
    orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.created_at >= today_start.isoformat()
    ).all()

    # Aggregate nutrition from order_items × food_items
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0,
              "fat": 0.0, "sugar": 0.0, "sodium": 0.0, "spent": 0.0}

    order_ids = [o.id for o in orders]
    if order_ids:
        items = db.query(OrderItem, FoodItem).join(
            FoodItem, OrderItem.food_id == FoodItem.id
        ).filter(OrderItem.order_id.in_(order_ids)).all()

        for oi, food in items:
            qty = oi.qty or 1
            totals["calories"] += (food.calories or 0) * qty
            totals["protein"]  += (food.protein  or 0) * qty
            totals["carbs"]    += (food.carbs    or 0) * qty
            totals["fat"]      += (food.fat      or 0) * qty
            totals["sugar"]    += (food.sugar    or 0) * qty
            totals["sodium"]   += (food.sodium   or 0) * qty

    for o in orders:
        totals["spent"] += o.total_price or 0

    # Round to 1 decimal
    totals = {k: round(v, 1) for k, v in totals.items()}

    # Condition-adjusted limits
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    conditions = _get_conditions(profile)

    limits = {
        "calories": 1600 if "Obesity" in conditions else 2000,
        "protein":  80  if any(c in conditions for c in ["Diabetes", "Hypertension"]) else 60,
        "carbs":    200 if "Diabetes" in conditions else 250,
        "fat":      55  if "Obesity" in conditions else 70,
        "sugar":    30  if "Diabetes" in conditions else 50,
        "sodium":   1500 if "Hypertension" in conditions else 2300,
    }

    # Deterministic insights
    insights = []
    if totals["protein"] < limits["protein"] * 0.5:
        insights.append(f"Protein intake is low today ({totals['protein']}g). Add eggs, dal, or grilled chicken.")
    if totals["sugar"] > limits["sugar"] * 0.8:
        insights.append(f"Sugar intake ({totals['sugar']}g) is nearing your daily limit of {limits['sugar']}g. Avoid sweetened drinks.")
    if totals["sodium"] > limits["sodium"] * 0.8:
        insights.append(f"Sodium is high ({totals['sodium']}mg). Choose low-salt options for the rest of the day.")
    if totals["carbs"] > limits["carbs"] * 0.9:
        insights.append(f"Carbohydrate intake is nearly at your daily limit ({totals['carbs']}g / {limits['carbs']}g).")
    if totals["calories"] == 0:
        insights.append("No food orders recorded for today yet. Log your first meal!")
    if not insights:
        insights.append("Great job! Your nutrition is well-balanced today. Keep it up.")

    cal_pct = round(min(100, totals["calories"] / limits["calories"] * 100)) if limits["calories"] else 0

    return {
        "date":       today_str,
        "totals":     totals,
        "limits":     limits,
        "cal_pct":    cal_pct,
        "orders_today": len(orders),
        "conditions": conditions,
        "insights":   insights
    }



# ─── RISK ──────────────────────────────────────────────────────────────────────

@router.get("/risk")
async def get_health_risks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    conditions = _get_conditions(profile)
    if not conditions:
        return []

    today = datetime.now()
    this_week_start = (today - timedelta(days=7)).isoformat()
    last_week_start = (today - timedelta(days=14)).isoformat()

    orders_this_week = db.query(Order).filter(
        Order.user_id == current_user.id, Order.created_at >= this_week_start
    ).all()
    orders_last_week = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.created_at >= last_week_start, Order.created_at < this_week_start
    ).all()

    def sum_macros(orders_list):
        return (
            sum(o.total_sugar or 0 for o in orders_list),
            sum(o.total_sodium or 0 for o in orders_list),
            sum(o.total_calories or 0 for o in orders_list)
        )

    tw_sugar, tw_sodium, tw_cal = sum_macros(orders_this_week)
    lw_sugar, lw_sodium, lw_cal = sum_macros(orders_last_week)
    has_orders = bool(orders_this_week or orders_last_week)

    results = []
    for cond in conditions:
        trend, msg = "stable", "Maintaining steady nutritional boundaries."
        if has_orders:
            if cond == "Diabetes":
                if tw_sugar > lw_sugar:   trend, msg = "up",   "Sugar intake increased this week."
                elif tw_sugar < lw_sugar: trend, msg = "down", "Sugar intake decreased this week."
            elif cond == "Hypertension":
                if tw_sodium > lw_sodium:   trend, msg = "up",   "Sodium intake increased this week."
                elif tw_sodium < lw_sodium: trend, msg = "down", "Sodium intake decreased this week."
            elif cond == "Obesity":
                if tw_cal > lw_cal:   trend, msg = "up",   "Calorie intake increased this week."
                elif tw_cal < lw_cal: trend, msg = "down", "Calorie intake decreased this week."
        results.append({"name": cond, "risk_score": profile.risk_score or 0, "trend": trend, "message": msg})

    return results

# ─── HEALTH PREDICTION ─────────────────────────────────────────────────────────

@router.get("/prediction")
async def get_health_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    conditions = _get_conditions(profile)

    sugar_limit_weekly  = 210 if "Diabetes" in conditions else 350
    sodium_limit_weekly = 10500 if "Hypertension" in conditions else 16100
    cal_limit_weekly    = 11200 if "Obesity" in conditions else 14000

    orders = _get_orders_in_range(db, current_user.id, 7)
    total_sugar  = sum(o.total_sugar or 0 for o in orders)
    total_sodium = sum(o.total_sodium or 0 for o in orders)
    total_cal    = sum(o.total_calories or 0 for o in orders)

    predictions = []

    sugar_pct = (total_sugar / sugar_limit_weekly * 100) if sugar_limit_weekly else 0
    if sugar_pct > 80:
        predictions.append({
            "id": "PRED-SUG-WARN", "type": "warning", "title": "Sugar Intake Warning",
            "description": f"You consumed {total_sugar:.0f}g sugar this week. At this rate you will exceed your limit of {sugar_limit_weekly}g.",
            "suggestion": "Opt for sugar-free beverages or skip desserts.", "intensity": min(100, int(sugar_pct))
        })
    elif sugar_pct < 50:
        predictions.append({
            "id": "PRED-SUG-SUCC", "type": "success", "title": "Optimal Sugar Control",
            "description": f"You are well within your weekly sugar limit ({total_sugar:.0f}g / {sugar_limit_weekly}g).",
            "suggestion": "Keep up the great work!", "intensity": int(sugar_pct)
        })

    sodium_pct = (total_sodium / sodium_limit_weekly * 100) if sodium_limit_weekly else 0
    if sodium_pct > 80:
        predictions.append({
            "id": "PRED-SOD-WARN", "type": "warning", "title": "Sodium Intake Warning",
            "description": f"You consumed {total_sodium:.0f}mg sodium this week. Nearing your limit of {sodium_limit_weekly}mg.",
            "suggestion": "Avoid processed or high-sodium soup items.", "intensity": min(100, int(sodium_pct))
        })

    cal_pct = (total_cal / cal_limit_weekly * 100) if cal_limit_weekly else 0
    if cal_pct > 80:
        predictions.append({
            "id": "PRED-CAL-WARN", "type": "warning", "title": "Calorie Intake Warning",
            "description": f"You consumed {total_cal:.0f}kCal this week. Nearing your limit of {cal_limit_weekly}kCal.",
            "suggestion": "Consider lighter meals for the rest of the week.", "intensity": min(100, int(cal_pct))
        })

    if not predictions:
        predictions.append({
            "id": "PRED-GEN-INFO", "type": "info", "title": "On Track with Macros",
            "description": "Your macronutrient tracking is looking stable and within normal limits.",
            "suggestion": "Maintain your current eating habits.", "intensity": 50
        })

    return predictions

# ─── BUDGET ────────────────────────────────────────────────────────────────────

@router.get("/budget")
async def get_budget_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now()
    cutoff_7d  = (today - timedelta(days=7)).isoformat()
    cutoff_30d = (today - timedelta(days=30)).isoformat()

    # Get user's budget target from profile
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    budget_target = (profile.weekly_budget if profile and profile.weekly_budget else 500.0)

    # Spending last 7 days
    orders_7d = db.query(Order).filter(
        Order.user_id == current_user.id, Order.created_at >= cutoff_7d
    ).all()
    total_spent_7d = sum(o.total_price or 0 for o in orders_7d)

    # Food trends from last 30 days
    orders_30d = db.query(Order).filter(
        Order.user_id == current_user.id, Order.created_at >= cutoff_30d
    ).all()
    order_ids_30d = [o.id for o in orders_30d]

    item_counts = {}
    if order_ids_30d:
        order_items = _map_order_items(db, order_ids_30d)
        for oi, food in order_items:
            item_counts[food.name] = item_counts.get(food.name, 0) + (oi.qty or 1)

    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)

    def trend_entry(label, items, idx, default_name, change, t):
        name = items[idx][0] if len(items) > idx else default_name
        return {"label": label, "name": name, "change": change, "type": t}

    food_trends = [
        trend_entry("TOP CHOICE",  sorted_items, 0, "Palak Dal",                  "+12%",  "positive"),
        trend_entry("RISING",      sorted_items, 1, "Mixed Vegetable Oats Upma",  "+25%",  "positive"),
        trend_entry("CONSISTENT",  sorted_items, 2, "Grilled Chicken Bowl",       "Stable","neutral"),
        {"label": "DECLINING", "name": "Fried Snacks", "change": "-15%", "type": "negative"},
    ]

    # Cost-effective suggestions sourced from cheapest food items in the canteen
    cheap_foods = db.query(FoodItem).filter(FoodItem.is_available == True).order_by(FoodItem.price.asc()).limit(3).all()
    cost_suggestions = []
    for food in cheap_foods:
        cost_suggestions.append({
            "emoji": food.image_emoji or "🍽️",
            "name": food.name,
            "price_per_meal": round(food.price, 2),
            "savings": round(budget_target * 0.03, 2)  # dynamic "save" hint
        })
    # Fallback if no foods
    if not cost_suggestions:
        cost_suggestions = [
            {"emoji": "🥗", "name": "Bulk Quinoa & Beans", "price_per_meal": 1.20, "savings": 4.50},
            {"emoji": "🍳", "name": "Seasonal Veggie Stir-fry", "price_per_meal": 2.30, "savings": 3.20},
            {"emoji": "🥣", "name": "Oatmeal with Nuts", "price_per_meal": 0.80, "savings": 2.50},
        ]

    budget_pct = min(100, (total_spent_7d / budget_target * 100)) if budget_target else 0
    budget_status = "OVER BUDGET" if total_spent_7d > budget_target else "UNDER BUDGET"

    return {
        "budget_target":     budget_target,
        "budget_value":      round(total_spent_7d, 2),
        "budget_status":     budget_status,
        "budget_percentage": round(budget_pct, 1),
        "food_trends":       food_trends,
        "cost_suggestions":  cost_suggestions,
    }

# ─── AI PREDICTIONS (for analysis-predictions.html) ───────────────────────────

@router.get("/ai/predictions")
async def get_ai_predictions(
    timeframe: str = Query("Daily"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    conditions = _get_conditions(profile)

    # Determine days and labels based on timeframe
    if timeframe == "Daily":
        days = 1
        labels = ["08:00", "10:00", "12:00", "14:00", "NOW"]
    elif timeframe == "Weekly":
        days = 7
        labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    elif timeframe == "Monthly":
        days = 30
        labels = ["WK 1", "WK 2", "WK 3", "WK 4"]
    else:  # Yearly
        days = 365
        labels = ["Q1", "Q2", "Q3", "Q4"]

    orders = _get_orders_in_range(db, current_user.id, days)
    total_sugar  = sum(o.total_sugar or 0 for o in orders)
    total_cal    = sum(o.total_calories or 0 for o in orders)
    total_sodium = sum(o.total_sodium or 0 for o in orders)

    # Compute wellness score (100 - penalties for over-limits)
    cal_limit  = 1600 if "Obesity" in conditions else 2000
    sug_limit  = 30 if "Diabetes" in conditions else 50

    daily_cal_avg = total_cal / max(days, 1)
    daily_sug_avg = total_sugar / max(days, 1)

    score = 100
    if daily_cal_avg > cal_limit: score -= 15
    if daily_sug_avg > sug_limit: score -= 15
    if total_sodium / max(days, 1) > 2300: score -= 10
    score = max(40, score)

    # Build chart data points based on score trend (simple linear fill)
    n = len(labels)
    data_points = [max(40, int(score - (n - 1 - i) * 3)) for i in range(n)]

    is_positive = score >= 70
    diff = {
        "text":  f"+{int((score - 60) / 60 * 20)}% forecast" if is_positive else f"-{int((70 - score) / 70 * 10)}% forecast",
        "icon":  "fa-arrow-trend-up" if is_positive else "fa-arrow-trend-down",
        "color": "positive" if is_positive else "negative"
    }

    # Dynamic predictions based on conditions and actual data
    predictions = []
    if total_sugar > 0 and daily_sug_avg > sug_limit * 0.7:
        predictions.append({
            "icon": "fa-triangle-exclamation", "title": "Sugar Spike Risk",
            "sub": "Linked to: HIGH SUGAR INTAKE",
            "desc": f"Your average daily sugar ({daily_sug_avg:.0f}g) is nearing the safe limit of {sug_limit}g. Consider avoiding sweetened beverages.",
            "risk": "Warning"
        })
    else:
        predictions.append({
            "icon": "fa-fire-flame-curved", "title": "Metabolic Boost",
            "sub": "Linked to: High Protein",
            "desc": "Your protein intake is driving better metabolic recovery and stable energy.",
            "risk": "Positive"
        })

    if total_sodium > 0 and total_sodium / max(days, 1) > 1800:
        predictions.append({
            "icon": "fa-heart", "title": "Blood Pressure Watch",
            "sub": "Linked to: HIGH SODIUM",
            "desc": f"Average sodium ({total_sodium / max(days, 1):.0f}mg/day) is elevated. Reduce salty snacks and processed foods.",
            "risk": "Moderate"
        })
    else:
        predictions.append({
            "icon": "fa-brain", "title": "Focus Peak",
            "sub": "Linked to: Omega-3 & Balanced Nutrients",
            "desc": "Balanced nutrient intake is maximizing your cognitive performance and alertness.",
            "risk": "High Efficiency"
        })

    # Dynamic insight
    if conditions:
        insight = f"Based on your health profile (<strong>{', '.join(conditions)}</strong>), your intake pattern over the past {days} day(s) shows a wellness score of <strong>{score}/100</strong>. Focus on reducing flagged nutrients for improvement."
    elif score >= 80:
        insight = f"Your dietary choices are excellent! A wellness score of <strong>{score}/100</strong> indicates great macro balance. Keep up the nutritious habits."
    else:
        insight = f"Your current score is <strong>{score}/100</strong>. Minor improvements in sugar and sodium intake can push this significantly higher."

    return {
        "score":       score,
        "diff":        diff,
        "insight":     insight,
        "chart":       {"labels": labels, "data": data_points},
        "predictions": predictions
    }

# ─── PERFORMANCE ANALYTICS (for analysis-performance.html) ────────────────────

@router.get("/performance")
async def get_performance_analytics(
    period: str = Query("Weekly"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now()

    if period == "Daily":
        days = 1
        labels = [(today - timedelta(hours=i * 3)).strftime("%H:00") for i in range(4, -1, -1)]
    elif period == "Weekly":
        days = 7
        labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    elif period == "Monthly":
        days = 30
        labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
    else:  # Yearly
        days = 365
        labels = ["Q1", "Q2", "Q3", "Q4"]

    orders = _get_orders_in_range(db, current_user.id, days)

    total_healthy   = 0
    total_unhealthy = 0
    food_counts: dict = {}

    for o in orders:
        is_healthy = (o.total_calories or 0) < 600 and (o.total_sugar or 0) < 20
        if is_healthy:
            total_healthy += 1
        else:
            total_unhealthy += 1

        order_items = db.query(OrderItem, FoodItem).join(
            FoodItem, OrderItem.food_id == FoodItem.id
        ).filter(OrderItem.order_id == o.id).all()

        for oi, food in order_items:
            if food.name not in food_counts:
                food_counts[food.name] = {
                    "count":   0,
                    "healthy": (food.calories or 0) < 500 and (food.sugar or 0) < 15,
                    "item":    food
                }
            food_counts[food.name]["count"] += (oi.qty or 1)

    # Build chart data: distribute healthy/unhealthy across labels
    n = len(labels)
    healthy_counts   = [max(0, total_healthy // max(n, 1))] * n
    unhealthy_counts = [max(0, total_unhealthy // max(n, 1))] * n

    score = 100 if (total_healthy + total_unhealthy) == 0 else int(
        total_healthy / (total_healthy + total_unhealthy) * 100
    )

    sorted_foods = sorted(food_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    top_performers = []
    focus_areas    = []

    for name, info in sorted_foods:
        if info["healthy"] and len(top_performers) < 3:
            top_performers.append({
                "icon":     "fa-leaf",
                "name":     name,
                "subtitle": f"Ordered {info['count']} time(s)",
                "xp":       f"+{info['count'] * 50} XP"
            })
        elif not info["healthy"] and len(focus_areas) < 3:
            focus_areas.append({
                "name":     name,
                "subtitle": f"{info['count']}x this {period.lower()}",
                "badge":    "Limit" if info["count"] > 2 else "Watch"
            })

    if not top_performers:
        top_performers = [
            {"icon": "fa-droplet", "name": "Hydration Goal", "subtitle": "Stay well hydrated", "xp": "+100 XP"},
            {"icon": "fa-seedling", "name": "Eat More Greens", "subtitle": "Aim for daily veg", "xp": "+80 XP"},
        ]
    if not focus_areas:
        focus_areas = [
            {"name": "Deep Fried Items", "subtitle": "High Trans-fats", "badge": "Watch"},
            {"name": "Sugary Beverages", "subtitle": "High in empty calories", "badge": "Limit"},
        ]

    return {
        "chart":          {"labels": labels, "healthy": healthy_counts, "unhealthy": unhealthy_counts},
        "score":          score,
        "change_pct":     12,
        "top_performers": top_performers,
        "focus_areas":    focus_areas
    }

# ─── TIMELINE ──────────────────────────────────────────────────────────────────

@router.get("/timeline")
async def get_health_timeline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.id.desc()).limit(10).all()
    timeline = []

    for o in orders:
        try:
            dt = datetime.fromisoformat(str(o.created_at).replace('Z', ''))
            score = 65 if (o.total_sugar or 0) > 20 or (o.total_sodium or 0) > 1000 else 85
            items_count = db.query(OrderItem).filter(OrderItem.order_id == o.id).count()
            timeline.append({
                "date":  dt.strftime("%b %d"),
                "score": score,
                "event": f"Ordered {items_count} item(s)"
            })
        except Exception:
            pass

    if not timeline:
        timeline.append({
            "date":  datetime.now().strftime("%b %d"),
            "score": 100,
            "event": "Profile Created"
        })

    return timeline


# ─── RISK PREDICTION ────────────────────────────────────────────────────────────

@router.get("/risk-prediction")
async def get_risk_prediction(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Full AI risk prediction report for the current user.
    Scores every food item using health_scoring.py metrics,
    detects patterns, and returns deterministic dietary advice.
    """
    try:
        from ai_engine.risk_prediction import (
            calculate_health_score, classify_risk_level,
            generate_advice, analyze_consumption_pattern
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Risk engine import error: {e}")

    # Fetch profile
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    conditions = _get_conditions(profile)
    allergies  = profile.allergies if profile and profile.allergies else ""

    user_profile_dict = {
        "conditions": conditions,
        "allergies":  allergies,
        "bmi":        float(profile.bmi or 22) if profile else 22,
    }

    # Last 7 days' orders and food items
    orders   = _get_orders_in_range(db, current_user.id, days=7)
    oi_pairs = _map_order_items(db, [o.id for o in orders])

    # Score every food from actual orders
    seen_food_ids: set[int] = set()
    risky_foods:   list[dict] = []
    all_scores:    list[int]  = []

    # Nutrition aggregates for projection
    total_sugar    = 0.0
    total_sodium   = 0.0
    total_calories = 0.0
    def _date_key(o):
        ca = o.created_at
        if ca is None:
            return None
        if hasattr(ca, 'strftime'):
            return ca.strftime('%Y-%m-%d')
        return str(ca)[:10]
    day_count = max(1, len(set(filter(None, (_date_key(o) for o in orders)))))


    for oi, food in oi_pairs:
        qty = oi.qty or 1
        total_sugar    += (food.sugar    or 0) * qty
        total_sodium   += (food.sodium   or 0) * qty
        total_calories += (food.calories or 0) * qty

        if food.id not in seen_food_ids:
            seen_food_ids.add(food.id)
            food_dict = {
                "name":          food.name,
                "sugar":         food.sugar    or 0,
                "sodium":        food.sodium   or 0,
                "calories":      food.calories or 0,
                "fat":           food.fat      or 0,
                "nut_allergy":   getattr(food, "nut_allergy",     False),
                "milk_allergy":  getattr(food, "milk_allergy",    False),
                "seafood_allergy": getattr(food, "seafood_allergy", False),
                "gluten_allergy":  getattr(food, "gluten_allergy",  False),
                "soy_allergy":     getattr(food, "soy_allergy",     False),
            }
            # New health_scoring output: {"score": 0-100, "overall_label": ..., "reasons": ..., "warnings": ..., "explanation": ...}
            score_data = calculate_health_score(food_dict, user_profile_dict)
            score = score_data["score"]
            level = classify_risk_level(score) # Use frontend friendly mapping (e.g., < 45 = DANGER)
            
            all_scores.append(score)

            if score < 75:  # Under 75 is MODERATE or DANGER
                risky_foods.append({
                    "id":         food.id,
                    "name":       food.name,
                    "sugar":      food.sugar    or 0,
                    "sodium":     food.sodium   or 0,
                    "calories":   food.calories or 0,
                    "risk_score": score,
                    "risk_level": level,
                    "warnings":   score_data["warnings"],
                    "reasons":    score_data["reasons"],
                    "explanation": score_data["explanation"],
                    "image":      food.image_emoji or "🍽️",
                })

    # Averages
    avg_daily_sugar    = round(total_sugar    / day_count, 1)
    avg_daily_sodium   = round(total_sodium   / day_count, 1)
    avg_daily_calories = round(total_calories / day_count, 1)
    # The new score is 0-100 format, where 100 is best.
    avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 100

    # Pattern analysis + projection
    danger_foods = [f for f in risky_foods if f["risk_level"] == "DANGER"]
    pattern = analyze_consumption_pattern(
        risky_foods_last_week=danger_foods,
        conditions=conditions,
        avg_daily_sugar=avg_daily_sugar,
        avg_daily_sodium=avg_daily_sodium,
    )

    # Advice
    advice = generate_advice(
        avg_score=avg_score,
        conditions=conditions,
        risky_foods=risky_foods,
        avg_daily_sugar=avg_daily_sugar,
        avg_daily_sodium=avg_daily_sodium,
        avg_daily_calories=avg_daily_calories,
    )

    return {
        "health_score":         round(avg_score),
        "avg_risk_score":       avg_score, # Passed as score, mapping 0-100 now.
        "conditions":           conditions,
        "orders_analyzed":      len(orders),
        "unique_foods_scored":  len(seen_food_ids),
        "risky_foods":          sorted(risky_foods, key=lambda x: x["risk_score"]), # Lowest score is highest risk
        "pattern":              pattern,
        "avg_daily": {
            "sugar":    avg_daily_sugar,
            "sodium":   avg_daily_sodium,
            "calories": avg_daily_calories,
        },
        "advice":    advice,
    }
