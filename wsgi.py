"""
WSGI entry point for production deployment.
Run this using Gunicorn (Linux) or Waitress (Windows).

Example (Linux):
gunicorn --bind 0.0.0.0:5000 wsgi:app

Example (Windows):
waitress-serve --port=5000 wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
