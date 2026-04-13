# PGVECTOR Setup Guide: Complete Docker Solution

## What is Docker & Why Use It?

Docker is a container tool that runs applications in isolated environments. For pgvector:
- **Without Docker**: You'd need to manually install PostgreSQL + pgvector extension on Windows (very complex)
- **With Docker**: One command runs PostgreSQL with pgvector pre-installed
- **Your App**: Still runs locally with `python manage.py` and `npm start` (not in Docker)

## Architecture
```
┌─────────────────────────────────────────────────────┐
│                   YOUR COMPUTER                      │
│                                                      │
│  ┌──────────────────┐      ┌───────────────────┐   │
│  │   Django App     │      │   React Frontend  │   │
│  │ (manage.py dev)  │      │   (npm start)     │   │
│  │  Port 8000       │      │   Port 3000       │   │
│  └────────┬─────────┘      └─────────────────┬─┘   │
│           │                                  │       │
│           └──────────────┬───────────────────┘       │
│                          │                           │
│           ┌──────────────▼──────────────┐           │
│           │   Docker Container         │           │
│           │  (PostgreSQL + pgvector)   │           │
│           │    + Redis (Celery)        │           │
│           │   Port 5432, 6379          │           │
│           └───────────────────────────┘            │
└─────────────────────────────────────────────────────┘
```

## Prerequisites
1. ✅ Docker Desktop installed (you said you have this)
2. ✅ Python 3.11+ with Django project (you have this)
3. ✅ PostgreSQL credentials ready

## Complete Setup: Step-by-Step

### STEP 1: Verify Docker is Installed
```powershell
docker --version
docker-compose --version
```

You should see version numbers. If not, install Docker Desktop from docker.com

### STEP 2: Verify Backend Environment File
Your `.env` file should have these Postgres settings (running in Docker):

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=flirty
POSTGRES_USER=flirty_user
POSTGRES_PASSWORD=flirty_password

# Redis  
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your_key_here

# Django
SECRET_KEY=your_secret_key
DEBUG=True
```

⚠️ **IMPORTANT**: Note the port is `5432` (Docker), NOT `5433` (what you might have used before)

### STEP 3: Start Docker Containers
```powershell
cd C:\Users\kiman\Projects\Flirtyfy

# Start PostgreSQL + pgvector and Redis in Docker
docker-compose up -d

# Watch for any errors (should say "Done" and show container names)
```

**What this does:**
- Pulls pgvector-enabled PostgreSQL image (ankane/pgvector)
- Starts PostgreSQL on port 5432
- Starts Redis on port 6379
- Creates flirty database

### STEP 4: Verify Containers are Running
```powershell
docker-compose ps

# You should see:
# - db (PostgreSQL + pgvector) - running
# - redis - running
```

### STEP 5: Run Django Migrations (Creates Tables)
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\backend

# Activate venv and run migrations
.\venv\Scripts\Activate.ps1
python manage.py migrate

# Expected output:
# Applying accounts.0001_initial... OK
# Applying accounts.0002_userprofile... OK
# Applying accounts.0003_novelty_models... OK
# ... (all show OK)
```

### STEP 6: Run Django Development Server
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\backend

# Keep venv activated from Step 5, then:
python manage.py runserver 8000

# Server should start at http://localhost:8000
# Keep this terminal open and running
```

### STEP 7: In Another Terminal - Start React Frontend
```powershell
cd C:\Users\kiman\Projects\Flirtyfy\frontend

npm start

# Frontend opens at http://localhost:3000
```

### STEP 8: Verify Everything Works
Open your browser:
- http://localhost:3000 - Frontend
- http://localhost:8000/api/register/ - Backend API

## Testing pgvector Integration

### Test 1: User Registration (uses pgvector)
```powershell
$body = @{
    email = "pgvector_test@test.com"
    username = "pgvector_user"
    password = "SecurePassword123!"
    confirmPassword = "SecurePassword123!"
    date_of_birth = "2000-01-01"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/register/" `
  -Method Post `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body

$response.Content | ConvertFrom-Json | Format-List
```

### Test 2: Upload Conversation (triggers pgvector embedding)
```powershell
$body = @{
    text = "This is a test conversation for pgvector embedding"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/novelty/upload/" `
  -Method Post `
  -Headers @{
    "Content-Type"="application/json"
    "Authorization"="Token YOUR_TOKEN_HERE"
  } `
  -Body $body

$response.Content | ConvertFrom-Json | Format-List
```

## Common Issues & Solutions

### Issue: "Cannot connect to PostgreSQL"
**Solution:** Check if Docker containers are running
```powershell
docker-compose ps
# All should show "running" status

# If not, restart:
docker-compose down
docker-compose up -d
```

### Issue: "Extension 'pgvector' do not exist"
**Solution:** This was the original problem! It's now fixed because:
- ✅ Docker uses `ankane/pgvector` image (has pgvector pre-installed)
- ✅ Migration updated to use pgvector VectorField
- ✅ Code updated to generate embeddings

### Issue: Migrations fail with "relation does not exist"
**Solution:** Drop and recreate database
```powershell
# CAUTION: This deletes all data
docker-compose down -v  # -v removes volumes (database)
docker-compose up -d
python manage.py migrate
```

### Issue: "Port 5432 already in use"
**Solution:** Another app is using PostgreSQL port
```powershell
# Use a different port in docker-compose.yml:
# Change: ports: ["5432:5432"]
# To:     ports: ["5433:5432"]

# Then update .env:
# POSTGRES_PORT=5433
```

## Stopping & Restarting

### Stop All Containers (data persists)
```powershell
docker-compose stop
```

### Restart Containers
```powershell
docker-compose start
```

### Remove Everything (caution: deletes database)
```powershell
docker-compose down -v
```

## File Changes Made to Enable pgvector

| File | Change | Reason |
|------|--------|--------|
| `settings.py` | Added `'pgvector.django'` to INSTALLED_APPS | Register pgvector with Django |
| `novelty_models.py` | Changed `embedding = TextField()` to `embedding = VectorField(dimensions=1536)` | Use vector column for embeddings |
| `similarity.py` | Restored `get_embedding()` to call OpenAI API | Generate actual embeddings instead of empty arrays |
| `similarity.py` | Restored `semantic_similar_replies()` with pgvector L2Distance | Enable vector similarity search |
| `0003_novelty_models.py` | Updated migration to use `pgvector.django.VectorField` | Create vector column in DB |
| `.env` | POSTGRES_PORT=5432 (Docker), not 5433 | Connect to Docker PostgreSQL |

## What pgvector Does Now

1. **Embedding Generation**: When you upload a conversation:
   - Text → OpenAI API → 1536-dimensional vector
   - Vector stored in PostgreSQL pgvector column

2. **Similarity Search**: Find similar conversations:
   - New vector compared against all stored vectors
   - Uses L2 distance (mathematical similarity)
   - Prevents duplicate/similar responses

3. **Performance**: 
   - pgvector creates indexes on vector columns
   - Fast similarity search even with 1000s of embeddings

## Verify Installation

After migrations run successfully, verify pgvector extension:

```powershell
# Connect to Docker PostgreSQL
docker exec -it flirtyfy-db-1 psql -U flirty_user -d flirty -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Should show: vector | 1.0 | ...
```

## Next Steps

1. ✅ Read this entire guide
2. ✅ Follow steps 1-7 in order
3. ✅ Run one of the test commands
4. ✅ Test frontend registration/chat flow
5. ✅ Monitor terminal output for any errors

**You're ready to use pgvector!** 🚀
