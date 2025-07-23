#!/bin/bash
"""
QuantMatrix V1 - ATR Signal Cron Setup
======================================

Sets up cron jobs for automated ATR signal generation:
- Pre-market: 6:00 AM ET (market analysis)
- Market Open: 9:30 AM ET (entry signals)  
- Midday: 12:00 PM ET (position monitoring)
- Market Close: 4:00 PM ET (end-of-day analysis)

Only runs Monday-Friday (market days).
"""

echo "🚀 Setting up QuantMatrix ATR Signal Cron Jobs..."

# Define paths
PROJECT_PATH="/Users/sankalpsharma/development/quantmatrix"
PYTHON_PATH="/usr/bin/python3"
LOG_PATH="/app/logs"

# Create log directory if it doesn't exist
mkdir -p ${LOG_PATH}

# Create cron job entries
CRON_JOBS="
# QuantMatrix V1 - ATR Signal Generation
# Monday-Friday only (market days)

# 6:00 AM ET - Pre-market Analysis
0 6 * * 1-5 cd ${PROJECT_PATH} && ${PYTHON_PATH} backend/tasks/daily_atr_signals.py >> ${LOG_PATH}/atr_signals.log 2>&1

# 9:30 AM ET - Market Open Signals  
30 9 * * 1-5 cd ${PROJECT_PATH} && ${PYTHON_PATH} backend/tasks/daily_atr_signals.py >> ${LOG_PATH}/atr_signals.log 2>&1

# 12:00 PM ET - Midday Check
0 12 * * 1-5 cd ${PROJECT_PATH} && ${PYTHON_PATH} backend/tasks/daily_atr_signals.py >> ${LOG_PATH}/atr_signals.log 2>&1

# 4:00 PM ET - Market Close Analysis
0 16 * * 1-5 cd ${PROJECT_PATH} && ${PYTHON_PATH} backend/tasks/daily_atr_signals.py >> ${LOG_PATH}/atr_signals.log 2>&1

# Weekly cleanup - Remove signals older than 30 days
0 2 * * 0 cd ${PROJECT_PATH} && ${PYTHON_PATH} -c \"from backend.tasks.cleanup_old_signals import cleanup_old_signals; cleanup_old_signals(days=30)\" >> ${LOG_PATH}/cleanup.log 2>&1
"

# Add to crontab
echo "Adding cron jobs..."
(crontab -l 2>/dev/null; echo "$CRON_JOBS") | crontab -

echo "✅ ATR Signal cron jobs installed!"
echo ""
echo "📋 Installed Schedule:"
echo "   6:00 AM ET - Pre-market analysis"
echo "   9:30 AM ET - Market open signals"
echo "   12:00 PM ET - Midday monitoring"  
echo "   4:00 PM ET - Market close analysis"
echo ""
echo "📁 Logs will be written to: ${LOG_PATH}/atr_signals.log"
echo ""
echo "🔍 To view current cron jobs:"
echo "   crontab -l"
echo ""
echo "❌ To remove all QuantMatrix cron jobs:"
echo "   crontab -l | grep -v 'QuantMatrix' | crontab -" 