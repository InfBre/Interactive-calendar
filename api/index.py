from flask import Flask
from app import app as flask_app

# Vercel Serverless Function handler
def handler(request):
    """Handle the request and return the response."""
    return flask_app.wsgi_app(request.environ, lambda x, y: None)
