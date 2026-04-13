# 🚀 PGVECTOR SETUP CHEAT SHEET

## Print This & Keep Open While Setting Up

---

## ANSWER TO YOUR QUESTION

**Q: Do I need Docker for pgvector?**
A: YES. Use Docker for database only. Easy setup, highly recommended.

**Q: Will I still use manage.py?**
A: YES. Exactly the same way.

**Q: Will I still use npm start?**
A: YES. Exactly the same way.

---

## 3 DOCKER COMMANDS YOU NEED

```
1. docker-compose up -d        ← Start containers
2. docker-compose ps           ← Check they're running
3. docker-compose stop         ← Stop containers
```

That's it! That's all you need to know about Docker.

---

## FIRST-TIME SETUP (20 minutes)

### Step 1: Install Docker (5 min)
- Download: https://www.docker.com/products/docker-desktop
- Install & restart computer
- Verify: `docker --version` (shows version number)

### Step 2: Start Database (1 min)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy
docker-compose up -d
docker-compose ps  # Should show 2 containers: db, redis
```

### Step 3: Run Migrations (1 min)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\backend
.\venv\Scripts\Activate.ps1
python manage.py migrate
# Look for: Applying accounts.0003... OK
# Look for: Applying accounts.0006... OK
```

### Step 4: Start Django (5 min)
Keep Terminal 1 in backend directory
```powershell
python manage.py runserver 8000
# Should say: Starting development server at http://127.0.0.1:8000/
```

### Step 5: Start React (5 min)
**NEW Terminal 2**
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\frontend
npm start
# Browser opens at localhost:3000
```

### Step 6: Test
Go to http://localhost:3000
- Register user ✅
- Login ✅
- Upload conversation ✅

**DONE!** pgvector working! 🎉

---

## DAILY USAGE (30 seconds startup)

### Morning (Before Work)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy
docker-compose up -d
# Containers start from disk
```

### Terminal 1: Start Django
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\backend
.\venv\Scripts\Activate.ps1
python manage.py runserver 8000
```

### Terminal 2: Start React
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\frontend
npm start
```

### Night (Before Shutdown)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy
docker-compose stop
# Data persists, containers stopped
```

---

## FILE CHANGES AT A GLANCE

✅ `settings.py` - Added pgvector.django
✅ `novelty_models.py` - VectorField instead of TextField
✅ `similarity.py` - Real OpenAI embeddings + search
✅ `0003_novelty_models.py` - Vector column migration
✅ `.env` - POSTGRES_PORT=5432, Docker Redis

**That's all!** No other changes needed.

---

## QUICK TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| Docker not found | Restart PowerShell after installing Docker |
| Port 5432 in use | Check `docker-compose ps` |
| Migration fails | Run `docker-compose down -v && docker-compose up -d` |
| Can't connect DB | Check .env POSTGRES_PORT=5432 |
| pgvector error | Verify Docker container running: `docker-compose ps` |

---

## DOCKER COMMANDS REFERENCE

```powershell
# Check version
docker --version

# List running containers
docker-compose ps

# Start containers
docker-compose up -d

# Stop containers (keeps data)
docker-compose stop

# Start stopped containers
docker-compose start

# View logs
docker-compose logs -f db

# Delete everything (caution!)
docker-compose down -v
```

---

## ENVIRONMENT VARIABLES (In .env)

**Already set for you:**
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=flirty
POSTGRES_USER=flirty_user
POSTGRES_PASSWORD=flirty

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

OPENAI_API_KEY=sk-proj-...
```

**No changes needed!** Already configured.

---

## EXPECTED OUTPUT

### After `docker-compose up -d`
```
[✓] db is ready to accept connections
[✓] redis is ready to accept connections
```

### After `python manage.py migrate`
```
Applying accounts.0001_initial... OK
Applying accounts.0002_userprofile... OK
Applying accounts.0003_novelty_models... OK
Applying accounts.0004_... OK
... (more OK statuses)
```

### After `python manage.py runserver 8000`
```
System check identified no issues (0 silenced).
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### After `npm start`
```
Compiled successfully!
You can now view flirtyfy in the browser.
  Local:            http://localhost:3000
```

---

## VERIFICATION TESTS

### Test 1: Register
```powershell
$body = @{
    email = "test@test.com"
    username = "testuser"
    password = "TestPass123!"
    confirmPassword = "TestPass123!"
    date_of_birth = "2000-01-01"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/register/" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

Expected: HTTP 201, token received

### Test 2: Login
```powershell
$body = @{
    email = "test@test.com"
    password = "TestPass123!"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/login/" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

Expected: HTTP 200, login successful

### Test 3: Upload Conversation
Replace `YOUR_TOKEN`:
```powershell
$body = @{
    text = "This is a test conversation"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/novelty/upload/" `
  -Method Post `
  -Headers @{
    "Content-Type"="application/json"
    "Authorization"="Token YOUR_TOKEN"
  } `
  -Body $body
```

Expected: HTTP 201, conversation created

---

## WHAT'S RUNNING

```
DOCKER CONTAINERS:
  PostgreSQL  → localhost:5432  (pgvector-enabled)
  Redis       → localhost:6379  (Celery tasks)

YOUR LOCAL APPS:
  Django      → localhost:8000  (Backend)
  React       → localhost:3000  (Frontend)
  
ALL CONNECTED:
  Django ←→ Docker PostgreSQL
  Django ←→ Docker Redis
  React  ←→ Django API
```

---

## SUCCESS CHECKLIST

After following setup, verify:

```
☐ Docker installed: docker --version (shows version)
☐ Containers running: docker-compose ps (shows 2 running)
☐ Migrations done: All show "OK"
☐ Django running: http://localhost:8000 responds
☐ React running: http://localhost:3000 opens
☐ Registration works: Can create user
☐ Login works: Can login with that user
☐ Upload works: Can upload conversation
☐ No errors: No red errors in terminal
```

---

## DOCUMENTATION FILES

**Print These Too:**

| File | Use When | Time |
|------|----------|------|
| INDEX_START_HERE.md | Learning which doc to read | 1 min |
| SIMPLE_DOCKER_ANSWER.md | Want simple explanation | 5 min |
| PGVECTOR_QUICK_START.md | Running setup commands | 15 min |
| PGVECTOR_DOCKER_SETUP.md | Want complete guide | 20 min |
| ARCHITECTURE_COMPLETE.md | Want visual diagrams | 15 min |
| PGVECTOR_RE_ENABLEMENT_SUMMARY.md | Want technical details | 10 min |
| FILE_CHANGES_CHECKLIST.md | Want change verification | 5 min |

---

## KEYBOARD SHORTCUTS

```
Terminal Stop Command:      Ctrl + C
PostgreSQL Doc:             https://postgresql.org/docs
Docker Documentation:       https://docs.docker.com
Django Management:          python manage.py help
```

---

## BACKUP QUICK REFERENCE

```
If something breaks:
  docker-compose down -v          # Delete everything
  docker-compose up -d            # Fresh start
  python manage.py migrate        # Rebuild database

If you want to uninstall:
  docker-compose down -v          # Stop & remove containers
  Uninstall Docker Desktop

If you want to keep going:
  Just keep running docker-compose up -d daily
```

---

## TIME TRACKER

```
Installation:     5 minutes
docker-compose:   1 minute
Migrations:       1 minute
Django startup:   5 minutes
React startup:    5 minutes
Testing:          3 minutes
─────────────────────────
TOTAL:          20 minutes
```

---

## ONE MORE TIME: YOUR 3 DOCKER COMMANDS

```
DAILY START:
  docker-compose up -d

CHECK STATUS:
  docker-compose ps

DAILY STOP:
  docker-compose stop
```

**That's literally all you need.** Bookmark this section! 📌

---

## YOU'RE READY!

✅ Everything is set up
✅ All files modified
✅ All docs written
✅ Just follow the steps above
✅ You'll have pgvector working in 20 minutes

**LET'S GO!** 🚀

---

**Questions? Check `PGVECTOR_QUICK_START.md` TROUBLESHOOTING section**

**Need more detail? Check `PGVECTOR_DOCKER_SETUP.md`**

---

**Print this page. Keep it open. Follow the steps. Done! ✅**
