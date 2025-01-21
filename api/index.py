from app import app

# Vercel Serverless Function handler
def handler(request, context):
    return app(request)
