#!/bin/bash

# Flirty App Setup Script
# This script automates the setup of both backend and frontend

echo "================================"
echo "Flirty App - Setup Script"
echo "================================"
echo ""

# Check Python installation
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check Node.js installation
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 14+"
    exit 1
fi
echo "✓ Node.js found: $(node --version)"
echo "✓ npm found: $(npm --version)"
echo ""

# Backend Setup
echo "================================"
echo "Setting up Backend..."
echo "================================"
cd backend

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy .env file
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate

echo "✓ Backend setup complete!"
echo ""
echo "To start the backend, run:"
echo "  cd backend"
echo "  source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
echo "  python manage.py runserver"
echo ""

# Frontend Setup
echo "================================"
echo "Setting up Frontend..."
echo "================================"
cd ../frontend

# Copy .env file
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Install dependencies
echo "Installing dependencies..."
npm install

echo "✓ Frontend setup complete!"
echo ""
echo "To start the frontend, run:"
echo "  cd frontend"
echo "  npm start"
echo ""

echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Terminal 1: cd backend && source venv/bin/activate && python manage.py runserver"
echo "2. Terminal 2: cd frontend && npm start"
echo "3. Visit http://localhost:3000 in your browser"
echo ""