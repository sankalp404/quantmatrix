#!/bin/bash
# QuantMatrix V1 - Docker Database Rebuild Script
# ===============================================
# 
# Rebuilds the V1 database using Docker containers
# (Following user preference for Docker-based development)

echo "🗃️ QuantMatrix V1 - Database Rebuild (Docker)"
echo "=============================================="

# Check if Docker Compose is running
if ! docker-compose ps | grep -q "backend"; then
    echo "⚠️ Docker containers not running. Starting them..."
    docker-compose up -d
    sleep 5
fi

echo "🔧 Rebuilding V1 database schema..."

# Option 1: Run database recreation in Docker container
echo "📦 Running database recreation in Docker container..."
docker-compose exec backend python backend/recreate_v1_database.py

if [ $? -eq 0 ]; then
    echo "✅ Database rebuild completed successfully!"
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Test API endpoints: docker-compose exec backend python -m pytest backend/tests/"
    echo "   2. Run ATR tests: docker-compose exec backend python backend/run_tests.py"
    echo "   3. Start live ATR signals: docker-compose exec backend python backend/scripts/run_atr_universe.py"
    echo ""
    echo "🚀 Your QuantMatrix V1 system is ready for production!"
else
    echo "❌ Database rebuild failed. Trying alternative approach..."
    echo ""
    echo "💡 Manual steps:"
    echo "   1. Check database connection: docker-compose logs postgres"
    echo "   2. Verify backend container: docker-compose logs backend"
    echo "   3. Install dependencies: docker-compose exec backend pip install -r requirements.txt"
    echo "   4. Retry: docker-compose exec backend python backend/recreate_v1_database.py"
fi

echo ""
echo "📊 Current container status:"
docker-compose ps 