#!/bin/bash

# QuantMatrix Startup Script
echo "🚀 Starting QuantMatrix Trading Platform..."

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to check if docker-compose is available
check_docker_compose() {
    if command -v docker-compose > /dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version > /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        echo "❌ Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    echo "✅ Docker Compose found: $COMPOSE_CMD"
}

# Function to setup environment
setup_env() {
    if [ ! -f .env ]; then
        echo "📝 Creating .env file from template..."
        cp env.example .env
        echo "⚠️  Please edit .env file with your configuration before proceeding."
        echo "   At minimum, you should change the SECRET_KEY."
        read -p "Press Enter to continue once you've configured .env..."
    else
        echo "✅ .env file exists"
    fi
}

# Function to start services
start_services() {
    echo "🐳 Starting Docker containers..."
    $COMPOSE_CMD up -d postgres redis
    
    echo "⏳ Waiting for database to be ready..."
    sleep 10
    
    echo "🔧 Starting backend services..."
    $COMPOSE_CMD up -d backend celery_worker celery_beat flower
    
    echo "✅ All services started!"
}

# Function to show service status
show_status() {
    echo ""
    echo "📊 Service Status:"
    $COMPOSE_CMD ps
    
    echo ""
    echo "🌐 Access URLs:"
    echo "   • API Documentation: http://localhost:8000/docs"
    echo "   • API Health Check: http://localhost:8000/health"
    echo "   • Celery Monitor (Flower): http://localhost:5555"
    echo "   • PostgreSQL: localhost:5432"
    echo "   • Redis: localhost:6379"
}

# Function to show logs
show_logs() {
    echo ""
    echo "📋 Recent logs:"
    $COMPOSE_CMD logs --tail=50 backend
}

# Function to run tests
run_tests() {
    echo "🧪 Running tests..."
    $COMPOSE_CMD exec backend python -m pytest tests/ -v
}

# Function to stop services
stop_services() {
    echo "🛑 Stopping all services..."
    $COMPOSE_CMD down
    echo "✅ All services stopped"
}

# Main menu
case "$1" in
    start)
        check_docker
        check_docker_compose
        setup_env
        start_services
        show_status
        ;;
    stop)
        check_docker_compose
        stop_services
        ;;
    restart)
        check_docker_compose
        stop_services
        sleep 2
        start_services
        show_status
        ;;
    status)
        check_docker_compose
        show_status
        ;;
    logs)
        check_docker_compose
        show_logs
        ;;
    test)
        check_docker_compose
        run_tests
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all QuantMatrix services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show service status and URLs"
        echo "  logs    - Show recent backend logs"
        echo "  test    - Run tests"
        exit 1
        ;;
esac 