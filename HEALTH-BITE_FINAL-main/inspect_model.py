import joblib
import os

model_path = r'h:\HEALTH-BITE_FINAL-!!!!!!!!!!!\HEALTH-BITE_FINAL-main\backend\models\intent_classifier.pkl'

try:
    model = joblib.load(model_path)
    print(f"Model Type: {type(model)}")
    
    if hasattr(model, 'classes_'):
        print(f"Classes (Intents) detected: {model.classes_}")
    else:
        print("No classes_ attribute found. Printing model details:")
        print(model)
        
except Exception as e:
    print(f"Error loading model: {e}")
