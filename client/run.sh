#!/bin/bash

# Hungarian Tarokk Client - Run Script
# Quick start script for development

cd "$(dirname "$0")"

echo "🎴 Hungarian Tarokk Client"
echo "=========================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env from .env.example..."
        cp .env.example .env
        echo ""
    fi
fi

echo "🚀 Starting development server..."
echo ""
npm run dev
