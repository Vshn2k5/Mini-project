# HealthBite System Architecture

Based on the project's deep technical documentation, here is the full system architecture diagram for HealthBite, utilizing a decoupled frontend-backend pattern and incorporating a specialized multi-layer AI Engine.

## System Architecture Diagram

```mermaid
graph TD
    classDef frontend fill:#3498db,stroke:#2980b9,color:white;
    classDef backend fill:#2ecc71,stroke:#27ae60,color:white;
    classDef database fill:#f39c12,stroke:#d35400,color:white;
    classDef ai fill:#9b59b6,stroke:#8e44ad,color:white;
    classDef external fill:#e74c3c,stroke:#c0392b,color:white;

    %% Client Layer
    subgraph Client [Frontend - Vanilla JavaScript]
        UI[User & Admin Portals<br/>HTML/CSS/JS]
        State[(LocalStorage<br/>JWT/Cart)]
        Visuals[Analytics Dashboard<br/>Chart.js]
    end
    class Client,UI,State,Visuals frontend;

    %% Application Layer
    subgraph Application [Backend - FastAPI & Python 3.10+]
        API[RESTful Endpoints<br/>CORS Middleware]
        AuthLogic[Security<br/>JWT & Bcrypt]
        Schemas[Data Validation<br/>Pydantic]
        ORM[Database Queries<br/>SQLAlchemy]
    end
    class Application,API,AuthLogic,Schemas,ORM backend;

    %% Persistence Layer
    subgraph Data [Data Persistence]
        DB[(canteen.db<br/>SQLite 3)]
    end
    class Data,DB database;

    %% Intelligence Layer
    subgraph Intelligence [AI Engine]
        Rules[Deterministic Engine<br/>Health Risk Scoring]
        ML[Machine Learning Engine<br/>Random Forest]
        RAG[NLP/RAG Chatbot<br/>Intent Classifier]
    end
    class Intelligence,Rules,ML,RAG ai;
    
    Groq[Groq Cloud LLM<br/>LLaMA 3.1 8B]
    class Groq external;

    %% Connections
    UI -- "HTTP/HTTPS REST APIs (JSON)" --> API
    API --> AuthLogic
    API --> Schemas
    Schemas --> ORM
    ORM -- "Object Relational Mapping" --> DB
    
    %% AI Interactions
    API -- "Food Items / Health Profile" --> Rules
    API -- "Extract Features" --> ML
    Rules -- "Hard Constraints / Score" --> ML
    API -- "User Chat Queries" --> RAG
    Rules -- "Scores & Rationale Context" --> RAG
    RAG -- "Context-Injected Prompts" --> Groq
    Groq -- "Strict Text Response" --> RAG
    
```

## Component Breakdown

1. **Frontend**: Lightweight vanilla implementation ensuring maximal speed. Uses HTTP requests to communicate with the application layer and `localStorage` to retain session keys locally without holding state on the central server.
2. **Backend**: Python-powered FastAPI routing application served by Uvicorn. Validates requests precisely with Pydantic and utilizes SQLAlchemy for abstracted database interactions.
3. **Data**: A local and lightweight SQLite 3 database keeping track of users, biometric profiles, menu catalog, historical orders, and logging AI prediction accuracy.
4. **AI Engine**: A hybrid system blending explicit clinical safety thresholds (deterministic python scripts) with a probabilistic Scikit-Learn Random Forest recommendation model. It employs Retrieval-Augmented Generation to fetch safety metrics into a hidden prompt format, communicating with the Groq Cloud LLaMA model to reply conversationally yet securely.
