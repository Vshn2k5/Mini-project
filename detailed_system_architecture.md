# Deep Dive: HealthBite System Architecture

Here is a deeper technical breakdown of the HealthBite Smart Canteen ecosystem, zooming into the specific data flows and modular layers of the application.

## 1. AI Food Recommendation Pipeline (Sequence Diagram)

This sequence diagram illustrates the complex flow of a user asking for food recommendations. It highlights the orchestration between the Fast API backend and the multi-layered AI Engine.

```mermaid
sequenceDiagram
    participant User as Frontend (User API)
    participant Auth as Backend (FastAPI Auth)
    participant DB as SQLite (Models)
    participant Engine as AI Recommendation Engine
    participant Scorer as Rule-Based Scorer
    participant ML as Random Forest (food_recommender.pkl)
    
    User->>Auth: POST /api/recommend-food (JWT)
    Auth->>DB: Verify User ID & Fetch Health Profile
    DB-->>Auth: User Profile Object
    Auth->>DB: Fetch Available Menu Items
    DB-->>Auth: Menu Items Array
    
    Auth->>Engine: Send Menu & User Profile
    
    note over Engine: 1. Hard Pruning & Deterministic Checks
    loop For each item in Menu
        Engine->>Scorer: Evaluate Allegies & Constraints
        Scorer-->>Engine: Strict Penalty Score
    end
    
    note over Engine: 2. Nutritional Calculus & Predictions
    Engine->>Engine: Compute Nutritional Distance (Macros)
    Engine->>ML: Feed Encoded User Features
    ML-->>Engine: Probability Distribution
    
    note over Engine: 3. Ensemble Ranking Synthesis
    Engine->>Engine: Fuse Clinical Score (75%) + ML (25%)
    
    Engine-->>Auth: Final Ranked Top 5 Foods + Expalainable AI Reasons
    
    Auth->>DB: Quiet Log to ai_recommendation_logs
    Auth-->>User: 200 OK (JSON Payload)
```

## 2. Hybrid NLP & RAG Chatbot Pipeline

This diagram shows how HealthBite ensures zero-hallucination medical advice by using a RAG (Retrieval-Augmented Generation) pipeline before querying the LLaMA model from Groq Cloud.

```mermaid
flowchart TD
    classDef frontend fill:#3498db,stroke:#2980b9,color:white;
    classDef backend fill:#2ecc71,stroke:#27ae60,color:white;
    classDef llm fill:#e74c3c,stroke:#c0392b,color:white;
    
    User(["User Input: 'Can I eat chocolate cake?'"]) --> Classifier
    
    subgraph CoreBackend [Backend / AI Engine]
        Classifier{"Intent Classifier"}
        
        Classifier -- "intent: recommendation" --> EntityExtraction["Extract Entities<br/>(e.g., 'chocolate cake')"]
        Classifier -- "intent: greeting/chat" --> GeneralPrompt["Standard Chat Prompt"]
        
        EntityExtraction --> ContextGathering{"Context Engine"}
        
        %% Score processing
        ContextGathering --> |Query item against profile| RunScorer["Clinical Scorer + ML"]
        RunScorer --> |Calculates| Penalties["Result: High Sugar (Score deducted)"]
        Penalties --> Injector["Context Injector (Hidden Prompt)"]
        
        %% Rejoin
        GeneralPrompt --> Injector
    end
    class CoreBackend backend;

    Injector -- "Context + Rules + Queries" --> GroqCloud

    subgraph External [Groq Cloud Framework]
        GroqCloud["LLaMA 3.1 8B API"]
    end
    class GroqCloud llm;

    GroqCloud -- "Strict JSON/Markdown Reply" --> BackendFormatter["Response Formatter"]
    BackendFormatter --> UI["Frontend UI"]
    class User,UI frontend;
```

## 3. Infrastructure & Component Map

Unlike the broad overview, this map zooms into the specific libraries, directories, and structural responsibilities of the backend ecosystem.

```mermaid
graph LR
    %% Application Layer
    A1[CORS Middleware]
    A2[Static File Server]
    R1[routers/auth.py]
    R2[routers/menu.py]
    R3[routers/ai_endpoints.py]
    
    A1 --> R1 & R2 & R3
    A2 --> FrontEndFiles["/frontend/*.html & js"]

    %% Data Layer
    S1["schemas.py (JSON val.)"]
    M1["models.py (SQLAlchemy)"]
    DB[(canteen.db)]
    
    R1 --> S1
    R2 --> S1
    R3 --> S1
    S1 --> M1
    M1 <--> DB

    %% AI Layer
    E1[health_scoring.py]
    E2[risk_prediction.py]
    ML1[recommendation_engine.py]
    ML2[train_model.py]
    RF[food_recommender.pkl]
    NLP[chatbot_engine.py]
    
    R3 -.-> ML1
    R3 -.-> NLP
    ML1 --> E1 & E2 & RF
    RF <-.-> ML2
```

### Deep Dive Explanations
*   **Explainable AI (XAI)**: When the Random Forest model and Clinical Scorer evaluate a food item, they don't just return a boolean `True/False` or a raw percentage match. They generate strings justifying the penalty (e.g., "(High Sugar)"). The system guarantees the user knows *why* food was rejected. 
*   **Ensemble Weighting Mechanism**: In the backend's recommendation engine, the final rank prioritizes clinical math over pure ML averages entirely. A 75% focus is given to strict health threshold calculations (`health_scoring.py`) versus the 25% focus on statistical popularity among similar users predicted by `food_recommender.pkl`. This is a hard guardrail.
*   **Role-Based Security Hooks**: By decrypting JWTs on every route payload locally, both the `backend/auth.py` router *and* the physical frontend UI panels (like `frontend/admin/script.js`) can simultaneously check roles (e.g., preventing a non-admin from visualizing the `ai_recommendation_logs` board).
