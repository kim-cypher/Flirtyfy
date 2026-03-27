# Quick Start Guide

## Prerequisites
- Python 3.8+ installed
- Node.js 14+ installed
- npm installed

## Windows Users

### Step 1: Run the Setup Script
Double-click `setup.bat` and wait for it to complete.

### Step 2: Start Backend (Terminal 1)
```powershell
cd backend
venv\Scripts\activate.bat
python manage.py runserver
```

### Step 3: Start Frontend (Terminal 2)
```powershell
cd frontend
npm start
```

### Step 4: Access the App
Open http://localhost:3000 in your browser

---

## Linux/Mac Users

### Step 1: Run the Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### Step 2: Start Backend (Terminal 1)
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

### Step 3: Start Frontend (Terminal 2)
```bash
cd frontend
npm start
```

### Step 4: Access the App
Open http://localhost:3000 in your browser

---

## Manual Setup (If Setup Script Fails)

### Backend Setup
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

**Backend will be available at:** http://localhost:8000

### Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

**Frontend will be available at:** http://localhost:3000

---

## Usage

### Register
1. Visit http://localhost:3000/register
2. Enter username, email, password, confirm password
3. Click "Register"
4. You'll be redirected to the dashboard

### Login
1. Visit http://localhost:3000/login
2. Enter email and password
3. Click "Login"
4. You'll be redirected to the dashboard

### Dashboard
- View your username and email
- Click "Logout" to logout

### Admin Panel
1. Create a superuser (if not done during setup)
```bash
cd backend
python manage.py createsuperuser
```
2. Visit http://localhost:8000/admin
3. Login with superuser credentials
4. Manage users and user profiles

---

## Troubleshooting

### CORS Error
**Problem:** Cross-Origin requests being blocked

**Solution:**
- Check that backend is running on port 8000
- Check that frontend is running on port 3000
- Verify CORS_ALLOWED_ORIGINS in backend/flirty_backend/settings.py

### Module Not Found Error
**Problem:** ImportError for Django or React modules

**Solution:**
- Ensure pip/npm dependencies are installed
- Rerun `pip install -r requirements.txt` (backend)
- Rerun `npm install` (frontend)

### Database Error
**Problem:** Django throws "no such table" error

**Solution:**
```bash
cd backend
python manage.py migrate
```

### Port Already in Use
**Problem:** Port 8000 or 3000 already in use

**Solution:**
- Kill the process using the port
- Or run on different port: `python manage.py runserver 8001`
- Or: `PORT=3001 npm start` (frontend)

### Environment Variables Not Loading
**Problem:** API calls going to wrong URL

**Solution:**
- Create .env file in frontend folder
- Add: `REACT_APP_API_URL=http://localhost:8000/api`
- Restart the frontend development server

---

## Project Structure Overview

```
Flirty/
├── backend/           # Django server
├── frontend/          # React app
├── README.md          # Full documentation
├── setup.bat          # Windows setup (double-click to run)
├── setup.sh           # Linux/Mac setup
└── COMPLETION_CHECKLIST.md  # What's been completed
```

---

## Testing with Postman/cURL

### Register User
```bash
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test@123456",
    "confirmPassword": "Test@123456"
  }'
```

### Login User
```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test@123456"
  }'
```

---

## What's Included

✅ Complete Django backend with user authentication
✅ Complete React frontend with routing
✅ Redux state management
✅ API integration with error handling
✅ Responsive UI design
✅ User profile model
✅ Admin interface
✅ Automatic profile creation
✅ CORS configuration
✅ Token-based authentication
✅ Environment configuration files
✅ Setup scripts
✅ Complete documentation

---

## Support

For issues, refer to:
1. README.md - Detailed documentation
2. COMPLETION_CHECKLIST.md - What's implemented
3. Backend logs: Check Django terminal output
4. Frontend logs: Check browser console (F12)
5. Admin panel: http://localhost:8000/admin

---

Happy coding! 🎉