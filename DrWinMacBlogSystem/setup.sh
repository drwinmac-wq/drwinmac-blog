#!/bin/bash

# Dr.WinMac Blog API - Local Development Setup Script
# Automates Python environment setup and dependency installation

set -e  # Exit on error

echo "🚀 Dr.WinMac Blog API - Development Setup"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+"
    exit 1
fi

echo "✅ Python $(python3 --version) found"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"

# Install dependencies
echo ""
echo "📚 Installing dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your:"
    echo "   - OPENAI_API_KEY"
    echo "   - ADMIN_PASSCODE"
    echo "   - SMTP credentials"
    echo ""
    echo "Then run: python app.py"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "========================================="
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate  # Activate virtual environment"
echo "  python app.py               # Start Flask server"
echo ""
echo "Then visit: http://localhost:5000/admin/"
echo ""
