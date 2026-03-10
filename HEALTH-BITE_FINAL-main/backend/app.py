"""
HealthBite Smart Canteen - Main Application Entry Point
========================================================
FastAPI backend server that powers the Smart Canteen system.
Serves both the API endpoints and the frontend static files.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base, get_db
import models  # MUST import models before create_all so all tables are registered
from models import FoodItem, AiRecommendationLog
from schemas import RecommendationRequest, RecommendationResponse
from ai_engine.recommendation_engine import engine as rec_engine
import os
from sqlalchemy.orm import Session

# Create all database tables
Base.metadata.create_all(bind=engine)

# Run safe column migrations for existing tables (ALTER TABLE if column missing)
def _run_migrations():
    """Add any missing columns without breaking existing deployments."""
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(engine)
    with engine.connect() as conn:
        # health_profiles: add weekly_budget if missing
        hp_cols = [c['name'] for c in inspector.get_columns('health_profiles')]
        if 'weekly_budget' not in hp_cols:
            conn.execute(text('ALTER TABLE health_profiles ADD COLUMN weekly_budget REAL DEFAULT 500.0'))
            conn.commit()
            print("Migration: added 'weekly_budget' to health_profiles")

        # food_items: add allergen columns if missing
        fi_cols = [c['name'] for c in inspector.get_columns('food_items')]
        allergen_migrations = [
            ('nut_allergy',     'INTEGER DEFAULT 0'),
            ('milk_allergy',    'INTEGER DEFAULT 0'),
            ('seafood_allergy', 'INTEGER DEFAULT 0'),
            ('gluten_allergy',  'INTEGER DEFAULT 0'),
            ('soy_allergy',     'INTEGER DEFAULT 0'),
        ]
        for col_name, col_def in allergen_migrations:
            if col_name not in fi_cols:
                conn.execute(text(f'ALTER TABLE food_items ADD COLUMN {col_name} {col_def}'))
                conn.commit()
                print(f"Migration: added '{col_name}' to food_items")
        if 'ingredients' not in fi_cols:
            conn.execute(text("ALTER TABLE food_items ADD COLUMN ingredients TEXT DEFAULT ''"))
            conn.commit()
            print("Migration: added 'ingredients' to food_items")

        # ── MULTI-CANTEEN MIGRATIONS ──────────────────────────────────────
        inspector = sa_inspect(engine)

        # Add canteen_id to users/food_items/orders if missing
        for tbl in ['users', 'food_items', 'orders']:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            if 'canteen_id' not in cols:
                conn.execute(text(f'ALTER TABLE {tbl} ADD COLUMN canteen_id INTEGER'))
                conn.commit()
                print(f"Migration: added 'canteen_id' to {tbl}")
                try:
                    conn.execute(text(f'CREATE INDEX IF NOT EXISTS idx_{tbl}_canteen ON {tbl}(canteen_id)'))
                    conn.commit()
                except Exception:
                    pass

        # Seed default canteen if none exists
        cnt = conn.execute(text('SELECT COUNT(*) FROM canteens')).scalar()
        if cnt == 0:
            conn.execute(text(
                "INSERT INTO canteens (canteen_name, institution_name, canteen_code, created_at) "
                "VALUES ('System Canteen', 'HealthBite System', 'SYS000', datetime('now'))"
            ))
            conn.commit()
            print("Migration: seeded default canteen (SYS000)")

        # Backfill existing rows with NULL canteen_id
        default_id = conn.execute(text("SELECT id FROM canteens WHERE canteen_code = 'SYS000'")).scalar()
        if default_id:
            for tbl in ['users', 'food_items', 'orders']:
                updated = conn.execute(text(
                    f'UPDATE {tbl} SET canteen_id = :cid WHERE canteen_id IS NULL'
                ), {"cid": default_id}).rowcount
                if updated > 0:
                    conn.commit()
                    print(f"Migration: backfilled {updated} rows in {tbl} with default canteen_id={default_id}")

_run_migrations()


# Initialize FastAPI application
app = FastAPI(
    title="HealthBite Smart Canteen",
    description="AI-Powered Health-Aware Canteen System",
    version="2.0.0"
)


# CORS Middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Import and Register Routers ---
from auth import router as auth_router
import health
import menu
from chatbot import router as chatbot_router
from analytics import router as analytics_router
from routes import (
    admin_dashboard,
    admin_foods,
    admin_inventory,
    admin_orders,
    admin_users,
    admin_ai,
    admin_analytics_routes,
)

app.include_router(auth_router)
app.include_router(health.router)
app.include_router(menu.router)
app.include_router(chatbot_router)
app.include_router(analytics_router)

# Admin routes
app.include_router(admin_dashboard.router)
app.include_router(admin_foods.router)
app.include_router(admin_inventory.router)
app.include_router(admin_orders.router)
app.include_router(admin_users.router)
app.include_router(admin_analytics_routes.router)
app.include_router(admin_ai.router)


# --- ML Recommendation Endpoint ---
# NOTE: This must be registered BEFORE the catch-all static file route below,
#       otherwise FastAPI would intercept the POST as a file request.
from dependencies import get_current_user
@app.post("/api/recommend-food", response_model=RecommendationResponse)
def get_ml_recommendation(
    request: RecommendationRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    ML-Powered hybrid recommendation endpoint.
    Retrieves ONLY available food items from DB and ranks them using the hybrid engine.
    """
    # 1. Fetch ONLY available food items from DB (CHECK 1 & CHECK 8)
    foods = db.query(FoodItem).filter(
        FoodItem.is_available == True,
        FoodItem.canteen_id == current_user.canteen_id
    ).all()

    # Convert SQLAlchemy objects to dicts for the engine (includes allergen fields)
    menu_list = [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "calories": f.calories,
            "protein": f.protein,
            "carbs": f.carbs,
            "fat": f.fat,
            "sugar": f.sugar,
            "sodium": f.sodium,
            "dietary_type": f.dietary_type,
            # Allergen flags
            "nut_allergy":     getattr(f, "nut_allergy", False) or False,
            "milk_allergy":    getattr(f, "milk_allergy", False) or False,
            "seafood_allergy": getattr(f, "seafood_allergy", False) or False,
            "gluten_allergy":  getattr(f, "gluten_allergy", False) or False,
            "soy_allergy":     getattr(f, "soy_allergy", False) or False,
        }
        for f in foods
    ]

    # 2. Run hybrid ML recommendation
    user_profile = request.dict()
    recommendations, error = rec_engine.recommend_food(user_profile, menu_list)

    if error:
        raise HTTPException(status_code=400, detail=error)

    # Log recommendations to DB for real analytics
    try:
        user_risk = "Low"
        if user_profile.get("diabetes_status", "").lower() == "high" or user_profile.get("bp_status", "").lower() == "high":
            user_risk = "High"
        elif user_profile.get("diabetes_status", "").lower() == "moderate" or user_profile.get("bp_status", "").lower() == "elevated":
            user_risk = "Moderate"
            
        for r in recommendations[:5]:  # Log top 5
            log_entry = AiRecommendationLog(
                user_id=current_user.id,
                canteen_id=current_user.canteen_id,
                food_id=r["food"]["id"],
                food_name=r["food"]["name"],
                food_category=r["food"]["category"],
                user_risk=user_risk,
                reason=r.get("explanation", "Recommended based on profile and menu nutritional balance."),
                confidence=float(r.get("match_pct", 0)),
                match_score=f"{r.get('health_score', 75)}%",
                user_action="No Response"
            )
            db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to save AI logs: {e}")

    # 3. Format response with food names, health scores, and explanations
    return {
        "recommended_food": [r["food"]["name"] for r in recommendations],
        "match_details": [
            {
                "food_name":     r["food"]["name"],
                "match_score":   r["match_pct"],
                "health_score":  r.get("health_score", 75),
                "overall_label": r.get("overall_label", "SAFE"),
                "diabetes_risk": r.get("diabetes_risk", "SAFE"),
                "hbp_risk":      r.get("hbp_risk", "SAFE"),
                "allergy_risk":  r.get("allergy_risk", "SAFE"),
                "triggered_allergens": r.get("triggered_allergens", []),
                "explanation":   r.get("explanation", ""),
                "reason":        "Top ML & Nutritional match" if r.get("ml_match") else "High nutritional alignment"
            }
            for r in recommendations
        ]
    }


# --- Serve Frontend Static Files ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# Mount static files (CSS, JS, images, etc.)
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
async def serve_index():
    """Serve the main login/landing page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{filename}.html")
async def serve_html(filename: str):
    """Serve any HTML page from the frontend directory"""
    filepath = os.path.join(FRONTEND_DIR, f"{filename}.html")
    if os.path.exists(filepath):
        return FileResponse(filepath)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{filename}.css")
async def serve_css(filename: str):
    """Serve CSS files"""
    filepath = os.path.join(FRONTEND_DIR, f"{filename}.css")
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="text/css")


@app.get("/{filename}.js")
async def serve_js(filename: str):
    """Serve JavaScript files"""
    filepath = os.path.join(FRONTEND_DIR, f"{filename}.js")
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/javascript")


@app.get("/images/{filename}")
async def serve_image(filename: str):
    """Serve image files"""
    filepath = os.path.join(FRONTEND_DIR, "images", filename)
    if os.path.exists(filepath):
        return FileResponse(filepath)


@app.get("/{full_path:path}")
async def serve_nested(full_path: str):
    """Catch-all: serve any file from the frontend directory (supports nested paths)"""
    filepath = os.path.join(FRONTEND_DIR, full_path)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        # Determine media type
        if filepath.endswith(".css"):
            return FileResponse(filepath, media_type="text/css")
        elif filepath.endswith(".js"):
            return FileResponse(filepath, media_type="application/javascript")
        elif filepath.endswith(".html"):
            return FileResponse(filepath, media_type="text/html")
        return FileResponse(filepath)
    # Fallback to index
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# Print all registered routes for debugging
print("\n--- REGISTERED ROUTES ---")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"{route.path} [{', '.join(route.methods) if hasattr(route, 'methods') else 'N/A'}]")
print("------------------------\n")


# --- Start Server ---
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  HEALTHBITE SMART CANTEEN SERVER")
    print("  Starting on http://0.0.0.0:8080")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8080)
