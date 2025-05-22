#!/usr/bin/env python3
"""Run the Flask application."""
from app import app, create_app

if __name__ == '__main__':
    # Create and run the application
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5002)
