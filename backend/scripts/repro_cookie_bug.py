import asyncio
from fastapi import FastAPI, Response, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse
import json

# Minimal app to reproduce the middleware issue
from starlette.responses import Response as StarletteResponse

def create_test_app():
    app = FastAPI()

    @app.middleware("http")
    async def infrastructure_metadata_middleware(request: Request, call_next):
        response = await call_next(request)
        if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                data = json.loads(body)
                data["_infra_meta"] = {"trace_id": "test-trace"}
                modified_body = json.dumps(data).encode("utf-8")
                
                # REPRODUCING THE BUG: Using dict(response.headers)
                headers = dict(response.headers)
                headers.pop("content-length", None)
                
                return StarletteResponse(
                    content=modified_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type="application/json"
                )
            except:
                pass
        return response

    @app.post("/login")
    async def login():
        response = JSONResponse({"status": "success"})
        response.set_cookie("access_token", "secret1", httponly=True)
        response.set_cookie("refresh_token", "secret2", httponly=True)
        return response

    return app

def verify_cookies():
    app = create_test_app()
    client = TestClient(app)
    
    print("--- 🧪 Testing Cookie Persistence ---")
    response = client.post("/login")
    
    cookies = response.cookies
    print(f"Status Code: {response.status_code}")
    print(f"Cookies received: {list(cookies.keys())}")
    
    if "access_token" in cookies and "refresh_token" in cookies:
        print("✅ SUCCESS: Both cookies preserved.")
    else:
        print("❌ FAILURE: Cookies lost or collapsed due to dict(headers) conversion.")
        if "refresh_token" in cookies and "access_token" not in cookies:
            print("   (Confirmed: Only the last Set-Cookie header was kept)")

if __name__ == "__main__":
    verify_cookies()
