# PGVECTOR Quick Start: Copy-Paste Commands

This file contains the exact commands to run pgvector setup. Copy and paste them in order.

## Prerequisites Check (Run Once)
```powershell
docker --version
docker-compose --version
# Should show version numbers like: Docker version 24.x.x
```

## ⏱️ COMPLETE SETUP (One Time Only)

### Terminal 1: Start Docker PostgreSQL + Redis
```powershell
cd C:\Users\kiman\Projects\Flirtyfy
docker-compose up -d
docker-compose ps
```

Expected output:
```
NAME            STATE    PORTS
flirtyfy-db-1   running  5432/tcp
flirtyfy-redis-1 running 6379/tcp
```

### Terminal 2: Run Database Migrations
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\backend
.\venv\Scripts\Activate.ps1
python manage.py migrate
```

Expected output:
```
Applying accounts.0003_novelty_models... OK
Applying accounts.0004_...
...
```

### Terminal 2 (cont): Start Django Backend
```powershell
# Keep same terminal from above (venv already activated)
python manage.py runserver 8000
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

### Terminal 3: Start React Frontend
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\frontend
npm start
```

Browser will open at http://localhost:3000

---

## 🔄 DAILY USAGE (After Setup is Complete)

### Start Services (Every Time You Work)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy

# Terminal 1: Start containers (if not already running)
docker-compose start
# Or if you want fresh: docker-compose up -d

# Check they're running
docker-compose ps
```

### Terminal 2: Start Django
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\backend
.\venv\Scripts\Activate.ps1
python manage.py runserver 8000
```

### Terminal 3: Start React
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\frontend
npm start
```

---

## 🧪 VERIFY PGVECTOR WORKS

### Test 1: Register User
```powershell
$body = @{
    email = "pgvector_test_@test.com"
    username = "pgvector_user"
    password = "TestPass123!"
    confirmPassword = "TestPass123!"
    date_of_birth = "2000-01-15"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/register/" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body

$response.Content | ConvertFrom-Json | Format-List
```

Expected: HTTP 201, token received

### Test 2: Login
```powershell
$body = @{
    email = "pgvector_test_@test.com"
    password = "TestPass123!"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/login/" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body

$response.Content | ConvertFrom-Json | Format-List
```

Expected: HTTP 200, `message: "Login successful."`

### Test 3: Upload Conversation (Uses pgvector!)
Replace `YOUR_TOKEN` with token from Test 2:

```powershell
$body = @{
    text = "This is a test conversation that will be embedded with OpenAI and stored in pgvector"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/novelty/upload/" `
  -Method Post `
  -Headers @{
    "Content-Type"="application/json"
    "Authorization"="Token YOUR_TOKEN"
  } `
  -Body $body

$response.Content | ConvertFrom-Json | Format-List
```

Expected: HTTP 201, conversation upload created

---

## 🛑 STOP SERVICES

### Stop Docker (preserves data)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy
docker-compose stop
```

### Stop Django & React
Press `Ctrl+C` in each terminal

### Restart Next Day
```powershell
docker-compose start
# Then run Django and React again (see DAILY USAGE)
```

---

## 🔧 TROUBLESHOOTING

### "Cannot connect to PostgreSQL"
```powershell
docker-compose ps
# If not running:
docker-compose up -d
```

### "Port 5432 already in use"
```powershell
# Check what's using it:
netstat -ano | findstr 5432
# Kill it or use different port in docker-compose.yml
```

### "Migration error"
```powershell
# Reset database (caution: deletes data)
docker-compose down -v
docker-compose up -d
python manage.py migrate
```

### "OpenAI API error"
Verify in `.env`:
```
OPENAI_API_KEY=sk-proj-...
```
Should start with `sk-proj-`

### "pgvector extension not found"
```powershell
# Verify pgvector is running:
docker exec -it flirtyfy-db-1 psql -U flirty_user -d flirty -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 📊 WHAT'S HAPPENING

**Docker Containers Running:**
- PostgreSQL 14 + pgvector (port 5432)
- Redis 7 (port 6379)

**Your App Running Locally:**
- Django backend (port 8000) ← Connects to Docker PostgreSQL
- React frontend (port 3000) ← Calls Django API

**When You Upload Conversation:**
1. Text sent to API
2. OpenAI generates embedding (1536 dimensions)
3. Embedding stored in pgvector column
4. Future uploads compared using vector similarity
5. Similar responses filtered out (no duplicates/repetition)

---

## ✅ YOU'RE READY!

Follow the "COMPLETE SETUP" section once, then "DAILY USAGE" every day.

Any errors? Check TROUBLESHOOTING section above.
