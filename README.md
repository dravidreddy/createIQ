# CreatorIQ 🚀

<div align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge" alt="Production Ready" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react" alt="React Platform" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-AI-FF4F00?style=for-the-badge" alt="LangGraph Pipeline" />
</div>

<br />

**CreatorIQ** is a state-of-the-art, full-stack AI-powered content generation platform built for creators. Designed for high fidelity and scale, it utilizes a sophisticated multi-agent LangGraph pipeline to automate the end-to-end process of video script generation, from raw idea discovery to deep research, screenplay structuring, and final pacing optimization.

---

## ✨ Key Features

### 🤖 Multi-Stage AI Pipeline (Driven by LangGraph)
Our complex AI orchestrator drives high-quality outputs using specialized sub-agents:
- **Idea Discovery Agent:** Predicts trending topics by integrating real-time **YouTube Data API** and Tavily web searches.
- **Deep Research Agent:** Verifies facts and gathers deep context dynamically.
- **Script Drafting Agent:** Produces a comprehensive multi-page script from research.
- **Screenplay & Polish Agent:** Restructures pacing, boosts engagement loops, and ensures the content meets strict creator personas.

### 🛡️ Resilient Execution Layer
- **Multi-LLM Fallback Routing:** Automatic fallback cascading across preferred LLMs (Gemini, Claude, OpenAI, Groq) with smart circuit breakers to ensure zero downtime.
- **OutputGuard Validation:** Strict Pydantic tier validation to ensure reliable JSON parsing, preventing hallucinatory data corruption.
- **Budget Enforcers:** Token bucket rate-limiting and budget limiters running securely on **Redis** to ensure LLM usage does not blow past defined tiers.

### 💳 Built-In Monetization
- **Razorpay Integration:** Full end-to-end credit-based monetization. Users purchase packages (Starter, Popular, Pro) via a premium UI, and credits are atomically deducted per pipeline execution.

### ⚡ Real-Time Human-In-The-Loop Streaming
Watch your scripts generate live. Our platform utilizes custom **Server-Sent Events (SSE)** tied tightly to **Redis** for highly responsive token-by-token streaming via a beautiful **React Split-View** interface.

### 🔐 Secure Identity & Auth
Integrated cleanly with **Firebase Authentication**, ensuring secure cookie-propagation, cross-origin persistence, and seamless multi-user workspaces.

---

## 🛠 Tech Stack

**Frontend (Client)**
- **React 18** (Vite / TypeScript)
- **Tailwind CSS** (for rich aesthetics, glassmorphism, responsive designs)
- **Zustand** (Predictable, snappy state management)
- **Firebase Auth** (Client-side native identity)

**Backend (Server Layer)**
- **FastAPI** (High-speed, typed Python routing)
- **LangGraph & LangChain** (AI Orchestration / Graph Engine)
- **Razorpay SDK** (Payment gateway & webhook processing)
- **Firebase Admin SDK** (Token validation, interceptors)

**Databases & Infrastructure**
- **MongoDB Atlas** (Primary transactional database via Beanie ODM)
- **Qdrant Cloud** (Lightning-fast Vector DB / Neural Search for Embeddings)
- **Redis / Upstash** (State caching, streaming memory, token bucket rate limits)

**LLM Landscape**
- Google Gemini (Primary), OpenAI, Anthropic Claude, Groq (Fallbacks).

---

## 🚀 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/en/) 18+
- [Python](https://www.python.org/) 3.10+
- A Firebase Project (with Web & Admin credentials)
- Necessary API Keys for the Generative Services (Gemini, Groq, OpenAI, Tavily)
- MongoDB, Qdrant, and Redis instances.

### 1. Clone & Backend Setup

```bash
git clone https://github.com/yourusername/CreatorIQ.git
cd CreatorIQ/backend

# Initialize virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux

# Install requirements
pip install -r requirements.txt

# Configure the environment setup
cp .env.example .env
```

Review your `.env` file carefully. You must configure the `MONGO_URI`, `REDIS_URL`, `QDRANT_URL`, and various LLM/Search tokens:
```env
# Critical Keys
GEMINI_API_KEY=xxx
TAVILY_API_KEY=xxx
GROQ_API_KEY=xxx # Optional dev-tier fallback

# Databases
MONGO_URI=mongodb+srv://...
REDIS_URL=redis://...
QDRANT_URL=http://...
```
*Note: Make sure your `firebase-service-account.json` is properly mounted in the backend root based on your project configuration required by Firebase Admin.*

Run the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

In a new terminal:
```bash
cd CreatorIQ/frontend

# Install dependencies
npm install

# Setup local env
cp .env.example .env.local
```

Make sure your client-side variables point to both Firebase and your FastAPI backend:
```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=xxx
VITE_FIREBASE_AUTH_DOMAIN=xxx
VITE_FIREBASE_PROJECT_ID=xxx
```

Start the Vite hot-reloading dev server:
```bash
npm run dev
```

The application is now up and running! Visit `http://localhost:5173`. Your API Documentation is dynamically generated at `http://localhost:8000/docs`.

---

## 🏗 System Architecture Deep-Dive

**Layer 1: The Gateway**: The user issues a topic prompt on the Vite client. The request authenticates implicitly through Firebase tokens. The FastAPI layer verifies identity using the Firebase Admin interceptor.

**Layer 2: Execution Orchestration**: The prompt hits the LangGraph service, initiating a multi-stage flow. 
Our custom `ExecutionLayer` abstracts the raw models, checking global **Redis token buckets** to see if the user has breached their tier budget limit (e.g. `BUDGET_DAILY_USER_CAP_CENTS`). If the circuit breaker passes, it searches for idempotency caches and proceeds.

**Layer 3: Generative Assembly**:
1. Research fetches search terms, triggering the `Tavily API`. Target metadata is mapped into **Qdrant Vector DB**.
2. Context shifts dynamically through our agent chain, securely validated via tightly typed schemas via `Pydantic`.
3. LLM buffers stringify content and securely push them to the client utilizing Redis-mapped token streaming.

**Layer 4: Persistence**: Script generations alongside full context variables are updated automatically in **MongoDB**, linking safely back to the user's Firebase UID.

---

## 🧪 Testing and Checks
This repository boasts high-coverage sanity testing for the Execution layer, routing engine, and data integrations.

```bash
cd backend
python -m pytest testing/
```

This verifies the integrity of fallback routing mechanisms, budget enforcement limits, deterministic mocks (testing mode), and LLM circuit breakers explicitly isolated from the production network.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

Built with logic, passion, and next-generation compute layers. Create smartly. 🚀
