#!/bin/bash

# Start the Factor Trading Frontend
echo "Starting Factor Trading Frontend..."
echo "Access the application at: http://localhost:8502"
echo ""
echo "Pages available:"
echo "  🚀 Backtest Management - Create and manage backtests"
echo "  📈 Results Visualization - Analyze backtest results"
echo ""

streamlit run app.py --server.port 8502