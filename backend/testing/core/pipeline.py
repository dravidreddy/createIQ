import asyncio
import os
import sys
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from jose import jwt
from dotenv import load_dotenv

# Path detection: ensure we can find internal modules
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from testing.runner import TestRunner, TestResult
from testing.evaluator import ResponseEvaluator, EvaluationScore

# Load environment - try from script dir and root
load_dotenv(dotenv_path=os.path.join(root_dir, ".env"))

SECRET_KEY = os.getenv("SECRET_KEY", "your_super_secret_key_change_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def generate_test_token(user_id: str = "60f0f1f2f3f4f5f6f7f8f9fa") -> str:
    # We use a valid-looking 24-char hex ID because Beanie/PydanticObjectId expects it
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.utcnow().timestamp() + 3600, # 1 hour
        "iat": datetime.utcnow().timestamp()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

class TestingPipeline:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.token = generate_test_token()
        self.runner = TestRunner(BASE_URL, self.token)
        self.evaluator = ResponseEvaluator(GEMINI_API_KEY)
        self.results = []

    async def run(self, dry_run: bool = False):
        print(f"🚀 Starting CreatorIQ Internal Testing Pipeline [dry_run={dry_run}]")
        
        with open(self.dataset_path, "r") as f:
            test_cases = json.load(f)

        for tc in test_cases:
            print(f"--- Running Test Case: {tc['id']} [{tc['type']}] ---")
            
            if dry_run:
                # Dummy results for dry run
                self.results.append({
                    "test_id": tc['id'],
                    "status": "dry_skipped",
                    "timestamp": datetime.utcnow().isoformat()
                })
                continue

            # 1. Execute Runner
            case_results = await self.runner.run_test_case(tc)
            
            # 2. Evaluate each result
            tc_evals = []
            for res in case_results:
                if res.status == "success":
                    print(f"  | Evaluation in progress for query: {res.query[:50]}...")
                    eval_score = await self.evaluator.evaluate(
                        query=res.query,
                        response=res.response,
                        expected_behavior=json.dumps(tc.get("expected", {}))
                    )
                    tc_evals.append(eval_score.model_dump())
                    print(f"  | Result: {'PASSED' if eval_score.final_pass else 'FAILED'} (Score: {eval_score.quality})")
                else:
                    print(f"  ! Error: {res.error}")
                    tc_evals.append({"error": res.error})

            self.results.append({
                "test_id": tc['id'],
                "type": tc['type'],
                "run_results": [r.model_dump() for r in case_results],
                "evaluations": tc_evals,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Save intermediate results
            self._save_results()

        self._print_final_report()

    def _save_results(self):
        result_dir = "backend/testing/results"
        os.makedirs(result_dir, exist_ok=True)
        with open(f"{result_dir}/results.json", "w") as f:
            json.dump(self.results, f, indent=2)

    def _print_final_report(self):
        print("\n" + "="*50)
        print("📊 FINAL AGGREGATE REPORT")
        print("="*50)
        
        total = len(self.results)
        if total == 0: return
        
        passed = 0
        total_latency = 0
        errors = 0
        
        for r in self.results:
            is_pass = all(e.get("final_pass", False) for e in r.get("evaluations", []))
            if is_pass: passed += 1
            
            for res in r.get("run_results", []):
                total_latency += res.get("latency_ms", 0)
                if res.get("status") in ("error", "failed"):
                    errors += 1

        print(f"Total Test Cases: {total}")
        print(f"Total Passed: {passed}")
        print(f"Total Errors: {errors}")
        print(f"Pass Rate: {(passed/total)*100:.2f}%")
        print(f"Average Latency: {total_latency/max(1, total):.2f} ms")
        print("="*50)

if __name__ == "__main__":
    import asyncio
    # Ensure correctly resolved path for the dataset
    default_dataset = os.path.join(current_dir, "datasets", "test_cases.json")
    pipeline = TestingPipeline(default_dataset)
    asyncio.run(pipeline.run(dry_run=False))
