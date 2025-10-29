#!/usr/bin/env python3
"""
New refactored Flask web application entry point.
Uses the modular app factory pattern.
"""

from app import create_app

# Create the Flask application using the factory
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*80)
    print("WAGES APP - WEB INTERFACE (REFACTORED)")
    print("="*80)
    print("\n🌐 Starting web server...")
    print("📊 Open your browser to: http://localhost:5001")
    print("⏹️  Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
