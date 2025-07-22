#!/bin/bash
# QuantMatrix Automated Testing Setup
# Installs dependencies and starts continuous testing

echo "🧪 QuantMatrix Automated Testing Setup"
echo "====================================="

# Check if we're in the backend directory
if [ ! -f "test_simple.py" ]; then
    echo "❌ Please run this from the backend directory"
    exit 1
fi

# Detect Python and pip commands
PYTHON_CMD=""
PIP_CMD=""

# Check for python3 first, then python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

# Check for pip3 first, then pip
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "❌ pip not found. Please install pip"
    exit 1
fi

echo "✅ Using Python: $PYTHON_CMD"
echo "✅ Using pip: $PIP_CMD"

# Install required dependencies
echo "📦 Installing test dependencies..."
$PIP_CMD install pytest pytest-asyncio watchdog requests --user

# Make test runner executable
chmod +x test_runner.py test_simple.py

echo ""
echo "🚀 Starting automated test runner..."
echo "This will:"
echo "  ✅ Run tests whenever you change backend files"
echo "  ✅ Show test results immediately"  
echo "  ✅ Run API smoke tests on failures"
echo "  ✅ Stop on first failure for quick debugging"
echo ""
echo "🛑 Press Ctrl+C to stop"
echo ""

# Update test runner to use detected Python command
sed -i.bak "s/python/$PYTHON_CMD/g" test_runner.py

# Start the test runner
$PYTHON_CMD test_runner.py 