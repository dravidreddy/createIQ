# CreateIQ 🚀

**AI-Powered Content Creation Platform for Creators**

CreateIQ is a full-stack application that uses a multi-agent AI pipeline to help content creators generate high-quality video scripts, from idea discovery to final polished content.

## Features

### 🤖 AI Agent Pipeline
1. **Idea Discovery Agent** - Searches trending topics and generates content ideas
2. **Research Script Agent** - Deep research and comprehensive script generation
3. **Screenplay Structure Agent** - Platform-specific structure and pacing guidance
4. **Editing & Improvement Agent** - Final polish with engagement optimization

### 🎨 Modern UI
- Dark/Light mode toggle
- Real-time streaming updates during generation
- Responsive design with Tailwind CSS
- Beautiful glassmorphism effects

### 🔐 Authentication
- JWT-based authentication
- Secure password hashing
- Token refresh mechanism

### 👤 Personalized Experience
- Creator profile setup
- Content niche selection
- Platform-specific optimization
- Target audience configuration

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **LangGraph** - Multi-agent orchestration
- **Google Gemini** - LLM provider (extensible to OpenAI)
- **Tavily** - Web search for research
- **FAISS** - Vector memory store
- **SQLAlchemy** - Database ORM
- **SQLite/PostgreSQL** - Database

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Axios** - API client

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- API Keys:
  - Google Gemini API key
  - Tavily API key (for web search)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

### Backend (.env)
```
# Required
GEMINI_API_KEY=your-gemini-api-key
TAVILY_API_KEY=your-tavily-api-key
SECRET_KEY=your-secret-key-for-jwt

# Optional
DATABASE_URL=sqlite+aiosqlite:///./data/createiq.db
LLM_PROVIDER=gemini
DEBUG=true
```

## Project Structure

```
CreateIQ/
├── backend/
│   ├── app/
│   │   ├── agents/         # AI agents (4 agents + orchestrator)
│   │   ├── api/            # API routes
│   │   ├── llm/            # LLM abstraction layer
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── tools/          # Search & memory tools
│   │   └── utils/          # Utilities
│   ├── data/               # SQLite DB & FAISS indexes
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/     # UI components
    │   ├── pages/          # Page components
    │   ├── services/       # API service
    │   ├── store/          # Zustand stores
    │   └── types/          # TypeScript types
    └── package.json
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Create account
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh tokens
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users/me` - Get user with profile
- `POST /api/v1/users/profile` - Create profile
- `PUT /api/v1/users/profile` - Update profile

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `DELETE /api/v1/projects/{id}` - Delete project
- `POST /api/v1/projects/{id}/select-idea` - Select idea

### Agents
- `POST /api/v1/agents/{id}/discover-ideas` - Run idea discovery
- `POST /api/v1/agents/{id}/generate-script` - Generate script
- `POST /api/v1/agents/{id}/analyze-screenplay` - Analyze screenplay
- `POST /api/v1/agents/{id}/edit-script` - Edit and polish
- `POST /api/v1/agents/{id}/run-pipeline` - Run full pipeline
- `GET /api/v1/agents/{id}/stream/discover-ideas` - SSE stream

## License

MIT License

---

Built with ❤️ using AI-powered content creation
