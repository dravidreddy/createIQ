import asyncio
import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel

class TestResult(BaseModel):
    test_id: str
    query: str
    response: str
    status: str
    latency_ms: float
    tokens: Dict[str, int]
    model: Optional[str] = "unknown"
    error: Optional[str] = None
    fallback_triggered: bool = False
    trace_id: str
    execution_trace: List[str] = []

class TestRunner:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.AsyncClient(timeout=60.0)

    async def run_test_case(self, test_case: Dict[str, Any]) -> List[TestResult]:
        results = []
        test_id = test_case["id"]
        queries = test_case.get("queries", [test_case.get("query")])
        context = test_case.get("context", {})
        
        # Use valid seeded hex IDs from context or fallback to known good ones
        project_id = context.get("project_id", "60f0f1f2f3f4f5f6f7f8f9fb")
        user_id = context.get("user_id", "60f0f1f2f3f4f5f6f7f8f9fa")
        thread_id = context.get("thread_id", str(uuid.uuid4()))
        test_control = test_case.get("failure_injection")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Request-ID": f"test-{uuid.uuid4()}",
            "X-Load-Test-User": user_id
        }
        if test_control:
            headers["X-Test-Control"] = test_control

        for query in queries:
            start_time = time.perf_counter()
            try:
                payload = {
                    "project_id": project_id,
                    "topic": query,
                    "blocking": True,
                    "test_control": test_control
                }
                
                # Corrected URL: no trailing slash, absolute path
                url = f"{self.base_url}/api/v1/chat"
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    results.append(TestResult(
                        test_id=test_id,
                        query=query,
                        response=data.get("reply", ""),
                        status="success",
                        latency_ms=latency_ms,
                        tokens=data.get("tokens", {"input": 0, "output": 0}),
                        model=data.get("model", "unknown"),
                        fallback_triggered=data.get("fallback_triggered", False),
                        trace_id=data.get("trace_id", "unknown"),
                        execution_trace=data.get("execution_trace", [])
                    ))
                else:
                    # Capture trace even on error if provided by our hardened 500 handler
                    try:
                        error_data = response.json()
                    except:
                        error_data = {"detail": response.text}
                        
                    results.append(TestResult(
                        test_id=test_id,
                        query=query,
                        response="",
                        status="error",
                        latency_ms=latency_ms,
                        tokens={"input": 0, "output": 0},
                        model="unknown",
                        error=f"HTTP {response.status_code}: {error_data.get('detail', response.text)}",
                        trace_id=error_data.get("trace_id", "unknown"),
                        execution_trace=error_data.get("execution_trace", [])
                    ))
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                results.append(TestResult(
                    test_id=test_id,
                    query=query,
                    response="",
                    status="failed",
                    latency_ms=latency_ms,
                    tokens={"input": 0, "output": 0},
                    model="unknown",
                    error=str(e),
                    trace_id="unknown"
                ))
            
            await asyncio.sleep(0.5)

        return results

    async def validate_system(self) -> bool:
        """Health check validation."""
        try:
            # Corrected Health URL: /health (at root in main.py)
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200 and response.json().get("status") == "healthy"
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    async def close(self):
        await self.client.aclose()
