# 🧬 HealthBite Deep Technical Architecture & Algorithms Report

This document provides an exhaustive breakdown of every technology, model, and algorithm actively running within the HealthBite Smart Canteen ecosystem. It defines exactly what each component does, where it resides, how it functions internally, and how it connects to the rest of the system.

---

## 🏗️ 1. Overall System Architecture

HealthBite follows a modern decoupling pattern. The backend acts as an intelligent API layer handling data storage, authentication, and core business/AI logic, while the frontend is a lightweight, static client that renders the UI and communicates strictly via RESTful endpoints.

- **Communication Protocol**: HTTP/HTTPS REST APIs.
- **Data Exchange Format**: JSON.
- **State Management**: Stateless backend. Sessions are managed entirely on the client side via JWT (JSON Web Tokens) stored in browser `localStorage`.

---

## 🧠 2. Backend & AI Engine 

The backend is completely modularized, blending traditional CRUD endpoints with a sophisticated multi-layered AI Engine.

### 2.1 Core Backend Technologies
*   **Language**: Python 3.10+
*   **Framework**: **FastAPI** ([backend/app.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/app.py)). Chosen for its superior asynchronous performance (via ASGI) and automatic OpenAPI (Swagger) documentation. It handles all routing, CORS middleware, and static file serving.
*   **Database Engine**: **SQLite 3** (`backend/canteen.db`). A lightweight disk-based database.
*   **ORM (Object-Relational Mapping)**: **SQLAlchemy** (`backend/models.py`). Abstracts SQL queries into Python objects. Manages the schemas for Users, Food Items, Health Profiles, Orders, Canteens, and AI Recommendation Logs.
*   **Data Validation**: **Pydantic** (`backend/schemas.py`). Ensures that all incoming JSON requests and outgoing responses strictly adhere to predefined data types, preventing malformed data errors.
*   **Authentication**: **JWT (JSON Web Tokens)** & **Bcrypt** (`backend/auth.py`). Passwords are mathematically hashed using Bcrypt before storage. Logins return a cryptographically signed JWT used to authorize subsequent requests.
*   **Server**: **Uvicorn**. The ASGI web server implementation used to run the FastAPI application.

### 2.2 The AI Engine (`backend/ai_engine/`)
The intelligence of HealthBite is broken into deterministic rule engines, probabilistic machine learning models, and Large Language Models (LLMs).

#### A. Deterministic Health Risk Scoring & Analysis ([health_scoring.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/health_scoring.py) & [risk_prediction.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/risk_prediction.py))
*   **What it is**: A clinical rule-based algorithm that acts as a strict, non-negotiable safety net.
*   **How it works**: It evaluates a specific food item against a user's health profile (Conditions: Diabetes, Hypertension, Obesity, Allergies). 
    *   It starts with a base score of 100.
    *   It applies mathematical penalties based on clinical thresholds. For example, if a diabetic user requests food with > 30g sugar, it deducts 50 points and flags it "SEVERE".
    *   Allergies triggered result in an immediate "DANGER" flag and a 50+ point deduction. 
    *   It also analyzes longitudinal patterns (e.g., avg daily sodium across past week's orders) to project a 30-day health risk increase percentage.
*   **Where it operates**: Used universally when a user browses the menu or when the chatbot evaluates a specific food request.

#### B. Machine Learning Recommendation Engine ([recommendation_engine.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/recommendation_engine.py) & [train_model.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/train_model.py))
*   **Technology / Model**: **Random Forest Classifier** (`scikit-learn`). Evaluated against Gaussian Naive Bayes and Decision Trees during training, Random Forest was selected for the highest F1 Score and Accuracy. 
*   **What it does**: Predicts the optimal food choice for a user out of the entire menu.
*   **How it works**:
    1.  **Diet/Health Filter (Hard Pruning)**: Eliminates foods that violate hard constraints (e.g., Meat for Vegans, high-sugar for Diabetics).
    2.  **Explainable Scoring**: Assigns a deterministic health score (using the algorithm in A).
    3.  **Nutritional Distance**: Computes a continuous mathematical distance between the user's macro goals (calories, protein, carbs) and the food's macros.
    4.  **ML Boosting**: The user's features (12 features including age, BMI, activity level, health conditions) are encoded and fed to the [food_recommender.pkl](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/food_recommender.pkl) Random Forest model. The model outputs a probability distribution across all menu items.
    5.  **Ensemble Ranking**: The final ranking combines the Clinical Score (75% weight) and the ML Probability (25% weight). The clinical score strictly gates the ML from suggesting unsafe but "statistically popular" foods.

#### C. Natural Language Processing (NLP) & RAG Chatbot ([chatbot_engine.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/chatbot_engine.py))
*   **Technology**: Hybrid Intent Classification + RAG (Retrieval-Augmented Generation) powered by **Groq Cloud** running **LLaMA 3.1 8B**.
*   **Intent Classifier**: A custom classifier evaluates the user's text message to categorize their goal (`greeting`, [recommendation](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/chatbot_engine.py#441-481), `reasoning`, `general_chat`, etc.).
*   **Entity Memory**: The engine remembers the "last discussed food item" natively, allowing users to ask follow-up pronouns like "why is *it* bad?".
*   **RAG Pipeline**: 
    1.  User asks: *"Can I eat the chocolate cake?"*
    2.  The engine extracts "chocolate cake". 
    3.  It runs the Clinical Scoring and ML model on chocolate cake against the user's profile.
    4.  It constructs a **hidden prompt** (Context) injecting the calculated scores, the reasons for penalties (e.g., "High Sugar"), and database stats.
    5.  It sends this strict context to the Groq LLaMA 3.1 API.
    6.  The LLM formats the response conversationally but is strictly instructed *not to invent medical facts outside of the injected context* (Zero-Hallucination mechanism).

---

## 🖥️ 3. Frontend Architecture

The frontend is a vanilla implementation, intentionally avoiding heavy frameworks (like React or Angular) to maintain blazing fast load times and simple deployment, while utilizing advanced CSS for a premium feel.

### 3.1 Core Frontend Technologies
*   **Languages**: HTML5, Vanilla JavaScript (ES6+), CSS3.
*   **Aesthetics**: Custom Glassmorphism UI (translucent panels, backdrop filters, soft UI elements, gradients).
*   **Icons**: FontAwesome 6.
*   **Charting**: **Chart.js**. Used extensively in the User Analytics dashboard and Admin Analytics to render responsive Bar, Line, and Doughnut charts.

### 3.2 Frontend Components & User Flows

#### User Portal (`/frontend/*.html`)
*   **Authentication Flow** (`index.html`, `register.html`): Handles data entry, API calls to `/api/auth/register` and `/api/auth/login`, and stores the returned JWT.
*   **Health Profile Manager** (`health.html`): Complex form validation capturing biometric data (Height, Weight -> auto-calculates BMI), allergies, and chronic diseases.
*   **Menu & Ordering** (`full-menu.html`, `cart.html`, `payment.html`): Dynamically fetches the menu from `/api/menu/`. Each food item card immediately displays its specific AI Health Safety badge calculated dynamically. Uses `localStorage` to manage the shopping cart state before pushing the final order to the server.
*   **Health Analytics** (`health-analytics.html`): Fetches longitudinal order data. Parses response into Chart.js datasets to visualize average macro-nutrient intake vs targets.
*   **AI Chatbot UI** (`health-assistant.html` & [chatbot.js](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/frontend/chatbot.js)): A persistent or dedicated floating widget mimicking a ChatGPT interface. It renders typing indicators, formats Markdown text (bolding, lists) returned by the Groq LLM, and displays rich "Explanation Cards" (colored insight chips).

#### Admin Portal (`/frontend/admin/*.html`)
A robust CMS (Content Management System) for managing the canteen ecosystem.
*   **Security Mechanism**: On every page load, `script.js` intercepts the request, checks the JWT role payload. If role != `ADMIN`, it hard-redirects to the user dashboard.
*   **Food / Inventory Management**: Interfaces to perform CRUD operations on the SQLite database via FastAPI.
*   **AI Monitor Board**: A specialized admin view that tracks the decisions made by the Recommendation Engine, displaying the confidence metrics of the Random Forest model and tracking which recommendations users actually ordered.

---

## 🔗 4. How Everything Connects (Data Flow)

Here is a step-by-step trace of how the frontend, backend, and AI engines interface during the most complex operation: **Asking for an AI Food Recommendation**.

1.  **Trigger (Frontend)**: User clicks "Recommend Food" in the UI. 
2.  **API Call (Frontend -> Backend)**: The frontend retrieves the user's JWT from `localStorage` and sens a `POST` request to `http://localhost:8080/api/recommend-food`.
3.  **Authentication (Backend)**: FastAPI receives the request. The `get_current_user` dependency decrypts the JWT. If valid, it queries `user_id` from the SQLite database to verify the user exists.
4.  **Data Hydration (Backend)**: The backend queries the user's full Health Profile and the Canteen's currently available Menu items from the database.
5.  **AI Engine Processing (Backend -> AI Engine)**: 
    *   The [recommendation_engine.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/recommendation_engine.py) receives the Menu list and the User Profile.
    *   It filters out lethal allergies (Deterministic Rule).
    *   It calculates Nutritional Distance (Math).
    *   It invokes [health_scoring.py](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/health_scoring.py) to get the Penalty Score. 
    *   It feeds the user profile into the [food_recommender.pkl](file:///c:/Users/Admin/Desktop/HEALTH-BITE_FINAL-Completed/HEALTH-BITE_FINAL-main%20FIXY/HEALTH-BITE_FINAL-main/backend/ai_engine/food_recommender.pkl) (Random Forest) to predict the best class.
    *   It fuses these into a Final Ranked List of top 5 safe foods.
6.  **Analytics Logging (Backend -> DB)**: The backend quietly writes a log of this specific AI recommendation into the `ai_recommendation_logs` database table (for the Admin AI Monitor).
7.  **Response Construction (Backend -> Frontend)**: The backend formats the top 5 foods, their match percentages, and the exact XAI (Explainable AI) string reasons why they were chosen, sending it back as a JSON Payload.
8.  **Render (Frontend)**: The JavaScript parses the JSON and generates DOM elements (Glassmorphism Cards, progress bars, reason chips) to display the highly personalized recommendations to the user.
