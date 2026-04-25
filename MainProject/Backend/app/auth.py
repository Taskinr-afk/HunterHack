# backend/app/auth.py
from fastapi import Header, HTTPException
import os

# Reads ADMIN_API_KEY from your .env file
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me")

async def verify_admin_key(x_api_key: str = Header(...)):
    """
    Protects sensitive endpoints.
    Caller must pass:  x-api-key: your-secret-key
    """
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True