# Flirty - Login & Register Application

A full-stack web application built with Django backend and React frontend with Redux state management.

## Project Structure

```
Flirty/
├── backend/                 # Django backend
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   ├── accounts/            # User accounts app
│   │   ├── migrations/
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── models.py (UserProfile model)
│   │   ├── admin.py (User admin customization)
│   │   ├── signals.py (Auto-create UserProfile)
│   │   ├── urls.py
│   │   └── apps.py
│   └── flirty_backend/      # Django project settings
│       ├── settings.py
│       ├── urls.py
│       ├── wsgi.py
│       └── asgi.py
└── frontend/                # React frontend
    ├── package.json
    ├── .env.example
    ├── .gitignore
    ├── public/
    ├── src/
    │   ├── index.js
    │   ├── App.js
    │   ├── store.js
    │   ├── services/        # API utilities
    │   │   └── apiClient.js (Axios configuration)
    │   ├── redux/           # Redux state management
    │   │   ├── actions/
    │   │   │   └── authActions.js
    │   │   └── reducers/
    │   │       └── authReducer.js
    │   └── components/      # React components
    │       ├── Login.js
    │       ├── Register.js
    │       ├── Dashboard.js
    │       ├── Auth.css
    │       └── Dashboard.css
```

## Features

✅ User Registration with validation  
✅ User Login with token authentication  
✅ JWT Token-based Authentication  
✅ Redux State Management for Auth  
✅ Protected Dashboard (requires login)  
✅ CORS Enabled for frontend/backend communication  
✅ Responsive UI with gradient styling  
✅ User Profiles with extended info  
✅ Automatic UserProfile creation on User registration  
✅ Admin interface for user management  

## Backend Setup

### Prerequisites
- Python 3.8 or higher
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the environment file:
```bash
cp .env.example .env
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser (optional, for admin panel):
```bash
python manage.py createsuperuser
```

7. Start the Django development server:
```bash
python manage.py runserver
```

The backend will be available at `http://localhost:8000`  
Admin panel: `http://localhost:8000/admin`

## Frontend Setup

### Prerequisites
- Node.js 14 or higher
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Install dependencies:
```bash
npm install
```

4. Start the React development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Register
- **URL:** `POST /api/register/`
- **Body:**
```json
{
  "username": "user",
  "email": "user@example.com",
  "password": "password123",
  "confirmPassword": "password123"
}
```
- **Response:**
```json
{
  "token": "token-key",
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "first_name": "",
    "last_name": "",
    "profile": {
      "bio": null,
      "avatar": null
    }
  },
  "message": "User registered successfully."
}
```

### Login
- **URL:** `POST /api/login/`
- **Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
- **Response:**
```json
{
  "token": "token-key",
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "first_name": "",
    "last_name": "",
    "profile": {
      "bio": null,
      "avatar": null
    }
  },
  "message": "Login successful."
}
```

## Usage

### Step 1: Start Backend
```bash
cd backend
python manage.py runserver
```

### Step 2: Start Frontend
```bash
cd frontend
npm start
```

### Step 3: Access the App
1. Open `http://localhost:3000` in your browser
2. Register a new account or login with existing credentials
3. After login, you'll be redirected to the dashboard
4. Click "Logout" to logout

## Database Models

### User (Django Built-in)
- id
- username
- email
- password (hashed)
- first_name
- last_name
- is_active
- is_staff
- date_joined

### UserProfile (Custom)
- id
- user (OneToOne relationship with User)
- bio (optional)
- avatar (optional image)
- created_at
- updated_at

The UserProfile is automatically created when a new User is registered.

## Admin Panel

Access the admin panel at `http://localhost:8000/admin` to:
- Manage users
- View and edit user profiles
- Create superusers

## Technologies Used

### Backend
- **Framework:** Django 4.2.7
- **API:** Django REST Framework 3.14.0
- **Authentication:** Token Authentication (DRF)
- **CORS:** django-cors-headers 4.3.1
- **Database:** SQLite (default, can be changed)

### Frontend
- **Framework:** React 18.2.0
- **State Management:** Redux with Redux Thunk
- **Routing:** React Router DOM 6.18.0
- **HTTP Client:** Axios 1.6.0
- **Build Tool:** Create React App

## Environment Variables

### Backend (.env)
```
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:8000/api
```

## Security Notes

⚠️ **Important for Production:**
- Change `SECRET_KEY` in Django settings
- Set `DEBUG = False` in production
- Use environment variables from `.env` files (not shown in code)
- Configure proper database (PostgreSQL recommended)
- Use HTTPS
- Set proper CORS origins
- Use secure password hashing
- Implement rate limiting
- Add CSRF protection

## Troubleshooting

### CORS Errors
If you get CORS errors, ensure:
1. Backend has the frontend URL in `CORS_ALLOWED_ORIGINS`
2. Frontend is making requests to the correct backend URL

### Token Authentication Issues
The token is stored in localStorage. Clear it and login again if issues persist.

### Database Issues
Reset the database:
```bash
# Remove db.sqlite3
# Run migrations again
python manage.py migrate
```

## License

This project is licensed under the MIT License.