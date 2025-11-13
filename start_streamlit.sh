#!/bin/bash
# Start Streamlit Frontend

echo "🎨 Starting Streamlit Frontend..."
echo "Make sure Flask server is running on http://localhost:5000"
echo ""
echo "Streamlit will be available at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop Streamlit"
echo ""

streamlit run streamlit_app.py
