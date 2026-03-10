from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class RoleEnum(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class DiseaseEnum(str, Enum):
    DIABETES = "Diabetes"
    HYPERTENSION = "Hypertension"
    OBESITY = "Obesity"
    ANEMIA = "Anemia"
    HEART_DISEASE = "Heart Disease"
    NONE = "None"


# User schemas
class UserBase(BaseModel):
    name: str
    email: str


class UserCreate(UserBase):
    password: str
    confirm_password: str
    role: RoleEnum
    admin_key: Optional[str] = None
    # Multi-canteen fields
    canteen_code: Optional[str] = None        # Required for USER registration
    canteen_name: Optional[str] = None        # Required for ADMIN registration
    institution_name: Optional[str] = None    # Required for ADMIN registration


class UserResponse(UserBase):
    id: int
    role: str
    disabled: int

    class Config:
        from_attributes = True


# Auth schemas
class LoginRequest(BaseModel):
    email: str
    password: str
    role: RoleEnum
    admin_key: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyIdentityRequest(BaseModel):
    email: str
    name: str


class DirectResetPasswordRequest(BaseModel):
    email: str
    new_password: str


class LoginResponse(BaseModel):
    message: str
    email: str
    name: str
    role: str
    token: str
    profile_completed: bool = False
    onboarding_step: int = 0
    canteen_id: Optional[int] = None
    canteen_name: Optional[str] = None
    canteen_code: Optional[str] = None


# Health profile schemas
class HealthProfileBase(BaseModel):
    age: int
    height_cm: float
    weight_kg: float
    gender: Optional[str] = "Other"
    disease: List[str] = []
    dietary_preference: str = "Veg"
    severity: Optional[dict] = {}
    health_values: Optional[dict] = {}
    allergies: Optional[List[dict]] = [] # [{"name": "Nuts", "severity": "Severe"}]


class HealthProfileCreate(HealthProfileBase):
    bmi: Optional[float] = None


class HealthStep1(BaseModel):
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    dietary_preference: str


class HealthStep2(BaseModel):
    disease: List[str]
    severity: dict
    health_values: dict
    allergies: List[dict]


class HealthReportResponse(BaseModel):
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    bmi: float
    bmi_category: str
    disease: List[str]
    allergies: List[dict]
    risk_score: int
    risk_level: str
    recommendations: List[str]


class HealthProfileResponse(HealthProfileBase):
    id: int
    user_id: int
    name: Optional[str] = None
    bmi: float
    bmi_category: str
    diabetes_status: str
    bp_status: str
    cholesterol_status: str
    risk_score: int
    risk_level: str

    class Config:
        from_attributes = True


# Order schemas
class OrderItemInput(BaseModel):
    food_id: int
    quantity: int = 1

class OrderCreate(BaseModel):
    items: List[OrderItemInput]
    total_price: float
    total_calories: float
    total_sugar: float
    total_sodium: float
    payment_method: str = "Cash"

class OrderItemResponse(BaseModel):
    food_id: Optional[int] = None
    food_name: str
    qty: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True

class OrderResponse(OrderCreate):
    id: int
    user_id: int
    items: Optional[str] = None
    order_items: List[OrderItemResponse] = []
    created_at: str

    class Config:
        from_attributes = True


# Daily Log schemas
class DailyLogCreate(BaseModel):
    water_intake_ml: Optional[int] = 0
    steps: Optional[int] = 0
    mood: Optional[str] = "Neutral"


class DailyLogResponse(DailyLogCreate):
    id: int
    user_id: int
    date: str

    class Config:
        from_attributes = True


# Recommendation schemas
class RecommendationRequest(BaseModel):
    age: int
    gender: str
    bmi: float
    activity_level: Optional[str] = "medium"
    diet_type: str
    goal: str
    health_condition: str
    calorie_target: int
    protein_requirement: int
    carbs_limit: int
    fat_limit: int

class RecommendationResponse(BaseModel):
    recommended_food: List[str]
    match_details: List[dict]
