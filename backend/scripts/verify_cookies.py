import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse, Response as StarletteResponse

def verify_cookie_fix():
    app = FastAPI()

    # The Logic I just added to your main.py
    @app.middleware("http")
    async def infra_middleware(request: Request, call_next):
        response = await call_next(request)
        if response.status_code == 200:
            body = b"".join([chunk async for chunk in response.body_iterator])
            # The Fix: Use raw_headers to preserve duplicates like Set-Cookie
            new_response = StarletteResponse(content=body, status_code=response.status_code)
            new_response.raw_headers = [(n, v) for n, v in response.raw_headers if n.lower() != b"content-length"]
            return new_response
        return response

    @app.post("/login")
    async def login():
        response = JSONResponse({"status": "success"})
        response.set_cookie("access_token", "secret1")
        response.set_cookie("refresh_token", "secret2")
        return response

    client = TestClient(app)
    response = client.post("/login")
    
    print(f"Cookies received: {list(response.cookies.keys())}")
    if "access_token" in response.cookies and "refresh_token" in response.cookies:
        print("✅ SUCCESS: Both cookies are preserved through the middleware!")
    else:
        print("❌ FAILURE: Cookies are still being lost.")

if __name__ == "__main__":
    verify_cookie_fix()
