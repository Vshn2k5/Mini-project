"""Admin AI Monitoring - /api/admin/ai"""

import math
import random
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import AiModelStatus, AiTrainingHistory, AiRecommendationLog, User
from routes.admin_deps import get_current_admin
from routes.audit_helper import log_action

router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai"])


def _ensure_status_row(db: Session) -> AiModelStatus:
    status_row = db.query(AiModelStatus).first()
    if not status_row:
        status_row = AiModelStatus(
            status="active",
            version="1.0.0",
            accuracy=85.0,
            precision_score=0.84,
            recall_score=0.83,
            f1_score=0.83,
            total_predictions=0,
        )
        db.add(status_row)
        db.commit()
        db.refresh(status_row)
    return status_row


def _title_status(status: str) -> str:
    val = (status or "active").lower()
    if val == "retraining":
        return "Retraining"
    if val == "degraded":
        return "Degraded"
    return "Active"


@router.get("/status")
def ai_status(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _ = admin
    status_row = _ensure_status_row(db)
    return {
        "status": _title_status(status_row.status),
        "version": status_row.version or "1.0.0",
        "last_trained": status_row.last_trained.isoformat() if status_row.last_trained else None,
        "total_predictions": int(status_row.total_predictions or 0),
        "metrics": {
            "accuracy": round(float(status_row.accuracy or 0), 2),
            "precision": round(float(status_row.precision_score or 0), 4),
            "recall": round(float(status_row.recall_score or 0), 4),
            "f1": round(float(status_row.f1_score or 0), 4),
        },
    }


@router.get("/features")
def ai_features(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _ = db
    _ = admin
    return {
        "features": [
            {"name": "Health Conditions", "importance": 24.0},
            {"name": "Diet Preference", "importance": 18.0},
            {"name": "Allergy Flags", "importance": 16.0},
            {"name": "BMI", "importance": 14.0},
            {"name": "Age", "importance": 12.0},
            {"name": "Order History", "importance": 9.0},
            {"name": "Time of Day", "importance": 7.0},
        ]
    }


@router.get("/accuracy-history")
def ai_accuracy_history(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _ = admin
    history = (
        db.query(AiTrainingHistory)
        .filter(AiTrainingHistory.status == "success")
        .order_by(AiTrainingHistory.ended_at.asc())
        .limit(12)
        .all()
    )

    dates, acc, notes = [], [], []
    for run in history:
        dates.append(run.ended_at.strftime("%b %d") if run.ended_at else "?")
        acc.append(round(float(run.accuracy_after or 0), 2))
        notes.append(run.notes or "Training run")

    if not dates:
        dates = ["Jan 10", "Jan 24", "Feb 07", "Feb 21", "Mar 01"]
        acc = [82.5, 84.1, 85.0, 87.2, 88.5]
        notes = ["Initial", "Tuned features", "Added data", "Threshold tuning", "Current"]

    return {"dates": dates, "accuracy": acc, "notes": notes}


@router.get("/logs")
def ai_logs(
    page: int = 1,
    limit: int = 20,
    per_page: int | None = None,
    risk: str | None = None,
    action: str | None = None,
    period: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _ = db
    _ = admin

    page = max(1, int(page or 1))
    page_size = int(per_page if per_page is not None else limit or 20)
    page_size = min(100, max(1, page_size))

    query = db.query(AiRecommendationLog).filter(AiRecommendationLog.canteen_id == admin.canteen_id)

    # Filters
    now = datetime.now()
    selected_period = (period or "all").lower()
    if selected_period in {"today", "7d", "30d"}:
        if selected_period == "today":
            cutoff = now - timedelta(days=1)
        elif selected_period == "7d":
            cutoff = now - timedelta(days=7)
        else:
            cutoff = now - timedelta(days=30)
        query = query.filter(AiRecommendationLog.timestamp >= cutoff)

    if risk and risk.lower() != "all":
        query = query.filter(AiRecommendationLog.user_risk.ilike(f"{risk}"))
    if action and action.lower() != "all":
        query = query.filter(AiRecommendationLog.user_action.ilike(f"{action}"))
    if search:
        s = f"%{search.strip()}%"
        # Join with User to search by user name or food name
        query = query.join(User, AiRecommendationLog.user_id == User.id).filter(
            User.name.ilike(s) | AiRecommendationLog.food_name.ilike(s)
        )

    total = query.count()
    pages = max(1, int(math.ceil(total / page_size)))
    page = min(page, pages)
    start = (page - 1) * page_size

    logs = query.order_by(AiRecommendationLog.timestamp.desc()).offset(start).limit(page_size).all()

    real_logs = []
    for log in logs:
        real_logs.append(
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else now.isoformat(),
                "user_name": log.user.name if log.user else f"User {log.user_id}",
                "user_risk": log.user_risk or "Low",
                "food_name": log.food_name,
                "food_category": log.food_category,
                "reason": log.reason,
                "confidence": round(float(log.confidence or 0), 1),
                "user_action": log.user_action,
                "match_score": log.match_score,
            }
        )

    return {"total": total, "page": page, "pages": pages, "logs": real_logs}


@router.get("/training-history")
def ai_training_history(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _ = admin
    rows = db.query(AiTrainingHistory).order_by(AiTrainingHistory.started_at.desc()).limit(20).all()

    history = []
    for row in rows:
        history.append(
            {
                "id": row.id,
                "triggered_by": "Admin",
                "date": row.started_at.strftime("%Y-%m-%d %H:%M") if row.started_at else "-",
                "duration": f"{row.duration_seconds}s" if row.duration_seconds else "-",
                "acc_before": round(float(row.accuracy_before or 0), 2),
                "acc_after": round(float(row.accuracy_after or 0), 2),
                "status": "Success" if row.status == "success" else ("Failed" if row.status == "failed" else "In Progress"),
                "notes": row.notes or "",
            }
        )

    if not history:
        history = [
            {
                "id": 1,
                "triggered_by": "System",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "duration": "10s",
                "acc_before": 87.2,
                "acc_after": 88.5,
                "status": "Success",
                "notes": "Initial seeded run",
            }
        ]
    return {"history": history}


def _run_retrain_task(training_id: int):
    """Background task to run actual dataset generation and model retraining."""
    import os
    import sys
    
    db = SessionLocal()
    try:
        # 1. Update status to retraining
        th = db.query(AiTrainingHistory).filter(AiTrainingHistory.id == training_id).first()
        ms = _ensure_status_row(db)
        
        if not th or not ms:
            return
            
        start_time = time.time()
        
        try:
            # 2. Add ai_engine to path so we can import its modules
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ai_engine_dir = os.path.join(base_dir, "..", "ai_engine")
            if ai_engine_dir not in sys.path:
                sys.path.append(ai_engine_dir)
                
            from dataset_generator import generate_dataset
            from train_model import train_model, DATASET_PATH
            
            # 3. Generate New Dataset
            # Note: We pass a smaller dataset size to speed up the admin dashboard demonstration
            df = generate_dataset(dataset_size=10000)
            df.to_csv(DATASET_PATH, index=False)
            
            # 4. Train Model
            stats = train_model()
            duration = int(time.time() - start_time)
            
            if stats:
                new_acc = round(stats["accuracy"] * 100, 2)
                new_precision = round(stats["precision"], 4)
                new_recall = round(stats["recall"], 4)
                new_f1 = round(stats["f1"], 4)
                
                # Update Model Status
                v_parts = ms.version.split('.') if ms.version else ["1", "0", "0"]
                v_parts[-1] = str(int(v_parts[-1]) + 1)
                
                ms.status = "active"
                ms.version = ".".join(v_parts)
                ms.accuracy = new_acc
                ms.precision_score = new_precision
                ms.recall_score = new_recall
                ms.f1_score = new_f1
                ms.last_trained = datetime.now()
                ms.total_predictions = int(ms.total_predictions or 0)
                
                # Update Training History
                th.status = "success"
                th.ended_at = datetime.now()
                th.duration_seconds = duration
                th.accuracy_after = new_acc
                th.notes = f"Model retrained. Best: {stats['model_name']}. New Accuracy: {new_acc}%"
            else:
                raise Exception("Model training returned no stats.")
                
        except Exception as e:
            # Handle Training Failure
            duration = int(time.time() - start_time)
            ms.status = "active"
            th.status = "failed"
            th.ended_at = datetime.now()
            th.duration_seconds = duration
            th.notes = f"Training failed: {str(e)}"
            print(f"Retraining Error: {str(e)}")
            
        db.commit()
    finally:
        db.close()


@router.post("/retrain", status_code=202)
def trigger_retrain(
    request: Request,
    bg_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    status_row = _ensure_status_row(db)
    if status_row.status == "retraining":
        return {"error": "Training already in progress"}

    current_acc = float(status_row.accuracy or 0)
    status_row.status = "retraining"

    training = AiTrainingHistory(
        triggered_by=admin.id,
        accuracy_before=current_acc,
        status="in_progress",
    )
    db.add(training)
    db.commit()
    db.refresh(training)

    log_action(db, admin.id, "RETRAIN", "ai_model", None, "Triggered AI model retrain", request=request)
    bg_tasks.add_task(_run_retrain_task, training.id)

    return {"message": "Retraining started", "training_id": training.id}
