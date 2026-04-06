import asyncio
import uuid
import time
import json
import httpx
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "http://localhost:8000/api/v1"
CONCURRENCY = 50
TIMEOUT = httpx.Timeout(120.0, connect=10.0)

@dataclass
class TestResult:
    user_id: str
    success: bool = False
    start_time: float = 0
    end_time: float = 0
    duration: float = 0
    error: str = ""
    stages_completed: List[str] = field(default_factory=list)

async def simulate_user(user_id: int, results: List[TestResult]):
    # MongoDB ObjectId must be 24-char hex. uuid4().hex is 32 chars.
    user_key = uuid.uuid4().hex[:24]
    result = TestResult(user_id=user_key, start_time=time.time())
    headers = {"X-Load-Test-User": user_key}
    project_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # 1. Start Pipeline
            logger.info(f"User {user_id}: Starting pipeline...")
            start_payload = {
                "project_id": project_id,
                "topic": f"Load test topic {user_id}",
                "niche": "Tech",
                "platforms": ["YouTube", "TikTok"],
                "video_length": "5-10 minute",
                "target_audience": "Tech enthusiasts",
                "language": "English"
            }
            
            thread_id = None
            async with client.stream("POST", f"{BASE_URL}/pipeline/start", json=start_payload, headers=headers) as response:
                if response.status_code != 200:
                    result.error = f"Start failed: {response.status_code}"
                    results.append(result)
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "): continue
                    data = json.loads(line[6:])
                    
                    if data["type"] == "thread_created":
                        thread_id = data["data"]["thread_id"]
                    elif data["type"] == "interrupt":
                        logger.info(f"User {user_id}: Hit interrupt at {data['data']['stage']}")
                        result.stages_completed.append(data['data']['stage'])
                        break
                    elif data["type"] == "error":
                        result.error = f"Pipeline Error: {data['data']['message']}"
                        results.append(result)
                        return

            if not thread_id:
                result.error = "Thread ID not received"
                results.append(result)
                return

            # 2. Resume Pipeline (Select Idea)
            logger.info(f"User {user_id}: Resuming pipeline for thread {thread_id}...")
            resume_payload = {
                "action": "select",
                "stage": "idea_selection",
                "selected_content": {"title": "Mock Idea", "description": "Mock Description"}
            }
            
            async with client.stream("POST", f"{BASE_URL}/pipeline/{thread_id}/resume", json=resume_payload, headers=headers) as response:
                if response.status_code != 200:
                    result.error = f"Resume failed: {response.status_code}"
                    results.append(result)
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "): continue
                    data = json.loads(line[6:])
                    
                    if data["type"] == "interrupt":
                        logger.info(f"User {user_id}: Hit second interrupt at {data['data']['stage']}")
                        result.stages_completed.append(data['data']['stage'])
                        break # In a real test we might go further
                    elif data["type"] == "done":
                        logger.info(f"User {user_id}: Pipeline finished")
                        result.success = True
                        break
                    elif data["type"] == "error":
                        result.error = f"Resume Error: {data['data']['message']}"
                        results.append(result)
                        return

            result.success = True
            result.end_time = time.time()
            result.duration = result.end_time - result.start_time
            logger.info(f"User {user_id}: Completed in {result.duration:.2f}s")

        except Exception as e:
            logger.error(f"User {user_id}: Exception: {str(e)}")
            result.error = str(e)
        finally:
            results.append(result)

async def main():
    logger.info(f"Starting architectural load test with {CONCURRENCY} concurrent users...")
    results = []
    
    start_time = time.time()
    tasks = [simulate_user(i, results) for i in range(CONCURRENCY)]
    await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Analysis
    success_count = sum(1 for r in results if r.success)
    error_count = len(results) - success_count
    total_duration = end_time - start_time
    
    avg_duration = sum(r.duration for r in results if r.success) / success_count if success_count > 0 else 0
    
    print("\n" + "="*50)
    print("ARCHITECTURAL LOAD TEST RESULTS")
    print("="*50)
    print(f"Total Users:      {CONCURRENCY}")
    print(f"Successful:       {success_count}")
    print(f"Failed:           {error_count}")
    print(f"Total Duration:   {total_duration:.2f}s")
    print(f"Avg User Time:    {avg_duration:.2f}s")
    print(f"Throughput:       {CONCURRENCY/total_duration:.2f} users/sec")
    print("="*50)
    
    if error_count > 0:
        print("\nERRORS:")
        for r in results:
            if r.error:
                print(f"- User {r.user_id[:8]}: {r.error}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
