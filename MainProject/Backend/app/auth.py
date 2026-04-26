# backend/app/auth.py
from fastapi import Header, HTTPException
import os


async def verify_admin_key(x_api_key: str = Header(...)):
    """
    Protects sensitive endpoints.
    Caller must pass:  x-api-key: your-secret-key
    """
    expected = os.getenv("ADMIN_API_KEY", "potholeiq-dev")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True