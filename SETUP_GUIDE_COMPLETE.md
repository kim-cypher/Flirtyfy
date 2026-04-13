# Complete Setup Guide for Flirty App
**After Cloning - Step by Step Instructions**

---

## 📋 Project Dependencies Overview

Your project uses:
- **Django 4.2.7** - Backend web framework
- **PostgreSQL with pgvector** - Database with vector search
- **Redis** - Message broker & caching
- **Celery** - Task queue (for async jobs)
- **React 18** - Frontend
- **Redux** - State management
- **OpenAI API** - For AI response generation
- **Docker** - Optional containerization

---

## ❓ Do You Need Docker Desktop?

**Answer: Only if you want the easy route**

- ✅ **WITH Docker**: One command to start everything (easier but heavier)
- ✅ **WITHOUT Docker**: Run services separately (what we recommend for WSL Redis)

Since you're using WSL Redis, we'll show BOTH methods.

---

# 🚀 OPTION 1: WITHOUT Docker (Using WSL Redis)

This is the simpler approach for your setup. Use this if you already have Redis running in WSL.

## Prerequisites Check

```powershell
# Check Python version (need 3.8+)
python --version

# Check Node.js (need 14+)
node --version

# Check npm
npm --version

# Check Redis is running in WSL (should get PONG)
wsl
redis-cli ping
exit
```

---

## Step 1: Create Environment Files

**Backend (.env file)**

Navigate to `backend/` folder and create a file named `.env`:

```
# backend/.env
SECRET_KEY=your-secret-key-here-make-it-long-and-random
DEBUG=True
OPENAI_API_KEY=sk-your-openai-api-key-here
GEONAMES_USERNAME=your-geonames-username

# Database (PostgreSQL)
POSTGRES_DB=flirty
POSTGRES_USER=flirty
POSTGRES_PASSWORD=flirty
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis (Your WSL Redis)
CELERY_BROKER_URL=redis://192.168.152.179:6379/0
CELERY_RESULT_BACKEND=redis://192.168.152.179:6379/0
```

**Frontend (.env file)**

Navigate to `frontend/` folder and create a file named `.env`:

```
# frontend/.env
REACT_APP_API_URL=http://localhost:8000
```

---

## Step 2: Install PostgreSQL

### Option A: Use Docker for just PostgreSQL

```powershell
# Run PostgreSQL in Docker (if you don't have it installed)
docker run -d `
  --name flirty-postgres `
  -e POSTGRES_DB=flirty `
  -e POSTGRES_USER=flirty `
  -e POSTGRES_PASSWORD=flirty `
  -p 5432:5432 `
  ankane/pgvector:latest
```

### Option B: Install PostgreSQL natively on Windows
- Download from: https://www.postgresql.org/download/windows/
- During installation, create a user `flirty` with password `flirty`
- Create database `flirty`

---

## Step 3: Backend Setup

```powershell
# Open PowerShell and navigate to project
cd c:\Users\kiman\Projects\Flirtyfy

# Go to backend folder
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat

# Install all dependencies
pip install -r requirements.txt

# Run migrations to create database tables
python manage.py migrate

# Create an admin account (optional, for Django admin panel)
#flirtykim
#pass: Kimani00!1
python manage.py createsuperuser

# Start Django server
python manage.py runserver
```

✅ Backend should now run at `http://localhost:8000`

---

## Step 4: Frontend Setup

Open a **NEW PowerShell terminal** (keep backend running in the first one):

```powershell
# Navigate to frontend
cd c:\Users\kiman\Projects\Flirtyfy\frontend

# Install dependencies
npm install

# Start React development server
npm start
```

✅ Frontend should open at `http://localhost:3000`

---

## Step 5: Verify Everything Works

1. **Backend Check**: Go to `http://localhost:8000` - You should see a Django page
2. **Admin Panel**: Go to `http://localhost:8000/admin` - Login with your superuser account
3. **Frontend Check**: Frontend tab should auto-open at `http://localhost:3000`
4. **Redis Check**: Run this in WSL:
   ```bash
   wsl
   redis-cli
   ping
   # Should respond: PONG
   exit
   ```

---

## ⚠️ CHANNEL_LAYERS Configuration

Since you're using WSL Redis at `192.168.152.179:6379`, update your `settings.py`:

**Location**: `backend/flirty_backend/settings.py`

Find this section (around line 170) and make sure it matches:

```python
# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://192.168.152.179:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://192.168.152.179:6379/0')

# Cache (add if not present)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://192.168.152.179:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# WebSocket support (add if using Django Channels)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("192.168.152.179", 6379)],
        },
    },
}
```

---

## 🐛 Troubleshooting Without Docker

### Issue: "Cannot connect to Redis"
**Solution**: Verify WSL Redis is running:
```powershell
wsl
redis-server  # or sudo systemctl start redis-server
exit
```

### Issue: "Cannot connect to PostgreSQL"
**Solution**: If using Docker, verify container is running:
```powershell
docker ps  # Should show flirty-postgres
```

### Issue: "Port 8000 already in use"
**Solution**: Kill the process using port 8000:
```powershell
netstat -ano | findstr :8000
# Note the PID, then:
taskkill /PID <PID> /F
```

### Issue: "Port 3000 already in use"
**Solution**: Kill the process using port 3000:
```powershell
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

---

---

# 🐳 OPTION 2: WITH Docker (Complete Containerization)

Use this if you want everything automated, but your WSL Redis will be replaced with Docker Redis.

## Prerequisites

1. **Install Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Enable WSL 2 integration during installation
   - Restart your computer

2. **Verify Installation**
   ```powershell
   docker --version
   docker run hello-world
   ```

---

## Step 1: Create Environment File

Create `backend/.env`:

```
SECRET_KEY=your-secret-key-here-make-it-long-and-random
DEBUG=False
OPENAI_API_KEY=sk-your-openai-api-key-here
GEONAMES_USERNAME=your-geonames-username

# Docker handles these automatically via docker-compose
POSTGRES_DB=flirty
POSTGRES_USER=flirty
POSTGRES_PASSWORD=flirty
POSTGRES_HOST=db
POSTGRES_PORT=5432

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

---

## Step 2: Understand docker-compose.yml

Your `docker-compose.yml` has 3 services:

```yaml
services:
  db:           # PostgreSQL database
    - Runs on: localhost:5432
    - Image: ankane/pgvector (PostgreSQL with vector extensions)
  
  redis:        # Redis cache & broker
    - Runs on: localhost:6379
    - Image: redis:7
  
  backend:      # Django API
    - Runs on: localhost:8000
    - Builds from Dockerfile
    - Runs migrations
    - Starts Celery worker
    - Starts Gunicorn server
```

---

## Step 3: Build and Run with Docker

```powershell
# Navigate to project root
cd c:\Users\kiman\Projects\Flirtyfy

# Build Docker images (first time only - takes 2-3 minutes)
docker-compose build

# Start all services (Docker containers)
docker-compose up

# This will output logs. You should see:
# - "db_1    | database system is ready to accept connections"
# - "redis_1 | Ready to accept connections"  
# - "backend_1 | Starting development server at 0.0.0.0:8000"
```

✅ All backend services now running in Docker!

---

## Step 4: Run Frontend

Open a **NEW PowerShell terminal**:

```powershell
# Navigate to frontend
cd c:\Users\kiman\Projects\Flirtyfy\frontend

# Install dependencies (first time only)
npm install

# Start development server
npm start
```

✅ Frontend at `http://localhost:3000`

---

## Step 5: Docker Common Commands

```powershell
# View running containers
docker ps

# View logs
docker-compose logs backend
docker-compose logs -f redis  # Follow logs

# Stop all containers
docker-compose down

# Remove all Docker data (warning: deletes database!)
docker-compose down -v

# Rebuild after code changes
docker-compose up --build

# Execute command in running container
docker-compose exec backend python manage.py createsuperuser

# Access PostgreSQL in Docker
docker-compose exec db psql -U flirty -d flirty
```

---

## 🔄 Switching from Docker to WSL Redis

If you want to use Docker but with your WSL Redis, update `docker-compose.yml`:

```yaml
backend:
  # ... other settings ...
  environment:
    - CELERY_BROKER_URL=redis://host.docker.internal:6379/0
    - CELERY_RESULT_BACKEND=redis://host.docker.internal:6379/0
```

Also update `backend/.env`:
```
CELERY_BROKER_URL=redis://192.168.152.179:6379/0
CELERY_RESULT_BACKEND=redis://192.168.152.179:6379/0
```

The key is using `host.docker.internal` instead of a specific IP inside Docker.

---

---

# 📊 Comparison: Docker vs Non-Docker

| Factor | WITHOUT Docker | WITH Docker |
|--------|---|---|
| **Setup Time** | 5-10 min | 15-20 min (first time) |
| **Complexity** | Lower | Higher |
| **Resources** | Lower | Higher (Docker uses memory) |
| **Isolation** | No | Yes |
| **Production Ready** | No | Yes |
| **Best For** | Development | Both dev & production |
| **For WSL Redis** | ✅ Easier | ⚠️ Need special config |

---

# 🎯 Recommended Setup for You

**Since you're using WSL Redis on Windows:**

✅ **Use OPTION 1 (Without Docker)**
- You already have Redis running in WSL
- Simpler setup
- Easier to debug issues
- Your current RSL Redis will be used directly
- Lower system resource usage

Only use Docker if you plan to:
- Deploy to production
- Share setup with team members
- Need perfect environment isolation

---

# 📝 Summary Checklist

After cloning, follow this order:

- [ ] Create `backend/.env` with credentials
- [ ] Create `frontend/.env` with API URL
- [ ] Install PostgreSQL (Docker or native)
- [ ] Setup Python virtual environment
- [ ] Install backend dependencies (`pip install -r requirements.txt`)
- [ ] Run migrations (`python manage.py migrate`)
- [ ] Start Backend (`python manage.py runserver`)
- [ ] Install frontend dependencies (`npm install`)
- [ ] Start Frontend (`npm start`)
- [ ] Visit `http://localhost:3000`

**Time to functional app: ~15 minutes**

---

# 🆘 Quick Help

| Problem | Solution |
|---------|----------|
| Redis connection error | Verify WSL Redis running: `wsl redis-cli ping` |
| PostgreSQL connection error | Verify Docker container: `docker ps` or check native install |
| Port 8000 in use | `netstat -ano \| findstr :8000` → `taskkill /PID <PID> /F` |
| Port 3000 in use | `netstat -ano \| findstr :3000` → `taskkill /PID <PID> /F` |
| "ModuleNotFoundError" | Activate venv: `venv\Scripts\activate.bat` |
| Docker issues | Run: `docker-compose down` → `docker-compose up --build` |

---

# 🔑 Important API Keys

Before testing, add to `backend/.env`:

1. **OpenAI API Key** (for AI features)
   - Get from: https://platform.openai.com/api/keys
   - Add to `.env`: `OPENAI_API_KEY=sk-...`

2. **Geonames Username** (for location features)
   - Get from: https://www.geonames.org/login
   - Add to `.env`: `GEONAMES_USERNAME=...`

---

**You're all set! Start with Option 1 (Without Docker) for the quickest path.** 🚀
