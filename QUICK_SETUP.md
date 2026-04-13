# 🚀 Quick Start - After Cloning Flirtyfy

## 30-Second Summary

**Your Setup**: Windows 11 + WSL2 Redis + Python/Node.js

**Total Setup Time**: ~15 minutes

---

## ✅ Pre-Cloning Checklist

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Node.js 14+ installed (`node --version`)
- [ ] Redis running in WSL (`wsl redis-cli ping` should return PONG)
- [ ] PostgreSQL installed (Docker or native)

---

## 🎯 EXACT Steps to Run App

### Terminal 1: Backend Setup & Run

```powershell
cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Create `.env` file in backend folder:**
```
SECRET_KEY=generate-a-random-string-here
DEBUG=True
OPENAI_API_KEY=sk-your-key-here
GEONAMES_USERNAME=your-username
POSTGRES_DB=flirty
POSTGRES_USER=flirty
POSTGRES_PASSWORD=flirty
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://192.168.152.179:6379/0
CELERY_BROKER_URL=redis://192.168.152.179:6379/0
CELERY_RESULT_BACKEND=redis://192.168.152.179:6379/0
```

**Then run:**
```powershell
python manage.py migrate
python manage.py runserver
```

✅ Backend ready at: `http://localhost:8000`

---

### Terminal 2: Frontend Setup & Run

```powershell
cd frontend
npm install
npm start
```

✅ Frontend opens automatically at: `http://localhost:3000`

---

## 🔧 What Gets Installed

| Component | Purpose | Version | Port |
|-----------|---------|---------|------|
| **Django** | Backend API | 4.2.7 | 8000 |
| **PostgreSQL** | Database | pgvector | 5432 |
| **Redis** | Cache & broker | 7 | 6379 |
| **Celery** | Task queue | 5.3.6 | - |
| **React** | Frontend | 18.2.0 | 3000 |
| **Redux** | State mgmt | 4.2.1 | - |

---

## 📋 File Structure

```
flirtyfy/
├── backend/
│   ├── .env                    ← Create this (copy from .env.example)
│   ├── requirements.txt         ← Dependencies
│   ├── manage.py               ← Django commands
│   ├── accounts/               ← User app
│   └── flirty_backend/         ← Settings & config
└── frontend/
    ├── package.json            ← Dependencies
    ├── src/
    │   ├── App.js
    │   └── redux/              ← State management
    └── public/
```

---

## ⚠️ Redis Configuration (CRITICAL)

**Your WSL Redis IP: `192.168.152.179`**

This is already configured in:
- ✅ `backend/flirty_backend/settings.py` (line ~170)
- ✅ `backend/.env.example` (shows correct IP)
- ✅ CHANNEL_LAYERS configuration (for WebSockets)

**In your `.env`**, use:
```
REDIS_URL=redis://192.168.152.179:6379/0
CELERY_BROKER_URL=redis://192.168.152.179:6379/0
CELERY_RESULT_BACKEND=redis://192.168.152.179:6379/0
```

---

## 🐳 Docker: Should You Use It?

| Use Case | Recommendation |
|----------|---|
| Local development with WSL Redis | ❌ NO - Skip Docker |
| Production deployment | ✅ YES - Use Docker |
| Team collaboration | ✅ YES - Use Docker |
| Just testing locally | ❌ NO - Use WSL directly |

**Your case**: ✅ Skip Docker, use WSL Redis directly (simpler).

---

## 🆘 Common Issues & Fixes

### "Can't connect to Redis"
```powershell
wsl
redis-cli ping
# Should output: PONG
```
If it fails, start Redis in WSL:
```bash
wsl
redis-server
# Or:
sudo systemctl start redis-server
```

### "Connection refused to PostgreSQL:5432"
Start PostgreSQL Docker container:
```powershell
docker run -d `
  --name flirty-postgres `
  -e POSTGRES_DB=flirty `
  -e POSTGRES_USER=flirty `
  -e POSTGRES_PASSWORD=flirty `
  -p 5432:5432 `
  ankane/pgvector:latest
```

### "Port 8000 already in use"
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "ModuleNotFoundError" when running manage.py
Make sure virtual environment is activated:
```powershell
venv\Scripts\activate.bat
```

### "npm: command not found"
Node.js not installed. Download from: https://nodejs.org/

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────┐
│  React Frontend (localhost:3000)        │
│  - Redux State Management               │
│  - Components & UI                      │
└─────────────────┬───────────────────────┘
                  │
                  │ HTTP/WebSocket
                  ↓
┌─────────────────────────────────────────┐
│  Django Backend (localhost:8000)        │
│  - REST API                             │
│  - User Authentication                  │
│  - AI Response Generation               │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┬──────────┐
        ↓                    ↓          ↓
    ┌────────┐        ┌──────────┐   ┌──────────┐
    │ Redis  │        │PostgreSQL│   │ Celery   │
    │(Cache) │        │(Database)│   │(Tasks)   │
    │:6379   │        │:5432     │   │Worker    │
    └────────┘        └──────────┘   └──────────┘
```

---

## 🔑 Required API Keys

Before testing features, add these to `.env`:

1. **OpenAI API Key**
   - Get at: https://platform.openai.com/api/keys
   - Key format: `sk-...`

2. **Geonames Username**
   - Get at: https://www.geonames.org/
   - Free account needed

---

## ✨ After Setup: Testing the App

1. **Visit Frontend**: http://localhost:3000
2. **Register a new account**
3. **Login with credentials**
4. **Test chat feature** (uses OpenAI)
5. **Admin panel**: http://localhost:8000/admin

---

## 📚 Detailed Guides

For more information:
- Full setup guide: Read `SETUP_GUIDE_COMPLETE.md`
- Docker guide: Section "OPTION 2: WITH Docker" in `SETUP_GUIDE_COMPLETE.md`
- Troubleshooting: See "🆘 Quick Help" section in `SETUP_GUIDE_COMPLETE.md`

---

## 🎓 What Each Component Does

### Backend (Django + DRF)
- Handles user authentication
- Manages database operations
- Generates AI responses
- Provides REST API endpoints
- Runs async tasks with Celery

### Frontend (React + Redux)
- User interface
- Form handling
- State management (Redux)
- API communication

### Database (PostgreSQL)
- Stores user data
- Vector embeddings (pgvector extension)
- Message history

### Redis
- **Cache**: Fast data retrieval
- **Broker**: Celery task queue
- WebSocket support
- Session storage

### Celery
- Background task processing
- Async job handling
- Long-running operations without blocking

---

## 🚀 You're Ready!

1. Create `.env` file in backend/
2. Run Terminal 1: Backend
3. Run Terminal 2: Frontend
4. Open http://localhost:3000

**Happy coding!** 🎉

---

*Last updated: April 5, 2026*
*For WSL2 Redis with Windows 11*
