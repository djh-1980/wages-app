#!/usr/bin/env python3
"""
New refactored Flask web application entry point.
Uses the modular app factory pattern.
"""

from app import create_app

# Create the Flask application using the factory
app = create_app()

if __name__ == '__main__':
    import os
    from pathlib import Path
    
    # Check if SSL certificates exist
    cert_file = Path('cert.pem')
    key_file = Path('key.pem')
    
    if cert_file.exists() and key_file.exists():
        print("\n" + "="*80)
        print("WAGES APP - WEB INTERFACE (REFACTORED) - HTTPS ENABLED")
        print("="*80)
        print("\n🌐 Starting web server with HTTPS...")
        print("📊 Open your browser to: https://localhost:5001")
        print("📱 Mobile access: https://192.168.1.170:5001")
        print("⚠️  You'll see a security warning - click 'Advanced' and 'Proceed'")
        print("⏹️  Press Ctrl+C to stop\n")
        print("="*80 + "\n")
        
        app.run(debug=True, host='0.0.0.0', port=5001, ssl_context=('cert.pem', 'key.pem'))
    else:
        print("\n" + "="*80)
        print("WAGES APP - WEB INTERFACE (REFACTORED)")
        print("="*80)
        print("\n🌐 Starting web server...")
        print("📊 Open your browser to: http://localhost:5001")
        print("⏹️  Press Ctrl+C to stop\n")
        print("="*80 + "\n")
        
        app.run(debug=True, host='0.0.0.0', port=5001)
